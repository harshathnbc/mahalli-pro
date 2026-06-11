"""
Seed & global (cross-tenant) data — Section 2 of the architecture doc, grounded in
the real LCGPA files:

  • IsicSector            <- "Local Content Score Template - v.2.xlsx" / Appendix B
  • EtimadCommodity       <- "Mandatory List of Government Entities (Jan 2026).xlsx"
  • MandatoryMinThreshold <- "The minimum percentage ... February 2026.xlsx"
  • GlobalWhitelistEntry  <- self-enriching network-effect dictionary (+SABIC/Aramco/STC)
  • TemplateVault         <- blank official .xlsx + cell-coordinate mappings

These are GLOBAL tables (no tenant_id, RLS-exempt).
"""
import uuid
from decimal import Decimal

from django.db import models


class IsicSector(models.Model):
    """Appendix B sector with its baseline Local Content Score (the multiplier)."""

    class Kind(models.TextChoices):
        GOODS = "GOODS", "Goods"
        SERVICES = "SERVICES", "Services"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=120, unique=True)  # e.g. "4_SERVICES - KSA Security Services"
    name_en = models.CharField(max_length=255, blank=True)
    name_ar = models.CharField(max_length=255, blank=True)
    kind = models.CharField(max_length=10, choices=Kind.choices, blank=True)
    baseline_lc_score = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal("0"))
    description = models.TextField(blank=True)
    compliance_year = models.PositiveSmallIntegerField(null=True, blank=True)

    def __str__(self):
        return self.code


class EtimadCommodity(models.Model):
    """A product on the LCGPA Mandatory List, keyed by its Etimad platform code."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    etimad_code = models.CharField(max_length=32, db_index=True)
    segment_no = models.CharField(max_length=32, blank=True)
    sector_sheet = models.CharField(max_length=255, blank=True)
    name_ar = models.CharField(max_length=512, blank=True)
    name_en = models.CharField(max_length=512, blank=True)
    desc_ar = models.TextField(blank=True)
    desc_en = models.TextField(blank=True)
    is_mandatory = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=["etimad_code"])]
        constraints = [
            models.UniqueConstraint(fields=["etimad_code", "sector_sheet"], name="uq_etimad_code_sheet"),
        ]

    def __str__(self):
        return f"{self.etimad_code} {self.name_en}"


class MandatoryMinThreshold(models.Model):
    """Per-year minimum local-content % for a mandatory-list product (2026/27/28...)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    etimad_code = models.CharField(max_length=32, db_index=True)
    year = models.PositiveSmallIntegerField()
    min_pct = models.DecimalField(max_digits=5, decimal_places=4)
    effective_date = models.DateField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["etimad_code", "year"], name="uq_threshold_code_year"),
        ]


class GlobalWhitelistEntry(models.Model):
    """
    The self-enriching, cross-tenant verified-vendor dictionary (the data moat).

    Whenever any tenant uploads a valid LCGPA certificate, the verified LC score +
    VAT are pushed here so other tenants auto-fill accurately — WITHOUT exposing the
    originating tenant's identity or spend (`_source_tenant` is internal-only and
    never serialized to any tenant).

    Conflict resolution: a newer certificate (later expiry / financial year) wins;
    older uploads are rejected to prevent data regression.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vat_number = models.CharField(max_length=15, unique=True)
    cr_number = models.CharField(max_length=10, blank=True)
    vendor_name_norm = models.CharField(max_length=512, db_index=True)  # trigram index added in migration
    lc_score = models.DecimalField(max_digits=5, decimal_places=4)
    certificate_expiry_date = models.DateField(null=True, blank=True)
    financial_year = models.PositiveSmallIntegerField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)
    source_cert_sha256 = models.CharField(max_length=64, blank=True)
    verified_at = models.DateTimeField(auto_now=True)
    # Internal provenance only — never exposed to tenants.
    _source_tenant = models.ForeignKey(
        "tenancy.Tenant", null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
        db_column="source_tenant_id",
    )

    def __str__(self):
        return f"{self.vendor_name_norm} ({self.vat_number})"


class TemplateVault(models.Model):
    """Blank official LCGPA workbooks, owned exclusively by the Master Admin."""

    class TemplateKey(models.TextChoices):
        LC_SCORE_V2 = "LC_SCORE_V2", "Local Content Score Template v2"
        TARGET_ENTITY = "TARGET_ENTITY", "Target LC Score (Entity Level)"
        TARGET_CONTRACT = "TARGET_CONTRACT", "Target LC Score (Contract Level)"
        PERIODIC_CONTRACT = "PERIODIC_CONTRACT", "Periodic / Final Report (Contract Level)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template_key = models.CharField(max_length=30, choices=TemplateKey.choices)
    compliance_year = models.PositiveSmallIntegerField()
    file_ref = models.CharField(max_length=512)  # object-storage key
    uploaded_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["template_key", "compliance_year"], name="uq_template_key_year"),
        ]


class TemplateCellMapping(models.Model):
    """Maps a system variable to an exact worksheet cell in a vault template."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(TemplateVault, on_delete=models.CASCADE, related_name="cell_mappings")
    system_variable = models.CharField(max_length=120)
    sheet_name = models.CharField(max_length=120)
    cell_coordinate = models.CharField(max_length=16)  # e.g. "C10"
