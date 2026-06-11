"""
Procurement (Section 4) API viewsets. All endpoints require the Procurement role
(or Super/Company Admin) and are tenant-scoped.
"""
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import IsProcurement
from apps.common.views import TenantScopedViewSet
from apps.procurement import services
from apps.procurement.models import (
    ColumnMapping,
    ComplianceWarning,
    Invoice,
    ProcMonthlyUpload,
    TopVendorSelection,
    Vendor,
    VendorLcgpaCertificate,
)
from apps.procurement.serializers import (
    ColumnMappingSerializer,
    ComplianceWarningSerializer,
    InvoiceSerializer,
    ProcMonthlyUploadSerializer,
    TopVendorSelectionSerializer,
    VendorCertificateSerializer,
    VendorSerializer,
)
from apps.tenancy.models import ComplianceYear


class VendorViewSet(TenantScopedViewSet):
    permission_classes = [IsProcurement]
    serializer_class = VendorSerializer
    queryset = Vendor.objects.all()

    def perform_create(self, serializer):
        # ZATCA Intelligence Engine sets classification at write time.
        vat = serializer.validated_data.get("vat_number", "")
        serializer.save(
            tenant_id=self.request.user.tenant_id,
            classification=services.classify_vendor(vat),
        )

    @action(detail=True, methods=["post"])
    def resolve_score(self, request, pk=None):
        """Resolve & persist the vendor's LC score (cert > whitelist > baseline)."""
        vendor = self.get_object()
        score, source = services.resolve_vendor_lc_score(vendor)
        vendor.verified_lc_score = score
        vendor.lc_score_source = source
        vendor.save(update_fields=["verified_lc_score", "lc_score_source"])
        return Response({"verified_lc_score": score, "lc_score_source": source})


class ColumnMappingViewSet(TenantScopedViewSet):
    permission_classes = [IsProcurement]
    serializer_class = ColumnMappingSerializer
    queryset = ColumnMapping.objects.all()


class ProcUploadViewSet(TenantScopedViewSet):
    permission_classes = [IsProcurement]
    serializer_class = ProcMonthlyUploadSerializer
    queryset = ProcMonthlyUpload.objects.all()

    @action(detail=True, methods=["post"])
    def parse(self, request, pk=None):
        """Kick off async parsing of the raw ERP export for this upload."""
        upload = self.get_object()
        from apps.procurement.tasks import parse_invoice_upload

        parse_invoice_upload.delay(str(upload.id))
        upload.status = "PARSING"
        upload.save(update_fields=["status"])
        return Response({"status": upload.status}, status=status.HTTP_202_ACCEPTED)


class InvoiceViewSet(TenantScopedViewSet):
    permission_classes = [IsProcurement]
    serializer_class = InvoiceSerializer
    queryset = Invoice.objects.prefetch_related("lines").select_related("vendor")


class VendorCertificateViewSet(TenantScopedViewSet):
    permission_classes = [IsProcurement]
    serializer_class = VendorCertificateSerializer
    queryset = VendorLcgpaCertificate.objects.all()

    @action(detail=True, methods=["post"])
    def parse(self, request, pk=None):
        """OCR the certificate via Document AI, then auto-enrich the Global Whitelist."""
        cert = self.get_object()
        from apps.procurement.tasks import parse_vendor_certificate

        parse_vendor_certificate.delay(str(cert.id))
        return Response({"status": "PARSING"}, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=["post"])
    def push_to_whitelist(self, request, pk=None):
        """After OCR parsing, push the verified cert to the Global Whitelist."""
        cert = self.get_object()
        try:
            entry = services.push_certificate_to_whitelist(
                vat_number=cert.parsed_cr_vat,
                cr_number=cert.parsed_cr_vat,
                vendor_name=cert.parsed_vendor_name,
                lc_score=cert.parsed_lc_score,
                expiry_date=cert.expiry_date,
                financial_year=cert.expiry_date.year if cert.expiry_date else None,
                source_tenant_id=request.user.tenant_id,
            )
        except services.WhitelistRegression as exc:
            return Response(
                {
                    "detail": str(exc),
                    "current_version": exc.existing.version,
                    "current_expiry": exc.existing.certificate_expiry_date,
                },
                status=status.HTTP_409_CONFLICT,
            )
        return Response({"whitelist_id": entry.id, "version": entry.version})


class ComplianceWarningViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsProcurement]
    serializer_class = ComplianceWarningSerializer

    def get_queryset(self):
        return ComplianceWarning.objects.filter(tenant_id=self.request.user.tenant_id)


class YearAnalysisViewSet(viewsets.ViewSet):
    """Year-end engines: mandatory checks and the Top-40 / 70% optimizer."""

    permission_classes = [IsProcurement]

    def _year(self, request, pk):
        return get_object_or_404(
            ComplianceYear, pk=pk, tenant_id=request.user.tenant_id
        )

    @action(detail=True, methods=["post"])
    def mandatory_checks(self, request, pk=None):
        year = self._year(request, pk)
        warnings = services.run_mandatory_checks(request.user.tenant, year)
        return Response(ComplianceWarningSerializer(warnings, many=True).data)

    @action(detail=True, methods=["post"])
    def top40(self, request, pk=None):
        year = self._year(request, pk)
        selection = services.run_top40(request.user.tenant, year)
        return Response(TopVendorSelectionSerializer(selection).data)
