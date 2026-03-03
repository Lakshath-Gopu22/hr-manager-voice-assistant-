"""URL patterns for the Audit Logs app."""

from django.urls import path
from . import views

urlpatterns = [
    path("history/", views.history_view, name="audit-history"),
]
