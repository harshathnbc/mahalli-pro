"""
Module 8 — Export & Strategic Advisory (+ Module 10 cryptographic hashing).

Reports are two-dimensional: (level: ENTITY|CONTRACT) × (type: TARGET|PERIODIC|
FINAL|SCORE), matching the official template family. Export artifacts carry an
SHA-256 hash logged to the Master Audit Log so Big-4 auditors can verify integrity.
"""
from django.db import models

from apps.common.models import TenantScopedModel


class LcReport(TenantScopedModel):
    class Level(models.TextChoices):
        ENTITY = "ENTITY", "Entity Level"
        CONTRACT = "CONTRACT", "Contract Level"

    class Type(models.TextChoices):
        TARGET = "TARGET", "Target LC Score"
        PERIODIC = "PERIODIC", "Periodic Report"
        FINAL = "FINAL", "Final Report"
        SCORE = "SCORE", "LC Score"

    compliance_year = models.ForeignKey(
        "tenancy.ComplianceYear", on_delete=models.CASCADE, related_name="lc_reports"
    )
    contract = models.ForeignKey(
        "tenancy.Contract", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    level = models.CharField(max_length=10, choices=Level.choices)
    type = models.CharField(max_length=10, choices=Type.choices)
    state = models.CharField(max_length=20, default="DRAFT")
    computed_score = models.JSONField(null=True, blank=True)  # per-section breakdown
    created_at = models.DateTimeField(auto_now_add=True)


class ExportArtifact(TenantScopedModel):
    class Kind(models.TextChoices):
        SCORE_XLSX = "SCORE_XLSX", "LC Score .xlsx"
        TARGET_XLSX = "TARGET_XLSX", "Target .xlsx"
        PERIODIC_XLSX = "PERIODIC_XLSX", "Periodic/Final .xlsx"
        AUDIT_PACK_ZIP = "AUDIT_PACK_ZIP", "Audit Pack .zip"

    report = models.ForeignKey(LcReport, on_delete=models.CASCADE, related_name="artifacts")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    file_ref = models.CharField(max_length=512)
    sha256_hash = models.CharField(max_length=64, blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)


class SimulatorScenario(TenantScopedModel):
    """Siloed What-If / 10% price-preference Bidding Power calculator."""

    class Scope(models.TextChoices):
        SUPERADMIN = "SUPERADMIN", "Super Admin (cross-company)"
        PROCUREMENT = "PROCUREMENT", "Procurement (supply chain)"
        HR = "HR", "HR (Saudization)"

    scope = models.CharField(max_length=12, choices=Scope.choices)
    inputs = models.JSONField(default=dict)
    result = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
