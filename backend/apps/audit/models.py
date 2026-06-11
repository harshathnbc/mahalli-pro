"""
Module 1 — Master Audit Log.

A silent, permanent, append-only tracker of every mutating action across the
platform (liability protection). Immutability is enforced at the DB level by a
trigger that rejects UPDATE/DELETE (installed via `manage.py install_audit_guard`).
"""
import uuid

from django.db import models


class AuditAction(models.TextChoices):
    CREATE = "CREATE", "Create"
    READ = "READ", "Read"
    UPDATE = "UPDATE", "Update"
    DELETE = "DELETE", "Delete"


class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Nullable so Master-Admin (no tenant) actions are still captured.
    tenant = models.ForeignKey(
        "tenancy.Tenant", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    actor = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    action = models.CharField(max_length=10, choices=AuditAction.choices)
    entity_type = models.CharField(max_length=120, blank=True)
    entity_id = models.CharField(max_length=64, blank=True)
    method = models.CharField(max_length=10, blank=True)
    path = models.CharField(max_length=512, blank=True)
    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    ts = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "ts"]),
            models.Index(fields=["entity_type", "entity_id"]),
        ]
        ordering = ["-ts"]
