"""
Abstract base models. Every concrete model uses a UUID PK; tenant-scoped models
carry `tenant` and are protected by PostgreSQL Row-Level Security (see middleware
and apps.common.rls). RLS is the database-level backstop under the DRF RBAC layer.
"""
import uuid

from django.db import models


class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class BaseModel(UUIDModel, TimeStampedModel):
    class Meta:
        abstract = True


class TenantScopedModel(BaseModel):
    """
    Rows belong to exactly one tenant. A post-migrate hook (apps.common.rls)
    enables an RLS policy on each concrete table:

        USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
    """

    tenant = models.ForeignKey(
        "tenancy.Tenant",
        on_delete=models.CASCADE,
        related_name="+",
    )

    class Meta:
        abstract = True
