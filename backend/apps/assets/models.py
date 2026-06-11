"""
Module 5 — Assets & Depreciation (Section 7).

Asset register with mandatory In-Kingdom validation (Operating in KSA? No -> excluded
from the score) and a ±5% cross-check against the TB depreciation expense from Module 4.
"""
from django.db import models

from apps.common.fields import EncryptedDecimalField
from apps.common.models import TenantScopedModel


class AssetRegisterUpload(TenantScopedModel):
    compliance_year = models.ForeignKey(
        "tenancy.ComplianceYear", on_delete=models.CASCADE, related_name="asset_registers"
    )
    file_ref = models.CharField(max_length=512)
    uploaded_at = models.DateTimeField(auto_now_add=True)


class Asset(TenantScopedModel):
    class Origin(models.TextChoices):
        LOCAL = "LOCAL", "Local"
        FOREIGN = "FOREIGN", "Foreign"

    register = models.ForeignKey(
        AssetRegisterUpload, on_delete=models.CASCADE, related_name="assets"
    )
    asset_id_label = models.CharField(max_length=120)
    asset_class = models.CharField(max_length=255, blank=True)
    supplier_cr = models.CharField(max_length=20, blank=True)
    origin = models.CharField(max_length=10, blank=True)
    local_or_foreign = models.CharField(max_length=10, choices=Origin.choices, blank=True)
    annual_depreciation = EncryptedDecimalField()
    operating_in_ksa = models.BooleanField(default=True)
    included_in_score = models.BooleanField(default=True)
