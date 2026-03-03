"""URL patterns for the Authentication app."""

from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.login_view, name="auth-login"),
]
