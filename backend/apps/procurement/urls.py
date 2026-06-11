from rest_framework.routers import DefaultRouter

from apps.procurement import views

router = DefaultRouter()
router.register("vendors", views.VendorViewSet, basename="vendor")
router.register("column-mappings", views.ColumnMappingViewSet, basename="columnmapping")
router.register("uploads", views.ProcUploadViewSet, basename="procupload")
router.register("invoices", views.InvoiceViewSet, basename="invoice")
router.register("certificates", views.VendorCertificateViewSet, basename="certificate")
router.register("warnings", views.ComplianceWarningViewSet, basename="warning")
router.register("year-analysis", views.YearAnalysisViewSet, basename="year-analysis")

urlpatterns = router.urls
