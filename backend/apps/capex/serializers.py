"""DRF serializers for CAPEX (Section 5). The amount column is 🔒 encrypted."""
from rest_framework import serializers

from apps.capex.models import CapexItem


class CapexItemSerializer(serializers.ModelSerializer):
    amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    audited_score = serializers.DecimalField(
        max_digits=5, decimal_places=4, required=False, allow_null=True
    )

    class Meta:
        model = CapexItem
        fields = [
            "id", "compliance_year", "contract", "asset_type", "description",
            "supplier_name", "supplier_cr", "goods_or_services", "local_or_foreign",
            "factory_manufactured", "isic_sector", "amount", "audited_score",
        ]
