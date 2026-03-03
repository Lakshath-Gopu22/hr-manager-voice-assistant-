"""
HR Views – Endpoints for HR users only + shared notification endpoints.

Allows HR authenticated users to view/edit employees,
view/approve/reject leave requests with quota enforcement,
add new employees, and manage notifications.
"""

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from datetime import date

from apps.authentication.models import Employee
from apps.authentication.serializers import EmployeeSerializer
from apps.hr_queries.models import LeaveRequest, LeaveBalance, Payroll, Notification
from apps.hr_queries.serializers import (
    LeaveRequestSerializer, HREmployeeSerializer,
    LeaveBalanceSerializer, NotificationSerializer,
)


# ──────────────────────────────────────────────
# Permissions
# ──────────────────────────────────────────────
class IsHRUser(IsAuthenticated):
    """Custom permission to only allow HR users."""

    def has_permission(self, request, view):
        is_authenticated = super().has_permission(request, view)
        return is_authenticated and getattr(request.user, "is_hr", False)


# ──────────────────────────────────────────────
# HR Employee Management
# ──────────────────────────────────────────────
class HREmployeeListView(generics.ListAPIView):
    """
    GET /api/hr/employees/
    Returns a list of all employees.
    """
    queryset = Employee.objects.all().select_related("payroll").order_by("employee_id")
    serializer_class = HREmployeeSerializer
    permission_classes = [IsHRUser]
    pagination_class = None


class HREmployeeDetailView(generics.RetrieveUpdateAPIView):
    """
    GET, PUT, PATCH /api/hr/employees/<employee_id>/
    Allows HR to view or update specific employee details.
    """
    queryset = Employee.objects.all()
    serializer_class = HREmployeeSerializer
    permission_classes = [IsHRUser]
    lookup_field = "employee_id"

    def perform_update(self, serializer):
        instance = serializer.save()

        salary_data = self.request.data.get("salary")
        bonus_data = self.request.data.get("bonus")

        if salary_data is not None or bonus_data is not None:
            if hasattr(instance, "payroll"):
                if salary_data is not None:
                    instance.payroll.salary = salary_data
                if bonus_data is not None:
                    instance.payroll.bonus = bonus_data
                instance.payroll.save()


