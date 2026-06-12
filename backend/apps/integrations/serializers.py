"""Serializers for the Enterprise Integration Layer (Module 10)."""
from rest_framework import serializers

from apps.integrations.models import ApiKey, AuditorPortalLink, WebhookEndpoint


class AuditorPortalLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditorPortalLink
        fields = ["id", "compliance_year", "token", "expires_at", "read_only", "created_by"]
        read_only_fields = ["token", "expires_at", "read_only", "created_by"]


class WebhookEndpointSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookEndpoint
        fields = ["id", "url", "events", "is_active"]
        # secret is write-only; never echo it back.
        extra_kwargs = {"secret": {"write_only": True}}


class ApiKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = ApiKey
        fields = ["id", "label", "scopes", "is_active"]
        read_only_fields = ["is_active"]
