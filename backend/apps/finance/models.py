"""
Module 4 — Finance & the Master Validator (Appendix A).

Monthly Soft-Close + Annual Hard-Close, Trial Balance mapping with statutory
exemptions, the strict ±5% reconciliation block, and the Evidence Vault. Finance
is the gatekeeper: no auditor export unless everything reconciles within ±5%.
"""
from django.db import models

from apps.common.fields import EncryptedDecimalField
from apps.common.models import TenantScopedModel


class MonthlySoftClose(TenantScopedModel):
    compliance_year = models.ForeignKey(
        "tenancy.ComplianceYear", on_delete=models.CASCADE, related_name="soft_closes"
    )
    month = models.PositiveSmallIntegerField()
    total_salaries = EncryptedDecimalField()
    total_purchases = EncryptedDecimalField()
    hr_variance = models.DecimalField(max_digits=6, decimal_places=4, null=True, blank=True)
    proc_variance = models.DecimalField(max_digits=6, decimal_places=4, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "compliance_year", "month"], name="uq_soft_close_slot"
            ),
        ]


class AnnualHardClose(TenantScopedModel):
    """The 5 high-level totals from the Audited Income Statement."""

    compliance_year = models.OneToOneField(
        "tenancy.ComplianceYear", on_delete=models.CASCADE, related_name="hard_close"
    )
    revenues = EncryptedDecimalField()
    direct_costs = EncryptedDecimalField()
    gna = EncryptedDecimalField()  # General & Administrative
    selling_distribution = EncryptedDecimalField()
    finance_costs = EncryptedDecimalField()
    state = models.CharField(max_length=20, default="DRAFT")
    reconciliation_passed = models.BooleanField(default=False)


class TrialBalanceUpload(TenantScopedModel):
    compliance_year = models.ForeignKey(
        "tenancy.ComplianceYear", on_delete=models.CASCADE, related_name="trial_balances"
    )
    raw_file_ref = models.CharField(max_length=512)
    uploaded_at = models.DateTimeField(auto_now_add=True)


class TbAccountMapping(TenantScopedModel):
    """Interactive TB mapping incl. statutory exemptions subtracted from the ceiling."""

    class Category(models.TextChoices):
        REVENUE = "REVENUE", "Revenue"
        DIRECT_COST = "DIRECT_COST", "Direct Cost"
        GNA = "GNA", "G&A"
        SELLING = "SELLING", "Selling / Distribution"
        FINANCE_COST = "FINANCE_COST", "Finance Cost"
        DEPRECIATION = "DEPRECIATION", "Depreciation Expense"
        EXEMPT_ZAKAT = "EXEMPT_ZAKAT", "Exemption — Zakat"
        EXEMPT_CUSTOMS = "EXEMPT_CUSTOMS", "Exemption — Customs & Duties"
        EXEMPT_VISA = "EXEMPT_VISA", "Exemption — Visa / Residency Fees"

    trial_balance = models.ForeignKey(
        TrialBalanceUpload, on_delete=models.CASCADE, related_name="account_mappings"
    )
    account_code = models.CharField(max_length=64, blank=True)
    account_name = models.CharField(max_length=255, blank=True)
    mapped_category = models.CharField(max_length=20, choices=Category.choices)
    amount = EncryptedDecimalField()


class ReconciliationCheck(TenantScopedModel):
    class Scope(models.TextChoices):
        MONTHLY = "MONTHLY", "Monthly"
        ANNUAL = "ANNUAL", "Annual (Hard-Close)"

    compliance_year = models.ForeignKey(
        "tenancy.ComplianceYear", on_delete=models.CASCADE, related_name="reconciliations"
    )
    scope = models.CharField(max_length=10, choices=Scope.choices)
    variance_pct = models.DecimalField(max_digits=6, decimal_places=4, null=True, blank=True)
    passed = models.BooleanField(default=False)
    checked_at = models.DateTimeField(auto_now_add=True)


class EvidenceVault(TenantScopedModel):
    class DocType(models.TextChoices):
        FIN_STATEMENTS_PDF = "FIN_STATEMENTS_PDF", "Signed Financial Statements (PDF)"
        TB_EXCEL = "TB_EXCEL", "Raw Trial Balance (Excel)"
        GOSI_PDF = "GOSI_PDF", "GOSI Certificate (PDF)"

    compliance_year = models.ForeignKey(
        "tenancy.ComplianceYear", on_delete=models.CASCADE, related_name="evidence"
    )
    doc_type = models.CharField(max_length=20, choices=DocType.choices)
    file_ref = models.CharField(max_length=512)
    uploaded_at = models.DateTimeField(auto_now_add=True)
