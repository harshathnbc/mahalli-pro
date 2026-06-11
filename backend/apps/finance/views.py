"""
Finance (Appendix A) API viewsets. Finance-RBAC-gated, tenant-scoped, and protected
by the Immutable Data Lock guard (writes denied once the year is LOCKED).
"""
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import IsFinance
from apps.common.views import TenantScopedViewSet
from apps.finance import services
from apps.finance.models import (
    AnnualHardClose,
    EvidenceVault,
    MonthlySoftClose,
    ReconciliationCheck,
    TbAccountMapping,
    TrialBalanceUpload,
)
from apps.finance.serializers import (
    AnnualHardCloseSerializer,
    EvidenceVaultSerializer,
    MonthlySoftCloseSerializer,
    ReconciliationCheckSerializer,
    TbAccountMappingSerializer,
    TrialBalanceUploadSerializer,
)
from apps.tenancy.locking import YearLockWriteGuard
from apps.tenancy.models import ComplianceYear


class SoftCloseViewSet(TenantScopedViewSet):
    permission_classes = [IsFinance, YearLockWriteGuard]
    serializer_class = MonthlySoftCloseSerializer
    queryset = MonthlySoftClose.objects.all()

    def perform_create(self, serializer):
        instance = serializer.save(tenant_id=self.request.user.tenant_id)
        # Instantly check HR/Proc uploads against the typed numbers (flag errors early).
        services.run_monthly_reconciliation(instance)


class HardCloseViewSet(TenantScopedViewSet):
    permission_classes = [IsFinance, YearLockWriteGuard]
    serializer_class = AnnualHardCloseSerializer
    queryset = AnnualHardClose.objects.all()

    @action(detail=True, methods=["post"])
    def reconcile(self, request, pk=None):
        """Run the annual ±5% Strict Block. Red Light blocks export when it fails."""
        hard_close = self.get_object()
        check = services.run_annual_reconciliation(hard_close)
        return Response(
            {
                "passed": check.passed,
                "variance_pct": check.variance_pct,
                "export_unlocked": check.passed,
            },
            status=status.HTTP_200_OK if check.passed else status.HTTP_409_CONFLICT,
        )


class TrialBalanceViewSet(TenantScopedViewSet):
    permission_classes = [IsFinance, YearLockWriteGuard]
    serializer_class = TrialBalanceUploadSerializer
    queryset = TrialBalanceUpload.objects.prefetch_related("account_mappings")

    @action(detail=True, methods=["get"])
    def ceiling(self, request, pk=None):
        """LCGPA ceiling = base minus statutory exemptions (Zakat/Customs/Visa)."""
        tb = self.get_object()
        return Response(
            {
                "ceiling": services.compute_ceiling(tb),
                "depreciation": services.depreciation_from_tb(tb),
            }
        )


class TbAccountMappingViewSet(TenantScopedViewSet):
    permission_classes = [IsFinance, YearLockWriteGuard]
    serializer_class = TbAccountMappingSerializer
    queryset = TbAccountMapping.objects.all()


class EvidenceVaultViewSet(TenantScopedViewSet):
    permission_classes = [IsFinance, YearLockWriteGuard]
    serializer_class = EvidenceVaultSerializer
    queryset = EvidenceVault.objects.all()


class ReconciliationViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsFinance]
    serializer_class = ReconciliationCheckSerializer

    def get_queryset(self):
        return ReconciliationCheck.objects.filter(tenant_id=self.request.user.tenant_id)


class YearCloseViewSet(viewsets.ViewSet):
    """The Immutable Data Lock action."""

    permission_classes = [IsFinance]

    @action(detail=True, methods=["post"])
    def lock(self, request, pk=None):
        year = get_object_or_404(
            ComplianceYear, pk=pk, tenant_id=request.user.tenant_id
        )
        try:
            services.lock_compliance_year(year)
        except services.HardCloseNotPassed as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response({"state": year.state, "locked_at": year.locked_at})
