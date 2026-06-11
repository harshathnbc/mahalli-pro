"""
Compliance Copilot API (Module 9). Any authenticated tenant user may ask; the
zero-trust RBAC routing inside services.retrieve restricts what context each role
can actually see, so HR cannot pull FINANCE documents into the prompt.
"""
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.copilot import services
from apps.copilot.models import CopilotConversation
from apps.copilot.serializers import (
    AskSerializer,
    CopilotConversationSerializer,
    CopilotMessageSerializer,
)


class CopilotViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def _conversations(self, request):
        return CopilotConversation.objects.filter(
            tenant_id=request.user.tenant_id, user=request.user
        )

    def list(self, request):
        return Response(
            CopilotConversationSerializer(
                self._conversations(request).prefetch_related("messages"), many=True
            ).data
        )

    @action(detail=False, methods=["post"])
    def ask(self, request):
        """Ask a question; answered strictly from RBAC-authorized retrieved context."""
        serializer = AskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        conv_id = serializer.validated_data.get("conversation")
        if conv_id:
            conversation = self._conversations(request).get(id=conv_id)
        else:
            conversation = CopilotConversation.objects.create(
                tenant_id=request.user.tenant_id, user=request.user
            )
        message = services.answer(
            conversation=conversation,
            query=serializer.validated_data["query"],
            role=request.user.role,
        )
        return Response(
            {
                "conversation": conversation.id,
                "message": CopilotMessageSerializer(message).data,
            },
            status=status.HTTP_201_CREATED,
        )
