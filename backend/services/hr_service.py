"""
HR Service – Data Retrieval Layer.

Dispatches database queries based on the detected intent
and returns a human-readable text response. This is the
"brain" that bridges NLP intents to actual HR data.
"""

import logging
from datetime import date, timedelta

from apps.hr_queries.models import LeaveRequest, Payroll, Notification

logger = logging.getLogger(__name__)


# ==================================================
# COMPANY POLICIES (static; could move to DB later)
# ==================================================
COMPANY_POLICIES = {
    "work_from_home": (
        "Our WFH policy allows up to 2 days per week of remote work. "
        "Please apply through the HR portal at least 24 hours in advance."
    ),
    "working_hours": (
        "Standard working hours are 9:00 AM to 6:00 PM, Monday to Friday. "
        "Core hours (mandatory presence) are 10:00 AM to 4:00 PM."
    ),
    "dress_code": (
        "Business casual is the standard dress code. "
        "Formal attire is required for client-facing meetings."
    ),
    "general": (
        "For detailed company policies, please visit the HR portal "
        "or contact the HR department directly at hr@company.com."
    ),
}


def handle_intent(intent: str, employee) -> str:
    """
    Process the detected intent and return an HR response.

    Args:
        intent:   One of the known intents (e.g. 'leave_balance').
        employee: The authenticated Employee model instance.

    Returns:
        A human-friendly text response.
    """
    handler = INTENT_HANDLERS.get(intent, _handle_unknown)
    return handler(employee)


# --------------------------------------------------
# Individual intent handlers
# --------------------------------------------------

def _handle_greeting(employee) -> str:
    return (
        f"Hello {employee.name}! I'm your HR Voice Assistant. "
        f"You can ask me about your leave balance, attendance, "
        f"salary, company policies, or apply for leave. "
        f"How can I help you today?"
    )


def _handle_leave_balance(employee) -> str:
    pending_count = LeaveRequest.objects.filter(
        employee=employee, status="pending"
    ).count()

    response = (
        f"Hi {employee.name}, your current leave balance is "
        f"{employee.leave_balance} days."
    )
    if pending_count > 0:
        response += f" You have {pending_count} pending leave request(s)."
    return response


def _handle_apply_leave(employee) -> str:
    """Auto-create a 1-day leave request for tomorrow (demo)."""
    tomorrow = date.today() + timedelta(days=1)

    if employee.leave_balance <= 0:
        return (
            f"Sorry {employee.name}, you have no remaining leave balance. "
            f"Please contact HR for assistance."
        )

    leave = LeaveRequest.objects.create(
        employee=employee,
        start_date=tomorrow,
        end_date=tomorrow,
        reason="Applied via Voice Assistant",
        status="pending",
    )

    # Notify all HR users about the new leave request
    from apps.authentication.models import Employee as Emp
    hr_users = Emp.objects.filter(is_hr=True)
    for hr in hr_users:
        Notification.objects.create(
            recipient=hr,
            message=f"📋 New leave request from {employee.name} ({employee.employee_id}) for {tomorrow.strftime('%B %d, %Y')}.",
            notif_type="new_leave",
        )

    return (
        f"Leave request submitted for {tomorrow.strftime('%B %d, %Y')}. "
        f"Request ID: {leave.id}. Status: Pending. "
        f"Your remaining balance is {employee.leave_balance} days."
    )


def _handle_attendance(employee) -> str:
    return (
        f"Hi {employee.name}, your attendance percentage for the "
        f"current period is {employee.attendance_percentage}%."
    )


def _handle_payroll(employee) -> str:
    try:
        payroll = Payroll.objects.get(employee=employee)
        return (
            f"Hi {employee.name}, here are your payroll details:\n"
            f"• Monthly Salary: ₹{payroll.salary:,.2f}\n"
            f"• Bonus: ₹{payroll.bonus:,.2f}\n"
            f"• Last Paid: {payroll.last_paid_date.strftime('%B %d, %Y')}"
        )
    except Payroll.DoesNotExist:
        return (
            f"Sorry {employee.name}, no payroll record was found. "
            f"Please contact the Finance department."
        )


def _handle_policy(employee) -> str:
    # Return general policy info; future: parse sub-topic from query
    return COMPANY_POLICIES["general"]


def _handle_unknown(employee) -> str:
    return (
        f"I'm sorry {employee.name}, I didn't understand your request. "
        f"You can ask me about:\n"
        f"• Leave balance\n"
        f"• Applying for leave\n"
        f"• Attendance status\n"
        f"• Salary / payroll\n"
        f"• Company policies\n"
        f"Please try again!"
    )


# --------------------------------------------------
# Intent → Handler dispatch map
# --------------------------------------------------
INTENT_HANDLERS = {
    "greeting": _handle_greeting,
    "leave_balance": _handle_leave_balance,
    "apply_leave": _handle_apply_leave,
    "attendance_status": _handle_attendance,
    "payroll_query": _handle_payroll,
    "policy_question": _handle_policy,
    "unknown": _handle_unknown,
}
