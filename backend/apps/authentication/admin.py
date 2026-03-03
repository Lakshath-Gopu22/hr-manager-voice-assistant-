from django.contrib import admin
from .models import Employee


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("employee_id", "name", "department", "email", "leave_balance")
    search_fields = ("employee_id", "name", "email")
    list_filter = ("department",)
