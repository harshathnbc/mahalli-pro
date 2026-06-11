from rest_framework.routers import DefaultRouter

from apps.finance import views

router = DefaultRouter()
router.register("soft-close", views.SoftCloseViewSet, basename="softclose")
router.register("hard-close", views.HardCloseViewSet, basename="hardclose")
router.register("trial-balance", views.TrialBalanceViewSet, basename="trialbalance")
router.register("tb-mappings", views.TbAccountMappingViewSet, basename="tbmapping")
router.register("evidence", views.EvidenceVaultViewSet, basename="evidence")
router.register("reconciliations", views.ReconciliationViewSet, basename="reconciliation")
router.register("year-close", views.YearCloseViewSet, basename="year-close")

urlpatterns = router.urls
