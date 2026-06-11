"""
HR domain services (Sections 3 & 6).

The classification engine splits each employee's compensation between Section 3
(Labor) and Section 6 (Capacity Building):

  • Vacation status      -> 0 SAR salary (but still counts toward GOSI headcount)
  • Trainee/Scholarship  -> Section 3 zeroed, full value shifted to Section 6
                           (prevents audit double-counting penalties)
  • Regular              -> full value in Section 3

Plus the GOSI cross-check: Excel row count must equal the summed Saudi+Expat
headcount extracted from the GOSI certificate(s).
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from apps.hr.models import GosiCertificate, HrMonthlyUpload, PayrollRow


@dataclass
class SectionSplit:
    section3: Decimal
    section6: Decimal


def classify_payroll(*, status: str, classification: str, gross: Decimal) -> SectionSplit:
    """Pure split of one employee's compensation across Section 3 / Section 6."""
    if status == PayrollRow.Status.VACATION:
        return SectionSplit(Decimal("0"), Decimal("0"))
    if classification == PayrollRow.Classification.TRAINEE:
        return SectionSplit(Decimal("0"), gross)  # shift entirely to Capacity Building
    return SectionSplit(gross, Decimal("0"))


def apply_classification(row: PayrollRow) -> PayrollRow:
    """Compute and persist a row's Section 3/6 amounts from its 🔒 components."""
    gross = (
        (row.basic or Decimal("0"))
        + (row.housing or Decimal("0"))
        + (row.transport or Decimal("0"))
        + (row.bonus_vacation_pay or Decimal("0"))
    )
    split = classify_payroll(status=row.status, classification=row.classification, gross=gross)
    row.section3_amount = split.section3
    row.section6_amount = split.section6
    row.save(update_fields=["section3_amount", "section6_amount"])
    return row


@dataclass
class CrossCheckResult:
    row_count: int
    gosi_headcount: int
    matches: bool


def gosi_cross_check(upload: HrMonthlyUpload) -> CrossCheckResult:
    """Excel row count must equal summed Saudi+Expat headcount across branches."""
    row_count = PayrollRow.objects.filter(upload=upload).count()
    headcount = 0
    for cert in GosiCertificate.objects.filter(upload=upload):
        headcount += cert.saudi_headcount + cert.expat_headcount
    return CrossCheckResult(row_count, headcount, row_count == headcount)
