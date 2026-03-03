"""URL patterns for notifications (shared by HR and employees)."""

from django.urls import path
from apps.hr_queries import views

urlpatterns = [
    path("", views.NotificationListView.as_view(), name="notification-list"),
    path("<int:pk>/read/", views.NotificationMarkReadView.as_view(), name="notification-read"),
    path("read-all/", views.NotificationMarkAllReadView.as_view(), name="notification-read-all"),
]
