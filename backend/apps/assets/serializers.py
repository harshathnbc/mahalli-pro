"""DRF serializers for Assets (Section 7). annual_depreciation is 🔒 encrypted."""
from rest_framework import serializers

from apps.assets.models import Asset, AssetRegisterUpload


class AssetSerializer(serializers.ModelSerializer):
    annual_depreciation = serializers.DecimalField(max_digits=18, decimal_places=2)

    class Meta:
        model = Asset
        fields = [
            "id", "register", "asset_id_label", "asset_class", "supplier_cr",
            "origin", "local_or_foreign", "annual_depreciation",
            "operating_in_ksa", "included_in_score",
        ]
        read_only_fields = ["included_in_score"]


class AssetRegisterUploadSerializer(serializers.ModelSerializer):
    assets = AssetSerializer(many=True, read_only=True)

    class Meta:
        model = AssetRegisterUpload
        fields = ["id", "compliance_year", "file_ref", "uploaded_at", "assets"]
        read_only_fields = ["uploaded_at"]
