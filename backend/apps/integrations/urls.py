from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.integrations import views

router = DefaultRouter()
router.register("auditor-links", views.AuditorLinkViewSet, basename="auditorlink")
router.register("webhooks", views.WebhookEndpointViewSet, basename="webhook")
router.register("api-keys", views.ApiKeyViewSet, basename="apikey")

urlpatterns = [
    # Public, token-gated auditor portal (no auth).
    path("portal/<str:token>/", views.AuditorPortalView.as_view(), name="auditor-portal"),
    *router.urls,
]
