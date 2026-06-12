"""
Enterprise Integration Layer API (Module 10).

Internal management endpoints are Company-Admin/Export gated and tenant-scoped.
The public Auditor Portal endpoint is token-authenticated (no login) and strictly
read-only, exposing only sanitized report metadata + artifact hashes for verification.
"""
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsExport
from apps.common.views import TenantScopedViewSet
from apps.integrations import services
from apps.integrations.models import ApiKey, AuditorPortalLink, WebhookEndpoint
from apps.integrations.serializers import (
    ApiKeySerializer,
    AuditorPortalLinkSerializer,
    WebhookEndpointSerializer,
)
from apps.tenancy.models import ComplianceYear


class AuditorLinkViewSet(TenantScopedViewSet):
    permission_classes = [IsExport]
    serializer_class = AuditorPortalLinkSerializer
    queryset = AuditorPortalLink.objects.all()

    def create(self, request, *args, **kwargs):
        year = get_object_or_404(
            ComplianceYear, pk=request.data.get("compliance_year"), tenant_id=request.user.tenant_id
        )
        link = services.create_auditor_link(
            tenant=request.user.tenant, compliance_year=year, created_by=request.user,
            ttl_hours=int(request.data.get("ttl_hours", 72)),
        )
        return Response(self.get_serializer(link).data, status=status.HTTP_201_CREATED)


class AuditorPortalView(APIView):
    """Public, token-gated, read-only auditor view: report meta + artifact hashes."""

    permission_classes = [AllowAny]

    def get(self, request, token):
        link = get_object_or_404(AuditorPortalLink, token=token)
        if not services.link_is_valid(link):
            return Response({"detail": "Link expired."}, status=status.HTTP_410_GONE)
        return Response(
            {
                "tenant": link.tenant.name,
                "compliance_year": link.compliance_year.year,
                "state": link.compliance_year.state,
                "artifact_hashes": services.artifact_hashes(link.compliance_year),
            }
        )

    def post(self, request, token):
        """Verify a hash the auditor computed against the stored artifact hashes."""
        link = get_object_or_404(AuditorPortalLink, token=token)
        if not services.link_is_valid(link):
            return Response({"detail": "Link expired."}, status=status.HTTP_410_GONE)
        provided = request.data.get("sha256", "")
        return Response({"verified": services.verify_artifact_hash(link.compliance_year, provided)})


class WebhookEndpointViewSet(TenantScopedViewSet):
    permission_classes = [IsExport]
    serializer_class = WebhookEndpointSerializer
    queryset = WebhookEndpoint.objects.all()


class ApiKeyViewSet(TenantScopedViewSet):
    permission_classes = [IsExport]
    serializer_class = ApiKeySerializer
    queryset = ApiKey.objects.all()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        key, raw = services.issue_api_key(
            tenant=request.user.tenant,
            label=serializer.validated_data.get("label", ""),
            scopes=serializer.validated_data.get("scopes", []),
        )
        data = self.get_serializer(key).data
        data["api_key"] = raw  # shown once
        return Response(data, status=status.HTTP_201_CREATED)
