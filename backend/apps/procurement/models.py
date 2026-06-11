"""
Module 3 — Procurement & Supply Chain (Section 4).

Smart column mapping (memorized per tenant), vendor directory with verified LC
scores, OCR-only certificate parsing (feeds the Global Whitelist), the ZATCA
Intelligence Engine (Local vs Foreign), the Top-40 / 70% optimizer, and the
Mandatory-List threshold alert engine (keyed by Etimad commodity code).
"""
from django.db import models

from apps.common.fields import EncryptedDecimalField
from apps.common.models import TenantScopedModel


class ProcMonthlyUpload(TenantScopedModel):
    compliance_year = models.ForeignKey(
        "tenancy.ComplianceYear", on_delete=models.CASCADE, related_name="proc_uploads"
    )
    contract = models.ForeignKey(
        "tenancy.Contract", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    month = models.PositiveSmallIntegerField()
    raw_file_ref = models.CharField(max_length=512, blank=True)
    status = models.CharField(max_length=20, default="PENDING")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "compliance_year", "month"], name="uq_proc_upload_slot"
            ),
        ]


class ColumnMapping(TenantScopedModel):
    """Remembers how a tenant's raw ERP columns map to system fields."""

    class SystemField(models.TextChoices):
        INVOICE_NO = "INVOICE_NO", "Invoice Number"
        VAT = "VAT", "VAT Number"
        GROSS = "GROSS", "Gross Amount"
        VAT_AMOUNT = "VAT_AMOUNT", "VAT Amount"

    source_field_name = models.CharField(max_length=255)
    system_field = models.CharField(max_length=20, choices=SystemField.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "system_field"], name="uq_colmap_field"),
        ]


class Vendor(TenantScopedModel):
    class Classification(models.TextChoices):
        LOCAL = "LOCAL", "Local Vendor"
        FOREIGN = "FOREIGN", "Foreign Vendor"

    class ScoreSource(models.TextChoices):
        CERT = "CERT", "Parsed LCGPA Certificate"
        GLOBAL_WHITELIST = "GLOBAL_WHITELIST", "Global Whitelist auto-fill"
        BASELINE = "BASELINE", "Baseline (sector / expired)"

    name = models.CharField(max_length=255)
    cr_number = models.CharField(max_length=20, blank=True)  # Unified National Number / CR
    vat_number = models.CharField(max_length=15, blank=True)
    classification = models.CharField(
        max_length=10, choices=Classification.choices, default=Classification.FOREIGN
    )
    verified_lc_score = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    lc_score_source = models.CharField(
        max_length=20, choices=ScoreSource.choices, default=ScoreSource.BASELINE
    )
    global_whitelist = models.ForeignKey(
        "seed.GlobalWhitelistEntry", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    def __str__(self):
        return self.name


class Invoice(TenantScopedModel):
    upload = models.ForeignKey(ProcMonthlyUpload, on_delete=models.CASCADE, related_name="invoices")
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, related_name="invoices")
    invoice_number = models.CharField(max_length=120)
    vat_number = models.CharField(max_length=15, blank=True)
    gross_amount = EncryptedDecimalField()
    vat_amount = EncryptedDecimalField()
    net_eligible_spend = EncryptedDecimalField(null=True, blank=True)


class InvoiceLine(TenantScopedModel):
    """Section 4 line item (real template columns) — drives mandatory/threshold checks."""

    class GoodsServices(models.TextChoices):
        GOODS = "GOODS", "Goods"
        SERVICES = "SERVICES", "Services"

    class Origin(models.TextChoices):
        LOCAL = "LOCAL", "Local"
        FOREIGN = "FOREIGN", "Foreign"

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="lines")
    description = models.CharField(max_length=512, blank=True)
    etimad_commodity = models.ForeignKey(
        "seed.EtimadCommodity", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    goods_or_services = models.CharField(max_length=10, choices=GoodsServices.choices, blank=True)
    local_or_foreign = models.CharField(max_length=10, choices=Origin.choices, blank=True)
    factory_manufactured = models.BooleanField(default=False)
    isic_sector = models.ForeignKey(
        "seed.IsicSector", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    audited_score = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)


class VendorLcgpaCertificate(TenantScopedModel):
    """Uploaded official certificate (OCR-only). Parsed fields feed the Global Whitelist."""

    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="certificates")
    file_ref = models.CharField(max_length=512)
    parsed_vendor_name = models.CharField(max_length=255, blank=True)
    parsed_cr_vat = models.CharField(max_length=20, blank=True)
    parsed_lc_score = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    is_expired = models.BooleanField(default=False)
    doc_ai_json = models.JSONField(null=True, blank=True)


class TopVendorSelection(TenantScopedModel):
    """Top-40 / 70% optimizer result (auto-selected, manual override allowed)."""

    compliance_year = models.ForeignKey(
        "tenancy.ComplianceYear", on_delete=models.CASCADE, related_name="top_vendor_selections"
    )
    selected_vendor_ids = models.JSONField(default=list)
    computed_lc_score = models.DecimalField(max_digits=6, decimal_places=4, null=True, blank=True)
    manual_override = models.BooleanField(default=False)


class ComplianceWarning(TenantScopedModel):
    class WarningType(models.TextChoices):
        MANDATORY_FOREIGN = "MANDATORY_FOREIGN", "Mandatory item from Foreign vendor"
        THRESHOLD = "THRESHOLD", "Below minimum LC threshold"

    compliance_year = models.ForeignKey(
        "tenancy.ComplianceYear", on_delete=models.CASCADE, related_name="compliance_warnings"
    )
    type = models.CharField(max_length=20, choices=WarningType.choices)
    etimad_code = models.CharField(max_length=32, blank=True)
    vendor = models.ForeignKey(
        Vendor, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    message = models.TextField(blank=True)
    raised_at = models.DateTimeField(auto_now_add=True)
