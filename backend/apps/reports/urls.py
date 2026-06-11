from rest_framework.routers import DefaultRouter

from apps.reports import views

router = DefaultRouter()
router.register("lc-reports", views.LcReportViewSet, basename="lcreport")
router.register("simulator", views.SimulatorViewSet, basename="simulator")

urlpatterns = router.urls
