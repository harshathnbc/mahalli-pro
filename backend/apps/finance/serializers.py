"""DRF serializers for the Finance (Appendix A) API. 🔒 columns surface as Decimals."""
from rest_framework import serializers

from apps.finance.models import (
    AnnualHardClose,
    EvidenceVault,
    MonthlySoftClose,
    ReconciliationCheck,
    TbAccountMapping,
    TrialBalanceUpload,
)

_MONEY = dict(max_digits=18, decimal_places=2)


class MonthlySoftCloseSerializer(serializers.ModelSerializer):
    total_salaries = serializers.DecimalField(**_MONEY)
    total_purchases = serializers.DecimalField(**_MONEY)

    class Meta:
        model = MonthlySoftClose
        fields = [
            "id", "compliance_year", "month", "total_salaries", "total_purchases",
            "hr_variance", "proc_variance",
        ]
        read_only_fields = ["hr_variance", "proc_variance"]


class AnnualHardCloseSerializer(serializers.ModelSerializer):
    revenues = serializers.DecimalField(**_MONEY)
    direct_costs = serializers.DecimalField(**_MONEY)
    gna = serializers.DecimalField(**_MONEY)
    selling_distribution = serializers.DecimalField(**_MONEY)
    finance_costs = serializers.DecimalField(**_MONEY)

    class Meta:
        model = AnnualHardClose
        fields = [
            "id", "compliance_year", "revenues", "direct_costs", "gna",
            "selling_distribution", "finance_costs", "state", "reconciliation_passed",
        ]
        read_only_fields = ["state", "reconciliation_passed"]


class TbAccountMappingSerializer(serializers.ModelSerializer):
    amount = serializers.DecimalField(**_MONEY)

    class Meta:
        model = TbAccountMapping
        fields = ["id", "trial_balance", "account_code", "account_name", "mapped_category", "amount"]


class TrialBalanceUploadSerializer(serializers.ModelSerializer):
    account_mappings = TbAccountMappingSerializer(many=True, read_only=True)

    class Meta:
        model = TrialBalanceUpload
        fields = ["id", "compliance_year", "raw_file_ref", "uploaded_at", "account_mappings"]
        read_only_fields = ["uploaded_at"]


class ReconciliationCheckSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReconciliationCheck
        fields = ["id", "compliance_year", "scope", "variance_pct", "passed", "checked_at"]


class EvidenceVaultSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvidenceVault
        fields = ["id", "compliance_year", "doc_type", "file_ref", "uploaded_at"]
        read_only_fields = ["uploaded_at"]
