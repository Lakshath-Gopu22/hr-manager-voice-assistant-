from django.contrib import admin
from .models import ConversationLog


@admin.register(ConversationLog)
class ConversationLogAdmin(admin.ModelAdmin):
    list_display = ("employee", "detected_intent", "timestamp")
    list_filter = ("detected_intent",)
    search_fields = ("query_text", "response_text")
