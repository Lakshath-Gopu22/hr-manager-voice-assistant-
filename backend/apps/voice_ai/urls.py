"""URL patterns for the Voice AI app."""

from django.urls import path
from . import views

urlpatterns = [
    path("query/", views.voice_query_view, name="voice-query"),
    path("text-query/", views.text_query_view, name="text-query"),
]
