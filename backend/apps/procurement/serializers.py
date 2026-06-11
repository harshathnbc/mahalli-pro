"""
DRF serializers for the Procurement (Section 4) API.

Encrypted 🔒 columns surface as ordinary Decimal fields here — the model layer
transparently encrypts on write and decrypts on read.
"""
from rest_framework import serializers

from apps.procurement.models import (
    ColumnMapping,
    ComplianceWarning,
    Invoice,
    InvoiceLine,
    ProcMonthlyUpload,
    TopVendorSelection,
    Vendor,
    VendorLcgpaCertificate,
)

_MONEY = dict(max_digits=18, decimal_places=2)


class VendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = [
            "id", "name", "cr_number", "vat_number", "classification",
            "verified_lc_score", "lc_score_source", "global_whitelist",
        ]
        # Classification + score are system-derived, never client-set.
        read_only_fields = ["classification", "lc_score_source", "global_whitelist"]


class ColumnMappingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ColumnMapping
        fields = ["id", "source_field_name", "system_field"]


class ProcMonthlyUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcMonthlyUpload
        fields = ["id", "compliance_year", "contract", "month", "raw_file_ref", "status", "uploaded_at"]
        read_only_fields = ["status", "uploaded_at"]


class InvoiceLineSerializer(serializers.ModelSerializer):
    audited_score = serializers.DecimalField(max_digits=5, decimal_places=4, required=False, allow_null=True)

    class Meta:
        model = InvoiceLine
        fields = [
            "id", "description", "etimad_commodity", "goods_or_services",
            "local_or_foreign", "factory_manufactured", "isic_sector", "audited_score",
        ]


class InvoiceSerializer(serializers.ModelSerializer):
    gross_amount = serializers.DecimalField(**_MONEY)
    vat_amount = serializers.DecimalField(**_MONEY)
    net_eligible_spend = serializers.DecimalField(**_MONEY, required=False, allow_null=True)
    lines = InvoiceLineSerializer(many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id", "upload", "vendor", "invoice_number", "vat_number",
            "gross_amount", "vat_amount", "net_eligible_spend", "lines",
        ]


class VendorCertificateSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorLcgpaCertificate
        fields = [
            "id", "vendor", "file_ref", "parsed_vendor_name", "parsed_cr_vat",
            "parsed_lc_score", "expiry_date", "is_expired",
        ]
        read_only_fields = [
            "parsed_vendor_name", "parsed_cr_vat", "parsed_lc_score", "expiry_date", "is_expired",
        ]


class ComplianceWarningSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplianceWarning
        fields = ["id", "compliance_year", "type", "etimad_code", "vendor", "message", "raised_at"]


class TopVendorSelectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TopVendorSelection
        fields = ["id", "compliance_year", "selected_vendor_ids", "computed_lc_score", "manual_override"]
