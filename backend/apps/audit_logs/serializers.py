"""Serializers for Audit Logs app."""

from rest_framework import serializers
from .models import ConversationLog


class ConversationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConversationLog
        fields = [
            "id",
            "employee",
            "query_text",
            "detected_intent",
            "response_text",
            "audio_file",
            "timestamp",
        ]
        read_only_fields = fields
