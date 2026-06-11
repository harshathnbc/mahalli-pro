from rest_framework.routers import DefaultRouter

from apps.capex import views

router = DefaultRouter()
router.register("items", views.CapexItemViewSet, basename="capexitem")
router.register("years", views.CapexSummaryViewSet, basename="capexsummary")

urlpatterns = router.urls
