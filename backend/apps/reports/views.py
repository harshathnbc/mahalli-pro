"""
Reports & Export (Module 8) API. Company-Admin/Export RBAC, tenant-scoped.

Export actions are blocked (409 Red Light) until the Annual Hard-Close passes the
±5% reconciliation — enforced in the service layer via ExportBlocked.
"""
from decimal import Decimal

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import IsExport
from apps.common.views import TenantScopedViewSet
from apps.reports import services
from apps.reports.models import LcReport, SimulatorScenario
from apps.reports.serializers import (
    ExportArtifactSerializer,
    LcReportSerializer,
    SimulatorScenarioSerializer,
)


class LcReportViewSet(TenantScopedViewSet):
    permission_classes = [IsExport]
    serializer_class = LcReportSerializer
    queryset = LcReport.objects.prefetch_related("artifacts")

    def perform_create(self, serializer):
        report = serializer.save(tenant_id=self.request.user.tenant_id)
        # Snapshot the assembled section score at report creation.
        report.computed_score = _to_strs(
            services.assemble_score(report.tenant, report.compliance_year)
        )
        report.save(update_fields=["computed_score"])

    @action(detail=True, methods=["post"])
    def generate(self, request, pk=None):
        """Populate the official template .xlsx (the Victory Screen export)."""
        report = self.get_object()
        try:
            artifact = services.generate_score_xlsx(report)
        except services.ExportBlocked as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(ExportArtifactSerializer(artifact).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def audit_pack(self, request, pk=None):
        """Build the SHA-256-hashed Audit Pack .zip for external auditors."""
        report = self.get_object()
        try:
            artifact = services.build_audit_pack(report)
        except services.ExportBlocked as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(ExportArtifactSerializer(artifact).data, status=status.HTTP_201_CREATED)


class SimulatorViewSet(TenantScopedViewSet):
    permission_classes = [IsExport]
    serializer_class = SimulatorScenarioSerializer
    queryset = SimulatorScenario.objects.all()

    @action(detail=False, methods=["post"])
    def bidding_power(self, request):
        """10% price-preference Bidding Power calculator."""
        shifted = Decimal(str(request.data.get("shifted_spend", "0")))
        scope = request.data.get("scope", SimulatorScenario.Scope.SUPERADMIN)
        scenario = services.run_bidding_simulator(
            request.user.tenant, shifted_spend=shifted, scope=scope
        )
        return Response(SimulatorScenarioSerializer(scenario).data, status=status.HTTP_201_CREATED)


def _to_strs(score: dict) -> dict:
    """JSON-serialize Decimals from the score dict for storage in computed_score."""
    return {
        "sections": {k: str(v) for k, v in score.get("sections", {}).items()},
        "total": str(score.get("total", "0")),
    }
