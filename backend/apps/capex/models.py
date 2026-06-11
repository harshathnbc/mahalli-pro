"""
Section 5 — Capital Expenditures (CAPEX).

A full LCGPA section that the architecture doc omitted but the official
"Local Content Score Template - v.2.xlsx" includes (sheet "Section 5. CAPEX").
Columns mirror the real template line item.
"""
from django.db import models

from apps.common.fields import EncryptedDecimalField
from apps.common.models import TenantScopedModel


class CapexItem(TenantScopedModel):
    class GoodsServices(models.TextChoices):
        GOODS = "GOODS", "Goods"
        SERVICES = "SERVICES", "Services"

    class Origin(models.TextChoices):
        LOCAL = "LOCAL", "Local"
        FOREIGN = "FOREIGN", "Foreign"

    compliance_year = models.ForeignKey(
        "tenancy.ComplianceYear", on_delete=models.CASCADE, related_name="capex_items"
    )
    contract = models.ForeignKey(
        "tenancy.Contract", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    asset_type = models.CharField(max_length=255)
    description = models.CharField(max_length=512, blank=True)
    supplier_name = models.CharField(max_length=255, blank=True)
    supplier_cr = models.CharField(max_length=20, blank=True)
    goods_or_services = models.CharField(max_length=10, choices=GoodsServices.choices, blank=True)
    local_or_foreign = models.CharField(max_length=10, choices=Origin.choices, blank=True)
    factory_manufactured = models.BooleanField(default=False)
    isic_sector = models.ForeignKey(
        "seed.IsicSector", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    amount = EncryptedDecimalField()
    audited_score = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
