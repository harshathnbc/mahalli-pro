"""Assets (Section 7) API. Finance-RBAC-gated, tenant-scoped, year-lock protected."""
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import IsFinance
from apps.assets import services
from apps.assets.models import Asset, AssetRegisterUpload
from apps.assets.serializers import AssetRegisterUploadSerializer, AssetSerializer
from apps.common.views import TenantScopedViewSet
from apps.finance.services import depreciation_from_tb
from apps.finance.models import TrialBalanceUpload
from apps.tenancy.locking import YearLockWriteGuard


class AssetRegisterViewSet(TenantScopedViewSet):
    permission_classes = [IsFinance, YearLockWriteGuard]
    serializer_class = AssetRegisterUploadSerializer
    queryset = AssetRegisterUpload.objects.prefetch_related("assets")

    @action(detail=True, methods=["get"])
    def reconcile(self, request, pk=None):
        """±5% check: register depreciation vs the Trial Balance depreciation expense."""
        register = self.get_object()
        tb = (
            TrialBalanceUpload.objects.filter(
                tenant_id=request.user.tenant_id,
                compliance_year=register.compliance_year,
            )
            .order_by("-uploaded_at")
            .first()
        )
        tb_dep = depreciation_from_tb(tb) if tb else 0
        from decimal import Decimal

        return Response(services.reconcile_with_tb(register, Decimal(str(tb_dep))))


class AssetViewSet(TenantScopedViewSet):
    permission_classes = [IsFinance, YearLockWriteGuard]
    serializer_class = AssetSerializer
    queryset = Asset.objects.all()

    def perform_create(self, serializer):
        asset = serializer.save(tenant_id=self.request.user.tenant_id)
        services.apply_in_kingdom_rule(asset)  # exclude non-KSA assets from the score
