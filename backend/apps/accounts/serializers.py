"""Serializers for the Master Admin control plane."""
from rest_framework import serializers

from apps.audit.models import AuditLog
from apps.tenancy.models import Tenant


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = [
            "id", "name", "primary_cr_number", "subscription_tier", "status",
            "billing_status", "max_employees", "max_vendors", "hold_flag", "created_at",
        ]
        read_only_fields = ["created_at"]


class ProvisionTenantSerializer(serializers.Serializer):
    """Input for the 4-step Concierge Onboarding wizard."""

    name = serializers.CharField()
    cr_number = serializers.RegexField(r"^\d{10}$")
    compliance_years = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)
    branch_crs = serializers.ListField(
        child=serializers.RegexField(r"^\d{10}$"), required=False, default=list
    )
    billing_contact = serializers.CharField(required=False, allow_blank=True, default="")
    billing_email = serializers.EmailField()
    billing_mobile = serializers.CharField(required=False, allow_blank=True, default="")
    admin_email = serializers.EmailField()
    subscription_tier = serializers.ChoiceField(
        choices=["STARTER", "GROWTH", "ENTERPRISE"], default="STARTER"
    )
    max_employees = serializers.IntegerField(min_value=0, default=0)
    max_vendors = serializers.IntegerField(min_value=0, default=0)


class SoftHoldSerializer(serializers.Serializer):
    hold = serializers.BooleanField()


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = [
            "id", "tenant", "actor", "action", "entity_type", "entity_id",
            "method", "path", "ip", "ts",
        ]
        read_only_fields = fields
