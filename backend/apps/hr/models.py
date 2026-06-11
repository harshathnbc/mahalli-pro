"""
Module 2 — HR & Labor (Sections 3 & 6).

12 monthly slots per compliance year. GOSI PDF headcount aggregation across
branches, and the payroll classification engine (Trainee salary auto-shifts
Section 3 -> Section 6 to avoid audit double-counting). Financial columns are
AES-256 encrypted (🔒).
"""
from django.db import models

from apps.common.fields import EncryptedCharField, EncryptedDecimalField
from apps.common.models import TenantScopedModel


class HrMonthlyUpload(TenantScopedModel):
    compliance_year = models.ForeignKey(
        "tenancy.ComplianceYear", on_delete=models.CASCADE, related_name="hr_uploads"
    )
    month = models.PositiveSmallIntegerField()  # 1..12
    status = models.CharField(max_length=20, default="PENDING")
    payroll_file_ref = models.CharField(max_length=512, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "compliance_year", "month"], name="uq_hr_upload_slot"
            ),
        ]


class GosiCertificate(TenantScopedModel):
    """1-page GOSI PDF per branch; parser extracts + sums Saudi/Expat headcounts."""

    upload = models.ForeignKey(HrMonthlyUpload, on_delete=models.CASCADE, related_name="gosi_certs")
    branch = models.ForeignKey(
        "tenancy.TenantBranch", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    file_ref = models.CharField(max_length=512)
    saudi_headcount = models.PositiveIntegerField(default=0)
    expat_headcount = models.PositiveIntegerField(default=0)
    parsed_at = models.DateTimeField(null=True, blank=True)


class PayrollRow(TenantScopedModel):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        VACATION = "VACATION", "Vacation (0 SAR, counts for GOSI)"

    class Classification(models.TextChoices):
        REGULAR = "REGULAR", "Regular Employee"
        TRAINEE = "TRAINEE", "Trainee / Scholarship (-> Section 6)"

    upload = models.ForeignKey(HrMonthlyUpload, on_delete=models.CASCADE, related_name="rows")

    # Demographics (PII -> encrypted).
    national_id = EncryptedCharField()
    name = EncryptedCharField()
    gender = models.CharField(max_length=10, blank=True)
    nationality = models.CharField(max_length=80, blank=True)
    is_saudi = models.BooleanField(default=False)  # drives ×1.0 vs ×0.534 multiplier

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    classification = models.CharField(
        max_length=10, choices=Classification.choices, default=Classification.REGULAR
    )

    # Financials (🔒).
    basic = EncryptedDecimalField()
    housing = EncryptedDecimalField()
    transport = EncryptedDecimalField()
    bonus_vacation_pay = EncryptedDecimalField()
    eosb_accrual = EncryptedDecimalField()
    # Derived by the classification engine.
    section3_amount = EncryptedDecimalField(null=True, blank=True)
    section6_amount = EncryptedDecimalField(null=True, blank=True)
