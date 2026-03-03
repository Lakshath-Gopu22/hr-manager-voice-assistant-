"""Serializers for the Authentication app."""

from rest_framework import serializers
from .models import Employee


class LoginSerializer(serializers.Serializer):
    """Validates login credentials."""
    employee_id = serializers.CharField(max_length=20)
    password = serializers.CharField(write_only=True)


class EmployeeSerializer(serializers.ModelSerializer):
    """Read-only representation of an Employee."""

    class Meta:
        model = Employee
        fields = [
            "employee_id",
            "name",
            "department",
            "email",
            "leave_balance",
            "attendance_percentage",
            "date_joined",
            "is_hr",
        ]
        read_only_fields = fields
