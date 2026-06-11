from rest_framework.routers import DefaultRouter

from apps.hr import views

router = DefaultRouter()
router.register("uploads", views.HrUploadViewSet, basename="hrupload")
router.register("gosi", views.GosiCertificateViewSet, basename="gosi")
router.register("payroll", views.PayrollRowViewSet, basename="payrollrow")

urlpatterns = router.urls
