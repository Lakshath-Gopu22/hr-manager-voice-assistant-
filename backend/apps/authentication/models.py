"""
Employee Model – Custom User model for VoiceHR.

Uses `employee_id` as the unique login identifier instead of the
default Django username field. Extends AbstractBaseUser for full
control over authentication.
"""

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class EmployeeManager(BaseUserManager):
    """Custom manager for the Employee model."""

    def create_user(self, employee_id, name, email, password=None, **extra_fields):
        """Create and return a regular employee."""
        if not employee_id:
            raise ValueError("Employee ID is required.")
        if not email:
            raise ValueError("Email is required.")

        email = self.normalize_email(email)
        user = self.model(
            employee_id=employee_id,
            name=name,
            email=email,
            **extra_fields,
        )
        user.set_password(password)  # hashes the password
        user.save(using=self._db)
        return user

    def create_superuser(self, employee_id, name, email, password=None, **extra_fields):
        """Create and return a superuser (for Django admin)."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(employee_id, name, email, password, **extra_fields)


class Employee(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model representing a company employee.

    Fields:
        employee_id  – unique ID used for login (e.g. 'EMP001')
        name         – full name of the employee
        department   – department name
        email        – official email address
        leave_balance        – remaining leave days
        attendance_percentage – % attendance in current period
    """

    employee_id = models.CharField(max_length=20, unique=True, primary_key=True)
    name = models.CharField(max_length=150)
    department = models.CharField(max_length=100, default="General")
    email = models.EmailField(unique=True)
    leave_balance = models.PositiveIntegerField(default=20)
    attendance_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=100.00
    )
    is_hr = models.BooleanField(default=False)

    # Django auth fields
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = EmployeeManager()

    # Tell Django to use employee_id for login
    USERNAME_FIELD = "employee_id"
    REQUIRED_FIELDS = ["name", "email"]

    class Meta:
        verbose_name = "Employee"
        verbose_name_plural = "Employees"
        ordering = ["employee_id"]

    def __str__(self):
        return f"{self.employee_id} – {self.name}"
