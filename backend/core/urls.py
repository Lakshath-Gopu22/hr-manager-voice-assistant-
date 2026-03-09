"""
VoiceHR – Root URL Configuration

All API endpoints are mounted under /api/.
Media files are served during development.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    
    path("", TemplateView.as_view(template_name="index.html"), name="home"),


    path("admin/", admin.site.urls),

    
    path("api/auth/", include("apps.authentication.urls")),
    path("api/employee/", include("apps.employees.urls")),
    path("api/hr/", include("apps.hr_queries.urls")),
    path("api/voice/", include("apps.voice_ai.urls")),
    path("api/audit/", include("apps.audit_logs.urls")),

    
    path("api/notifications/", include("apps.hr_queries.notification_urls")),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
