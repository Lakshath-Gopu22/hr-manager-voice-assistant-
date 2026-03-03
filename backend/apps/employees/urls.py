"""URL patterns for the Employees app."""

from django.urls import path
from . import views
from apps.hr_queries.views import EmployeeLeaveBalanceView

urlpatterns = [
    path("profile/", views.profile_view, name="employee-profile"),
    path("leave/", views.leave_view, name="employee-leave"),
    path("leave-balances/", EmployeeLeaveBalanceView.as_view(), name="employee-leave-balances"),
]
