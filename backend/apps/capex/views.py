"""CAPEX (Section 5) API. Finance-RBAC-gated, tenant-scoped, year-lock protected."""
from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import IsFinance
from apps.capex import services
from apps.capex.models import CapexItem
from apps.capex.serializers import CapexItemSerializer
from apps.common.views import TenantScopedViewSet
from apps.tenancy.locking import YearLockWriteGuard
from apps.tenancy.models import ComplianceYear


class CapexItemViewSet(TenantScopedViewSet):
    permission_classes = [IsFinance, YearLockWriteGuard]
    serializer_class = CapexItemSerializer
    queryset = CapexItem.objects.all()


class CapexSummaryViewSet(viewsets.ViewSet):
    permission_classes = [IsFinance]

    @action(detail=True, methods=["get"])
    def summary(self, request, pk=None):
        """Total vs locally-eligible CAPEX for a compliance year."""
        year = get_object_or_404(ComplianceYear, pk=pk, tenant_id=request.user.tenant_id)
        return Response(services.aggregate_capex(request.user.tenant, year))
