from rest_framework.routers import DefaultRouter

from apps.assets import views

router = DefaultRouter()
router.register("registers", views.AssetRegisterViewSet, basename="assetregister")
router.register("assets", views.AssetViewSet, basename="asset")

urlpatterns = router.urls
