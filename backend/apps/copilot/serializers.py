"""DRF serializers for the Compliance Copilot (Module 9)."""
from rest_framework import serializers

from apps.copilot.models import CopilotConversation, CopilotMessage


class CopilotMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CopilotMessage
        fields = ["id", "role", "content", "retrieved_chunk_ids", "created_at"]
        read_only_fields = fields


class CopilotConversationSerializer(serializers.ModelSerializer):
    messages = CopilotMessageSerializer(many=True, read_only=True)

    class Meta:
        model = CopilotConversation
        fields = ["id", "messages", "created_at"]
        read_only_fields = ["created_at"]


class AskSerializer(serializers.Serializer):
    query = serializers.CharField()
    conversation = serializers.UUIDField(required=False)
