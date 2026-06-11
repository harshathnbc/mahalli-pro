from rest_framework.routers import DefaultRouter

from apps.copilot import views

router = DefaultRouter()
router.register("", views.CopilotViewSet, basename="copilot")

urlpatterns = router.urls
