"""Account API — the current-user endpoint the frontend uses to resolve role/tenant."""
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        u = request.user
        return Response(
            {
                "id": str(u.id),
                "email": u.email or u.username,
                "role": u.role,
                "tenant": str(u.tenant_id) if u.tenant_id else None,
                "is_master_admin": u.is_master_admin,
            }
        )
