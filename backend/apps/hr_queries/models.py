"""
HR Queries Models – LeaveRequest, Payroll, LeaveBalance, Notification.

These models store employee leave records, payroll information,
per-category leave balances, and cross-portal notifications.
"""

from django.db import models
from apps.authentication.models import Employee


class LeaveRequest(models.Model):
    """Tracks leave applications submitted by employees."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    LEAVE_TYPE_CHOICES = [
        ("casual", "Casual Leave"),
        ("medical", "Medical Leave"),
        ("earned", "Earned Leave"),
    ]

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="leave_requests",
    )
    leave_type = models.CharField(
        max_length=10, choices=LEAVE_TYPE_CHOICES, default="casual"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True, default="")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Leave Request"
        verbose_name_plural = "Leave Requests"

    @property
    def days(self):
        return (self.end_date - self.start_date).days + 1

    def __str__(self):
        return f"{self.employee.employee_id} | {self.leave_type} | {self.start_date} → {self.end_date} ({self.status})"


class LeaveBalance(models.Model):
    """Per-category leave quota for each employee."""

    LEAVE_TYPE_CHOICES = LeaveRequest.LEAVE_TYPE_CHOICES

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="leave_balances"
    )
    leave_type = models.CharField(max_length=10, choices=LEAVE_TYPE_CHOICES)
    total = models.PositiveIntegerField(default=0)
    used = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("employee", "leave_type")
        verbose_name = "Leave Balance"

    @property
    def remaining(self):
        return max(self.total - self.used, 0)

    def __str__(self):
        return f"{self.employee.employee_id} | {self.leave_type}: {self.used}/{self.total}"


class Payroll(models.Model):
    """Stores salary and payment details for each employee."""

    employee = models.OneToOneField(
        Employee,
        on_delete=models.CASCADE,
        related_name="payroll",
    )
    salary = models.DecimalField(max_digits=12, decimal_places=2)
    bonus = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    last_paid_date = models.DateField()

    class Meta:
        verbose_name = "Payroll"
        verbose_name_plural = "Payroll Records"

    def __str__(self):
        return f"{self.employee.employee_id} | ₹{self.salary}"


class Notification(models.Model):
    """Cross-portal notification messages."""

    TYPE_CHOICES = [
        ("leave_approved", "Leave Approved"),
        ("leave_rejected", "Leave Rejected"),
        ("new_leave", "New Leave Request"),
        ("employee_added", "New Employee Added"),
    ]

    recipient = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="notifications"
    )
    message = models.TextField()
    notif_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="new_leave")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.notif_type}] → {self.recipient.employee_id}: {self.message[:40]}"
