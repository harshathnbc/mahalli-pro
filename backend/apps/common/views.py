"""Shared DRF base classes."""
from rest_framework import viewsets


class TenantScopedViewSet(viewsets.ModelViewSet):
    """
    Restricts the queryset to the requesting user's tenant and stamps `tenant` on
    create. RLS enforces the same boundary at the database; this keeps the ORM
    layer honest and gives clean 404s instead of relying solely on RLS.
    """

    def get_queryset(self):
        qs = super().get_queryset()
        tenant_id = getattr(self.request.user, "tenant_id", None)
        return qs.filter(tenant_id=tenant_id) if tenant_id else qs.none()

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.user.tenant_id)
