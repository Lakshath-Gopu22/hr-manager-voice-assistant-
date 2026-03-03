from django.contrib import admin
from .models import LeaveRequest, Payroll


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ("employee", "start_date", "end_date", "status", "created_at")
    list_filter = ("status",)


@admin.register(Payroll)
class PayrollAdmin(admin.ModelAdmin):
    list_display = ("employee", "salary", "bonus", "last_paid_date")
