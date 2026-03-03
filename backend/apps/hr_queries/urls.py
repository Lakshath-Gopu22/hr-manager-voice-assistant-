"""URL patterns for the HR Queries app (HR portal endpoints)."""

from django.urls import path
from . import views

urlpatterns = [
    # Employee Management
    path("employees/", views.HREmployeeListView.as_view(), name="hr-employee-list"),
    path("employees/create/", views.HREmployeeCreateView.as_view(), name="hr-employee-create"),
    path("employees/<str:employee_id>/", views.HREmployeeDetailView.as_view(), name="hr-employee-detail"),

    # Leave Management
    path("leaves/", views.HRLeaveListView.as_view(), name="hr-leave-list"),
    path("leaves/<int:pk>/status/", views.HRLeaveStatusUpdateView.as_view(), name="hr-leave-status"),
    path("leave-balances/", views.HRLeaveBalanceAggregateView.as_view(), name="hr-leave-balances"),
]
