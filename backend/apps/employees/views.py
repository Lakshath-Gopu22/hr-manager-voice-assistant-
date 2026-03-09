"""
Views for the Employees app.

Provides authenticated employees access to their own
profile, leave balance, and leave request history.
"""

from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.authentication.serializers import EmployeeSerializer
from apps.hr_queries.models import LeaveRequest, LeaveBalance
from apps.hr_queries.serializers import LeaveRequestSerializer, LeaveBalanceSerializer


@api_view(["GET"])
def profile_view(request):
    """
    GET /api/employee/profile/

    Returns the authenticated employee's profile.
    """
    serializer = EmployeeSerializer(request.user)
    return Response(serializer.data)


@api_view(["GET"])
def leave_view(request):
    """
    GET /api/employee/leave/

    Returns leave balance (overall + per-type) and all
    leave requests for the authenticated employee.
    """
    employee = request.user
    leave_requests = LeaveRequest.objects.filter(employee=employee)
    leave_balances = LeaveBalance.objects.filter(employee=employee)

    return Response({
        "employee_id": employee.employee_id,
        "leave_balance": employee.leave_balance,
        "leave_balances": LeaveBalanceSerializer(leave_balances, many=True).data,
        "total_requests": leave_requests.count(),
        "leave_requests": LeaveRequestSerializer(leave_requests, many=True).data,
    })
