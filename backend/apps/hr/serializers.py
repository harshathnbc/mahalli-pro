"""DRF serializers for the HR (Sections 3 & 6) API. PII + money are 🔒 encrypted."""
from rest_framework import serializers

from apps.hr.models import GosiCertificate, HrMonthlyUpload, PayrollRow

_MONEY = dict(max_digits=18, decimal_places=2)


class HrMonthlyUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = HrMonthlyUpload
        fields = ["id", "compliance_year", "month", "status", "payroll_file_ref", "uploaded_at"]
        read_only_fields = ["status", "uploaded_at"]


class GosiCertificateSerializer(serializers.ModelSerializer):
    class Meta:
        model = GosiCertificate
        fields = [
            "id", "upload", "branch", "file_ref",
            "saudi_headcount", "expat_headcount", "parsed_at",
        ]
        read_only_fields = ["parsed_at"]


class PayrollRowSerializer(serializers.ModelSerializer):
    national_id = serializers.CharField()
    name = serializers.CharField()
    basic = serializers.DecimalField(**_MONEY)
    housing = serializers.DecimalField(**_MONEY)
    transport = serializers.DecimalField(**_MONEY)
    bonus_vacation_pay = serializers.DecimalField(**_MONEY)
    eosb_accrual = serializers.DecimalField(**_MONEY)
    section3_amount = serializers.DecimalField(**_MONEY, read_only=True)
    section6_amount = serializers.DecimalField(**_MONEY, read_only=True)

    class Meta:
        model = PayrollRow
        fields = [
            "id", "upload", "national_id", "name", "gender", "nationality", "is_saudi",
            "status", "classification", "basic", "housing", "transport",
            "bonus_vacation_pay", "eosb_accrual", "section3_amount", "section6_amount",
        ]
