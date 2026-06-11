"""
Audit middleware — records every mutating (POST/PUT/PATCH/DELETE) API request to
the Master Audit Log. Read-level auditing of sensitive endpoints is layered in at
the view level where needed.
"""
from django.utils.deprecation import MiddlewareMixin

_MUTATING = {"POST", "PUT", "PATCH", "DELETE"}
_METHOD_TO_ACTION = {
    "POST": "CREATE",
    "PUT": "UPDATE",
    "PATCH": "UPDATE",
    "DELETE": "DELETE",
}


class AuditLogMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        try:
            if request.method in _MUTATING and request.path.startswith("/api/"):
                user = getattr(request, "user", None)
                if user and user.is_authenticated and 200 <= response.status_code < 400:
                    # Imported lazily to avoid app-registry import-time issues.
                    from apps.audit.models import AuditLog

                    AuditLog.objects.create(
                        tenant_id=getattr(user, "tenant_id", None),
                        actor=user,
                        action=_METHOD_TO_ACTION.get(request.method, "UPDATE"),
                        method=request.method,
                        path=request.path[:512],
                        ip=request.META.get("REMOTE_ADDR"),
                    )
        except Exception:  # never let auditing break the request
            pass
        return response
