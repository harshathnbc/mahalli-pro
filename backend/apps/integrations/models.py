"""
Module 10 — Enterprise Integration Layer (Phase 2 roadmap stubs).

Cryptographic audit hashing lives on reports.ExportArtifact. Here we stub the
Certified Auditor Portal (time-limited read-only links) and the ERP API Gateway
(webhook endpoints + API keys for Odoo/SAP/Dynamics/Microtec).
"""
import uuid

from django.db import models

from apps.common.models import TenantScopedModel


class AuditorPortalLink(TenantScopedModel):
    """Secure, time-limited, read-only link for an external certified CPA."""

    compliance_year = models.ForeignKey(
        "tenancy.ComplianceYear", on_delete=models.CASCADE, related_name="auditor_links"
    )
    token = models.CharField(max_length=64, unique=True, default=uuid.uuid4)
    expires_at = models.DateTimeField()
    read_only = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )


class WebhookEndpoint(TenantScopedModel):
    url = models.URLField()
    secret = models.CharField(max_length=128, blank=True)
    events = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)


class ApiKey(TenantScopedModel):
    hashed_key = models.CharField(max_length=128)
    label = models.CharField(max_length=120, blank=True)
    scopes = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
