"""
Row-Level Security middleware.

On every authenticated request, set the Postgres session GUC `app.current_tenant_id`
to the requesting user's tenant. RLS policies on tenant-scoped tables then physically
restrict reads/writes to that tenant — even if application code forgets a filter.

Master Admin (no tenant) connects via a privileged RLS-bypass role; during a
ghost-login the impersonated tenant id is set here instead.
"""
from django.db import connection


class RowLevelSecurityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tenant_id = self._resolve_tenant_id(request)
        if tenant_id:
            with connection.cursor() as cursor:
                # set_config(..., is_local=true) scopes the GUC to this transaction.
                cursor.execute("SELECT set_config('app.current_tenant_id', %s, true)", [str(tenant_id)])
        return self.get_response(request)

    @staticmethod
    def _resolve_tenant_id(request):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return None
        # Ghost-login impersonation takes precedence (set on the session).
        impersonated = request.session.get("ghost_tenant_id") if hasattr(request, "session") else None
        if impersonated:
            return impersonated
        return getattr(user, "tenant_id", None)
