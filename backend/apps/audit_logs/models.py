"""
ConversationLog Model – Audit trail for every voice interaction.

Stores the original query text, detected intent, generated response,
and a link to the audio file for compliance and analytics.
"""

from django.db import models
from apps.authentication.models import Employee


class ConversationLog(models.Model):
    """Immutable log of each voice-assistant conversation turn."""

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="conversation_logs",
    )
    query_text = models.TextField(help_text="Transcribed text from employee's voice")
    detected_intent = models.CharField(max_length=50)
    response_text = models.TextField(help_text="Generated HR response")
    audio_file = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Relative path to the TTS audio file",
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "Conversation Log"
        verbose_name_plural = "Conversation Logs"

    def __str__(self):
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {self.employee.employee_id} → {self.detected_intent}"
