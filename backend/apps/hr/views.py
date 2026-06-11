"""
HR (Sections 3 & 6) API viewsets. HR-RBAC-gated, tenant-scoped, year-lock protected.
"""
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import IsHR
from apps.common.views import TenantScopedViewSet
from apps.hr import services
from apps.hr.models import GosiCertificate, HrMonthlyUpload, PayrollRow
from apps.hr.serializers import (
    GosiCertificateSerializer,
    HrMonthlyUploadSerializer,
    PayrollRowSerializer,
)
from apps.tenancy.locking import YearLockWriteGuard


class HrUploadViewSet(TenantScopedViewSet):
    permission_classes = [IsHR, YearLockWriteGuard]
    serializer_class = HrMonthlyUploadSerializer
    queryset = HrMonthlyUpload.objects.all()

    @action(detail=True, methods=["post"])
    def parse(self, request, pk=None):
        """Async-parse the payroll Excel + GOSI PDFs and run the classification engine."""
        upload = self.get_object()
        from apps.hr.tasks import parse_payroll_upload

        parse_payroll_upload.delay(str(upload.id))
        upload.status = "PARSING"
        upload.save(update_fields=["status"])
        return Response({"status": upload.status}, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=["get"])
    def cross_check(self, request, pk=None):
        """GOSI cross-check: Excel row count vs summed Saudi+Expat headcount."""
        upload = self.get_object()
        result = services.gosi_cross_check(upload)
        return Response(
            {
                "row_count": result.row_count,
                "gosi_headcount": result.gosi_headcount,
                "matches": result.matches,
            },
            status=status.HTTP_200_OK if result.matches else status.HTTP_409_CONFLICT,
        )


class GosiCertificateViewSet(TenantScopedViewSet):
    permission_classes = [IsHR, YearLockWriteGuard]
    serializer_class = GosiCertificateSerializer
    queryset = GosiCertificate.objects.all()


class PayrollRowViewSet(TenantScopedViewSet):
    permission_classes = [IsHR, YearLockWriteGuard]
    serializer_class = PayrollRowSerializer
    queryset = PayrollRow.objects.all()

    def perform_create(self, serializer):
        row = serializer.save(tenant_id=self.request.user.tenant_id)
        services.apply_classification(row)  # split Section 3 / Section 6 on write
