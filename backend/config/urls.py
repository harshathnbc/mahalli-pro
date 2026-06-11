from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)


def healthz(_request):
    """Liveness probe used by the platform / load balancer."""
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("healthz", healthz),
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/hr/", include("apps.hr.urls")),
    path("api/procurement/", include("apps.procurement.urls")),
    path("api/finance/", include("apps.finance.urls")),
    path("api/capex/", include("apps.capex.urls")),
    path("api/assets/", include("apps.assets.urls")),
    path("api/reports/", include("apps.reports.urls")),
    path("api/copilot/", include("apps.copilot.urls")),
]
