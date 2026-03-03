"""Serializers for HR Queries app."""

from rest_framework import serializers
from .models import LeaveRequest, Payroll, LeaveBalance, Notification
from apps.authentication.models import Employee


class LeaveRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.name", read_only=True)
    employee_id = serializers.CharField(source="employee.employee_id", read_only=True)
    days = serializers.IntegerField(read_only=True)

    class Meta:
        model = LeaveRequest
        fields = [
            "id", "employee", "employee_name", "employee_id",
            "leave_type", "start_date", "end_date", "reason",
            "status", "days", "created_at",
        ]
        read_only_fields = ["id", "employee", "status", "created_at"]


class LeaveBalanceSerializer(serializers.ModelSerializer):
    remaining = serializers.IntegerField(read_only=True)

    class Meta:
        model = LeaveBalance
        fields = ["id", "leave_type", "total", "used", "remaining"]


class PayrollSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payroll
        fields = ["employee", "salary", "bonus", "last_paid_date"]
        read_only_fields = ["employee"]


class HREmployeeSerializer(serializers.ModelSerializer):
    salary = serializers.DecimalField(source='payroll.salary', max_digits=12, decimal_places=2, read_only=True)
    bonus = serializers.DecimalField(source='payroll.bonus', max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Employee
        fields = [
            "employee_id", "name", "department", "email",
            "leave_balance", "attendance_percentage", "is_hr",
            "salary", "bonus",
        ]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "message", "notif_type", "is_read", "created_at"]
        read_only_fields = ["id", "message", "notif_type", "created_at"]
