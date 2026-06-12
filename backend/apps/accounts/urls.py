from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.accounts import master_views

router = DefaultRouter()
router.register("tenants", master_views.TenantControlViewSet, basename="master-tenant")
router.register("audit-log", master_views.MasterAuditLogViewSet, basename="master-audit")

urlpatterns = [
    path("provision/", master_views.ProvisionTenantView.as_view(), name="master-provision"),
    *router.urls,
]
