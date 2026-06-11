"""
Finance domain services (Appendix A) — the Master Validator.

Finance is the gatekeeper: no auditor export unless the Audited Trial Balance
reconciles with the HR/Procurement aggregates within ±5%. On a passing Annual
Hard-Close the compliance year is permanently LOCKED (the Immutable Data Lock).

All money is read out of 🔒 encrypted columns and summed in Python.
"""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.scoring.engine import within_tolerance
from apps.finance.models import (
    AnnualHardClose,
    MonthlySoftClose,
    ReconciliationCheck,
    TbAccountMapping,
    TrialBalanceUpload,
)
from apps.hr.models import PayrollRow
from apps.procurement.models import Invoice
from apps.tenancy.models import ComplianceYear

# Trial-balance categories that are subtracted to form the LCGPA ceiling.
EXEMPTION_CATEGORIES = {
    TbAccountMapping.Category.EXEMPT_ZAKAT,
    TbAccountMapping.Category.EXEMPT_CUSTOMS,
    TbAccountMapping.Category.EXEMPT_VISA,
}


# --- Aggregates from the operational modules ---------------------------------
def aggregate_hr_salaries(tenant, compliance_year, month: int | None = None) -> Decimal:
    """Sum Section-3 payroll compensation (decrypting 🔒 amounts) for a period."""
    rows = PayrollRow.objects.filter(
        tenant=tenant, upload__compliance_year=compliance_year
    )
    if month is not None:
        rows = rows.filter(upload__month=month)
    total = Decimal("0")
    for row in rows.only("basic", "housing", "transport", "bonus_vacation_pay"):
        total += (row.basic or Decimal("0")) + (row.housing or Decimal("0"))
        total += (row.transport or Decimal("0")) + (row.bonus_vacation_pay or Decimal("0"))
    return total


def aggregate_proc_purchases(tenant, compliance_year, month: int | None = None) -> Decimal:
    """Sum net eligible procurement spend for a period."""
    invoices = Invoice.objects.filter(
        tenant=tenant, upload__compliance_year=compliance_year
    )
    if month is not None:
        invoices = invoices.filter(upload__month=month)
    total = Decimal("0")
    for inv in invoices.only("gross_amount", "vat_amount", "net_eligible_spend"):
        net = inv.net_eligible_spend
        if net is None:
            net = (inv.gross_amount or Decimal("0")) - (inv.vat_amount or Decimal("0"))
        total += net
    return total


# --- Monthly Soft-Close -------------------------------------------------------
def run_monthly_reconciliation(soft_close: MonthlySoftClose) -> MonthlySoftClose:
    """Compare Finance's typed monthly totals against HR/Proc uploads (±5%)."""
    tenant = soft_close.tenant
    year = soft_close.compliance_year
    hr_actual = aggregate_hr_salaries(tenant, year, soft_close.month)
    proc_actual = aggregate_proc_purchases(tenant, year, soft_close.month)

    _, hr_var = within_tolerance(soft_close.total_salaries, hr_actual)
    _, proc_var = within_tolerance(soft_close.total_purchases, proc_actual)
    soft_close.hr_variance = hr_var
    soft_close.proc_variance = proc_var
    soft_close.save(update_fields=["hr_variance", "proc_variance"])
    return soft_close


# --- Trial Balance ceiling ----------------------------------------------------
def ceiling_from_mappings(items: list[tuple[str, Decimal]]) -> Decimal:
    """
    Pure helper: ceiling = base minus statutory exemptions, given (category, amount)
    pairs. Kept side-effect-free so it is unit-testable without a database.
    """
    base = Decimal("0")
    exemptions = Decimal("0")
    for category, amount in items:
        amount = amount or Decimal("0")
        if category in EXEMPTION_CATEGORIES:
            exemptions += amount
        else:
            base += amount
    return base - exemptions


def compute_ceiling(trial_balance: TrialBalanceUpload) -> Decimal:
    """
    LCGPA ceiling = mapped revenue/cost base minus statutory exemptions
    (Zakat, Customs & Duties, Visa/Residency Fees).
    """
    return ceiling_from_mappings(
        [(m.mapped_category, m.amount or Decimal("0")) for m in trial_balance.account_mappings.all()]
    )


def depreciation_from_tb(trial_balance: TrialBalanceUpload) -> Decimal:
    total = Decimal("0")
    for m in trial_balance.account_mappings.filter(
        mapped_category=TbAccountMapping.Category.DEPRECIATION
    ):
        total += m.amount or Decimal("0")
    return total


# --- Annual Hard-Close: the Strict Block --------------------------------------
def run_annual_reconciliation(hard_close: AnnualHardClose) -> ReconciliationCheck:
    """
    Reconcile the Audited income totals against the HR/Proc annual aggregates.
    A variance over ±5% throws the Red Light and blocks export (passed=False).
    """
    tenant = hard_close.tenant
    year = hard_close.compliance_year
    hr_actual = aggregate_hr_salaries(tenant, year)
    proc_actual = aggregate_proc_purchases(tenant, year)

    audited_costs = (hard_close.direct_costs or Decimal("0")) + (hard_close.gna or Decimal("0"))
    # Salaries reconcile against audited costs; purchases against direct costs.
    salaries_ok, _ = within_tolerance(hr_actual, audited_costs)
    purchases_ok, _ = within_tolerance(proc_actual, hard_close.direct_costs or Decimal("0"))

    _, variance = within_tolerance(
        hr_actual + proc_actual,
        audited_costs + (hard_close.direct_costs or Decimal("0")),
    )
    passed = salaries_ok and purchases_ok

    hard_close.reconciliation_passed = passed
    hard_close.save(update_fields=["reconciliation_passed"])
    return ReconciliationCheck.objects.create(
        tenant=tenant,
        compliance_year=year,
        scope=ReconciliationCheck.Scope.ANNUAL,
        variance_pct=variance,
        passed=passed,
    )


# --- The Immutable Data Lock --------------------------------------------------
class HardCloseNotPassed(Exception):
    """Raised when locking is attempted before reconciliation passes."""


@transaction.atomic
def lock_compliance_year(compliance_year: ComplianceYear) -> ComplianceYear:
    """
    Permanently LOCK the year after a passing Annual Hard-Close. HR/Procurement/
    Finance lose write access (enforced by the year-lock guard); Super Admin keeps
    read-only access for downloads.
    """
    hard_close = AnnualHardClose.objects.filter(compliance_year=compliance_year).first()
    if not hard_close or not hard_close.reconciliation_passed:
        raise HardCloseNotPassed("Annual Hard-Close must pass ±5% reconciliation before locking.")
    compliance_year.state = ComplianceYear.State.LOCKED
    compliance_year.locked_at = timezone.now()
    compliance_year.save(update_fields=["state", "locked_at"])
    return compliance_year


def export_allowed(compliance_year: ComplianceYear) -> bool:
    """Exports unlock only once the annual reconciliation has passed."""
    hard_close = AnnualHardClose.objects.filter(compliance_year=compliance_year).first()
    return bool(hard_close and hard_close.reconciliation_passed)
