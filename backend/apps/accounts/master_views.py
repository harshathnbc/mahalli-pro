"""
Master Admin control plane (Tier 1) API — `/api/master/`.

These endpoints are NOT tenant-scoped: the Master Admin operates across every
tenant. Querysets run on the privileged DB alias (settings.MASTER_DB_ALIAS), which
bypasses Row-Level Security so the platform owner can see all companies.
"""
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts import provisioning
from apps.accounts.permissions import IsMasterAdmin
from apps.accounts.serializers import (
    AuditLogSerializer,
    ProvisionTenantSerializer,
    SoftHoldSerializer,
    TenantSerializer,
)
from apps.audit.models import AuditLog
from apps.tenancy.models import Tenant

_DB = settings.MASTER_DB_ALIAS


class ProvisionTenantView(APIView):
    """Concierge Onboarding — the 4-step Tenant Provisioning Wizard."""

    permission_classes = [IsMasterAdmin]

    def post(self, request):
        serializer = ProvisionTenantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = provisioning.create_tenant_with_admin(**serializer.validated_data)
        return Response(result, status=status.HTTP_201_CREATED)


class TenantControlViewSet(viewsets.ReadOnlyModelViewSet):
    """Global Tenant Control Center — view/search/filter every company."""

    permission_classes = [IsMasterAdmin]
    serializer_class = TenantSerializer

    def get_queryset(self):
        qs = Tenant.objects.using(_DB).all().order_by("name")
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(name__icontains=search)
        billing = self.request.query_params.get("billing_status")
        if billing:
            qs = qs.filter(billing_status=billing)
        return qs

    @action(detail=True, methods=["post"])
    def soft_hold(self, request, pk=None):
        """Toggle the billing Soft-Hold (lock out / restore an entire tenant)."""
        tenant = get_object_or_404(Tenant.objects.using(_DB), pk=pk)
        serializer = SoftHoldSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        provisioning.toggle_soft_hold(tenant, hold=serializer.validated_data["hold"])
        return Response({"status": tenant.status, "hold_flag": tenant.hold_flag})

    @action(detail=True, methods=["post"])
    def ghost_login(self, request, pk=None):
        """Log In As Tenant — issue an impersonation token for the tenant Super Admin."""
        tenant = get_object_or_404(Tenant.objects.using(_DB), pk=pk)
        try:
            result = provisioning.start_ghost_login(master_admin=request.user, tenant=tenant)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(result)


class MasterAuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Master Audit Log — every CRUD action across the platform (append-only)."""

    permission_classes = [IsMasterAdmin]
    serializer_class = AuditLogSerializer

    def get_queryset(self):
        qs = AuditLog.objects.using(_DB).all()
        tenant_id = self.request.query_params.get("tenant")
        return qs.filter(tenant_id=tenant_id) if tenant_id else qs