class HREmployeeCreateView(APIView):
    """
    POST /api/hr/employees/create/
    Creates a new employee with Payroll and LeaveBalance records.
    """
    permission_classes = [IsHRUser]

    def post(self, request):
        data = request.data
        required = ["employee_id", "name", "email", "password"]
        for field in required:
            if not data.get(field):
                return Response(
                    {"error": f"'{field}' is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if Employee.objects.filter(employee_id=data["employee_id"]).exists():
            return Response(
                {"error": "Employee ID already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        emp = Employee.objects.create_user(
            employee_id=data["employee_id"],
            name=data["name"],
            email=data["email"],
            password=data["password"],
            department=data.get("department", "General"),
        )

        # Create payroll
        Payroll.objects.create(
            employee=emp,
            salary=data.get("salary", 0),
            bonus=data.get("bonus", 0),
            last_paid_date=date.today(),
        )

        # Create default leave balances
        for lt, total in [("casual", 12), ("medical", 10), ("earned", 15)]:
            LeaveBalance.objects.create(employee=emp, leave_type=lt, total=total, used=0)

        # Notify the new employee
        Notification.objects.create(
            recipient=emp,
            message=f"Welcome to the company, {emp.name}! Your account has been created by HR.",
            notif_type="employee_added",
        )

        return Response(
            {"message": f"Employee {emp.employee_id} created successfully."},
            status=status.HTTP_201_CREATED,
        )


# ──────────────────────────────────────────────
# HR Leave Management
# ──────────────────────────────────────────────
class HRLeaveListView(generics.ListAPIView):
    """
    GET /api/hr/leaves/
    Returns a list of all leave requests across the company.
    """
    queryset = LeaveRequest.objects.all().select_related("employee").order_by("-created_at")
    serializer_class = LeaveRequestSerializer
    permission_classes = [IsHRUser]
    pagination_class = None


class HRLeaveBalanceAggregateView(APIView):
    """
    GET /api/hr/leave-balances/
    Returns company-wide aggregate leave balances by type.
    """
    permission_classes = [IsHRUser]

    def get(self, request):
        from django.db.models import Sum
        result = {}
        for lt in ['casual', 'medical', 'earned']:
            agg = LeaveBalance.objects.filter(leave_type=lt).aggregate(
                total=Sum('total'), used=Sum('used')
            )
            total = agg['total'] or 0
            used = agg['used'] or 0
            result[lt] = {'total': total, 'used': used, 'remaining': total - used}
        return Response(result)


class HRLeaveStatusUpdateView(generics.UpdateAPIView):
    """
    PATCH /api/hr/leaves/<id>/status/
    Approves or rejects a leave request with quota enforcement.
    """
    queryset = LeaveRequest.objects.all()
    serializer_class = LeaveRequestSerializer
    permission_classes = [IsHRUser]
    lookup_field = "pk"

    def update(self, request, *args, **kwargs):
        leave_request = self.get_object()
        new_status = request.data.get("status")

        if new_status not in ["approved", "rejected", "pending"]:
            return Response(
                {"error": "Invalid status. Use 'approved', 'rejected', or 'pending'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if new_status == "approved":
            # Check quota
            balance = LeaveBalance.objects.filter(
                employee=leave_request.employee,
                leave_type=leave_request.leave_type,
            ).first()

            if balance:
                days_requested = leave_request.days
                if balance.used + days_requested > balance.total:
                    # Auto-reject due to insufficient balance
                    leave_request.status = "rejected"
                    leave_request.save()

                    Notification.objects.create(
                        recipient=leave_request.employee,
                        message=f"Your {leave_request.get_leave_type_display()} request ({leave_request.start_date} to {leave_request.end_date}) was rejected – quota exhausted ({balance.used}/{balance.total} days used).",
                        notif_type="leave_rejected",
                    )

                    return Response({
                        "error": f"Insufficient {leave_request.leave_type} balance. {balance.remaining} days remaining, {days_requested} requested.",
                        "auto_rejected": True,
                        "leave": LeaveRequestSerializer(leave_request).data,
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Deduct from balance
                balance.used += days_requested
                balance.save()

            leave_request.status = "approved"
            leave_request.save()

            Notification.objects.create(
                recipient=leave_request.employee,
                message=f"Your {leave_request.get_leave_type_display()} request ({leave_request.start_date} to {leave_request.end_date}) has been approved.",
                notif_type="leave_approved",
            )

        elif new_status == "rejected":
            leave_request.status = "rejected"
            leave_request.save()

            Notification.objects.create(
                recipient=leave_request.employee,
                message=f"Your {leave_request.get_leave_type_display()} request ({leave_request.start_date} to {leave_request.end_date}) has been rejected.",
                notif_type="leave_rejected",
            )

        else:
            leave_request.status = new_status
            leave_request.save()

        return Response(LeaveRequestSerializer(leave_request).data)


# ──────────────────────────────────────────────
# Employee Leave Balances
# ──────────────────────────────────────────────
class EmployeeLeaveBalanceView(generics.ListAPIView):
    """
    GET /api/employee/leave-balances/
    Returns per-category leave balances for the current employee.
    """
    serializer_class = LeaveBalanceSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return LeaveBalance.objects.filter(employee=self.request.user)


# ──────────────────────────────────────────────
# Notifications (shared – both HR and employees)
# ──────────────────────────────────────────────
class NotificationListView(generics.ListAPIView):
    """
    GET /api/notifications/
    Returns unread notifications for the authenticated user.
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user, is_read=False)


class NotificationMarkReadView(APIView):
    """
    PATCH /api/notifications/<id>/read/
    Marks a single notification as read.
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            notif = Notification.objects.get(pk=pk, recipient=request.user)
        except Notification.DoesNotExist:
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        notif.is_read = True
        notif.save()
        return Response({"message": "Marked as read."})


class NotificationMarkAllReadView(APIView):
    """
    PATCH /api/notifications/read-all/
    Marks all notifications as read for the authenticated user.
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return Response({"message": "All notifications marked as read."})
