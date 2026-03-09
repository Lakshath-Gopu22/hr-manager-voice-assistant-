"""
HR Service -- Data Retrieval Layer.

Dispatches database queries based on the detected intent
and returns a response dict with text, optional action flags,
and data for multi-step conversations (e.g. leave application).

All responses use clean, professional HR-style text without emojis.
All dates are generated dynamically using Python's datetime.
"""

import logging
import re
from datetime import date, datetime, timedelta
from decimal import Decimal

from apps.hr_queries.models import LeaveRequest, LeaveBalance, Payroll, Notification

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

# Leave type display labels (no emojis)
LEAVE_TYPE_LABELS = {
    "casual": "Casual Leave",
    "medical": "Medical Leave",
    "earned": "Earned Leave",
}

# Standard Indian payroll percentages
PAYROLL_PERCENTAGES = {
    "basic": Decimal("0.50"),        # 50% of gross
    "hra": Decimal("0.20"),          # 20% of gross
    "da": Decimal("0.10"),           # 10% of gross (Dearness Allowance)
    "special": Decimal("0.20"),      # 20% of gross (Special Allowance)
    "pf_rate": Decimal("0.12"),      # 12% of basic
    "pt_monthly": Decimal("200"),    # Professional Tax (fixed)
    "income_tax_rate": Decimal("0.10"),  # ~10% estimated income tax on gross
}


def _response(text, action=None, data=None):
    """Build a standard response dict."""
    return {"text": text, "action": action, "data": data}


def handle_intent(intent: str, employee, query_text: str = "") -> dict:
    """
    Process the detected intent and return an HR response dict.

    Returns:
        dict with keys: text (str), action (str|None), data (dict|None)
    """
    handler = INTENT_HANDLERS.get(intent, _handle_unknown)

    if intent in ("leave_balance", "apply_leave", "payroll_query"):
        return handler(employee, query_text)
    return handler(employee)


# --------------------------------------------------
# Individual intent handlers
# --------------------------------------------------

def _handle_greeting(employee):
    current_time = datetime.now()
    if current_time.hour < 12:
        greeting = "Good morning"
    elif current_time.hour < 17:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"

    return _response(
        f"{greeting}, {employee.name}! I am your HR Voice Assistant. "
        f"You can ask me about your leave balance, attendance, "
        f"salary details, company policies, or apply for leave. "
        f"How can I help you today?"
    )


def _handle_leave_balance(employee, query_text: str = ""):
    """Show per-type leave balance breakdown."""
    from services.intent_service import extract_leave_type

    balances = LeaveBalance.objects.filter(employee=employee)

    if not balances.exists():
        return _response(
            f"Hi {employee.name}, your overall leave balance is "
            f"{employee.leave_balance} days. Per-category details "
            f"are not yet configured. Please contact HR."
        )

    requested_type = extract_leave_type(query_text) if query_text else None

    if requested_type:
        bal = balances.filter(leave_type=requested_type).first()
        if bal:
            label = LEAVE_TYPE_LABELS.get(requested_type, requested_type.title())
            status_msg = (
                f"You have {bal.remaining} days remaining"
                if bal.remaining > 0
                else "You have no leaves remaining in this category"
            )
            return _response(
                f"Hi {employee.name}, your {label} status:\n"
                f"- Total: {bal.total} days\n"
                f"- Used: {bal.used} days\n"
                f"- Remaining: {bal.remaining} days\n\n"
                f"{status_msg}."
            )
        return _response(
            f"Sorry {employee.name}, no {requested_type} leave "
            f"balance found. Please contact HR."
        )

    # Show all types
    total_remaining = 0
    lines = [f"Hi {employee.name}, here is your leave balance as of {date.today().strftime('%B %d, %Y')}:\n"]

    for bal in balances:
        label = LEAVE_TYPE_LABELS.get(bal.leave_type, bal.leave_type.title())
        remaining = bal.remaining
        total_remaining += remaining
        if remaining > 0:
            lines.append(f"- {label}: {remaining}/{bal.total} remaining")
        else:
            lines.append(f"- {label}: No leaves remaining (0/{bal.total})")

    lines.append(f"\nTotal available: {total_remaining} days")

    exhausted = [
        LEAVE_TYPE_LABELS.get(b.leave_type, b.leave_type)
        for b in balances if b.remaining == 0
    ]
    if exhausted:
        lines.append(f"\nNote: Your {', '.join(exhausted)} quota is exhausted.")

    pending_count = LeaveRequest.objects.filter(
        employee=employee, status="pending"
    ).count()
    if pending_count > 0:
        lines.append(f"\nYou have {pending_count} pending leave request(s).")

    return _response("\n".join(lines))


def _handle_apply_leave(employee, query_text: str = ""):
    """
    Smart leave application -- only asks for what's missing.

    Cases:
      - No type, no dates   -> ask for both (show balances)
      - Dates but no type   -> ask for type only
      - Type but no dates   -> ask for dates only
      - Both type and dates -> submit immediately (status: Pending)

    Reason always defaults to "Personal reasons" (no reason step).
    """
    from services.intent_service import extract_leave_type, extract_dates

    leave_type = extract_leave_type(query_text) if query_text else None
    start_date, end_date = extract_dates(query_text) if query_text else (None, None)

    has_type = leave_type is not None
    has_dates = start_date is not None and end_date is not None

    # ---- CASE 1: Neither type nor dates provided ----
    if not has_type and not has_dates:
        balances = LeaveBalance.objects.filter(employee=employee)
        bal_list = []
        lines = [
            f"Sure, {employee.name}. Which type of leave would you like to apply for?\n",
            "You can choose from the following:\n",
        ]

        for bal in balances:
            label = LEAVE_TYPE_LABELS.get(bal.leave_type, bal.leave_type.title())
            remaining = bal.remaining
            bal_list.append({
                "leave_type": bal.leave_type,
                "label": label,
                "total": bal.total,
                "used": bal.used,
                "remaining": remaining,
            })
            if remaining > 0:
                lines.append(f"- {label}: {remaining}/{bal.total} days remaining")
            else:
                lines.append(f"- {label}: No leaves remaining")

        lines.append(
            "\nPlease select your leave type - Casual Leave, Medical Leave, "
            "or Earned Leave."
        )

        return _response(
            "\n".join(lines),
            action="select_leave_type",
            data={"balances": bal_list},
        )

    # ---- CASE 2: Dates provided but no type ----
    if has_dates and not has_type:
        balances = LeaveBalance.objects.filter(employee=employee)
        bal_list = []
        days_requested = (end_date - start_date).days + 1
        lines = [
            f"Got it, {employee.name}. You want {days_requested} day{'s' if days_requested > 1 else ''} of leave from "
            f"{start_date.strftime('%B %d, %Y')} to {end_date.strftime('%B %d, %Y')}.\n",
            "Which type of leave would you like to apply for?\n",
        ]

        for bal in balances:
            label = LEAVE_TYPE_LABELS.get(bal.leave_type, bal.leave_type.title())
            remaining = bal.remaining
            bal_list.append({
                "leave_type": bal.leave_type,
                "label": label,
                "total": bal.total,
                "used": bal.used,
                "remaining": remaining,
            })
            if remaining > 0:
                lines.append(f"- {label}: {remaining}/{bal.total} days remaining")
            else:
                lines.append(f"- {label}: No leaves remaining")

        lines.append(
            "\nPlease select your leave type - Casual Leave, Medical Leave, "
            "or Earned Leave."
        )

        return _response(
            "\n".join(lines),
            action="select_leave_type",
            data={
                "balances": bal_list,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        )

    # ---- At this point we have the type -- check balance ----
    label = LEAVE_TYPE_LABELS.get(leave_type, leave_type.title())
    balance = LeaveBalance.objects.filter(
        employee=employee, leave_type=leave_type
    ).first()

    if balance and balance.remaining <= 0:
        # Exhausted -- suggest alternatives
        other_balances = LeaveBalance.objects.filter(
            employee=employee
        ).exclude(leave_type=leave_type)

        alternatives = []
        alt_list = []
        for ob in other_balances:
            if ob.remaining > 0:
                alt_label = LEAVE_TYPE_LABELS.get(ob.leave_type, ob.leave_type)
                alternatives.append(f"- {alt_label}: {ob.remaining} days")
                alt_list.append({
                    "leave_type": ob.leave_type,
                    "label": alt_label,
                    "total": ob.total,
                    "used": ob.used,
                    "remaining": ob.remaining,
                })

        response_text = (
            f"Sorry {employee.name}, you have no {label} remaining "
            f"(0/{balance.total} days used)."
        )
        if alternatives:
            response_text += (
                f"\n\nYou can still apply for:\n"
                + "\n".join(alternatives)
                + "\n\nPlease select another leave type."
            )
            return _response(
                response_text,
                action="select_leave_type",
                data={"balances": alt_list},
            )

        response_text += "\n\nAll leave categories are exhausted. Please contact HR."
        return _response(response_text)

    # ---- CASE 3: Type provided but no dates ----
    if has_type and not has_dates:
        return _response(
            f"You selected {label}. You have {balance.remaining if balance else 0} "
            f"days remaining.\n\n"
            f"Please provide the start date and end date for your leave.",
            action="enter_dates",
            data={"leave_type": leave_type, "label": label},
        )

    # ---- CASE 4: Both type and dates provided -- submit directly ----
    # Validate dates
    today = date.today()
    if start_date < today:
        return _response(
            f"The start date ({start_date.strftime('%B %d, %Y')}) is in the past. "
            f"Please select a date from today ({today.strftime('%B %d, %Y')}) onwards.",
            action="enter_dates",
            data={"leave_type": leave_type, "label": label},
        )

    days_requested = (end_date - start_date).days + 1

    # Check if enough balance
    if balance and days_requested > balance.remaining:
        return _response(
            f"Insufficient {label} balance. You requested {days_requested} day(s) "
            f"but only have {balance.remaining} day(s) remaining.\n\n"
            f"Please select shorter dates or choose a different leave type.",
            action="enter_dates",
            data={"leave_type": leave_type, "label": label},
        )

    reason_text = "Personal reasons"

    # Create leave request
    leave = LeaveRequest.objects.create(
        employee=employee,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        reason=reason_text,
        status="pending",
    )

    # Balance is deducted only when HR approves the request
    remaining_after = balance.remaining if balance else employee.leave_balance

    # Notify HR users
    from apps.authentication.models import Employee as Emp
    hr_users = Emp.objects.filter(is_hr=True)
    for hr in hr_users:
        Notification.objects.create(
            recipient=hr,
            message=(
                f"New {label} request from {employee.name} "
                f"({employee.employee_id}) for "
                f"{start_date.strftime('%B %d, %Y')} to "
                f"{end_date.strftime('%B %d, %Y')} "
                f"({days_requested} day{'s' if days_requested > 1 else ''}). "
                f"Reason: {reason_text}"
            ),
            notif_type="new_leave",
        )

    return _response(
        f"Your leave request has been submitted successfully.\n\n"
        f"Leave Type: {label}\n"
        f"Start Date: {start_date.strftime('%B %d, %Y')}\n"
        f"End Date: {end_date.strftime('%B %d, %Y')}\n"
        f"Duration: {days_requested} day{'s' if days_requested > 1 else ''}\n"
        f"Reason: {reason_text}\n"
        f"Request ID: {leave.id}\n"
        f"Status: Pending\n"
        f"{label} Remaining: {remaining_after} day{'s' if remaining_after != 1 else ''}"
    )


def _handle_attendance(employee):
    today = date.today()
    return _response(
        f"Hi {employee.name}, your attendance percentage for the "
        f"current period (as of {today.strftime('%B %d, %Y')}) "
        f"is {employee.attendance_percentage}%."
    )


def _handle_payroll(employee, query_text: str = ""):
    """Enhanced payroll handler with sub-intent detection."""
    from services.intent_service import extract_payroll_subintent

    try:
        payroll = Payroll.objects.get(employee=employee)
    except Payroll.DoesNotExist:
        return _response(
            f"Sorry {employee.name}, no payroll record was found. "
            f"Please contact the Finance department."
        )

    subintent = extract_payroll_subintent(query_text) if query_text else "general"
    gross = payroll.salary
    bonus = payroll.bonus
    today = date.today()

    # Calculate components
    basic = gross * PAYROLL_PERCENTAGES["basic"]
    hra = gross * PAYROLL_PERCENTAGES["hra"]
    da = gross * PAYROLL_PERCENTAGES["da"]
    special_allowance = gross * PAYROLL_PERCENTAGES["special"]

    # Deductions
    pf = basic * PAYROLL_PERCENTAGES["pf_rate"]
    pt = PAYROLL_PERCENTAGES["pt_monthly"]
    income_tax = gross * PAYROLL_PERCENTAGES["income_tax_rate"]
    total_deductions = pf + pt + income_tax
    net_salary = gross - total_deductions

    # Next credit date calculation
    pay_day = payroll.last_paid_date.day
    if today.day <= pay_day:
        next_pay = today.replace(day=pay_day)
    else:
        if today.month == 12:
            next_pay = today.replace(year=today.year + 1, month=1, day=pay_day)
        else:
            next_pay = today.replace(month=today.month + 1, day=pay_day)

    if subintent == "general":
        return _response(
            f"Hi {employee.name}, here are your payroll details "
            f"as of {today.strftime('%B %d, %Y')}:\n\n"
            f"- Monthly Gross Salary: Rs. {gross:,.2f}\n"
            f"- Net Salary (Take Home): Rs. {net_salary:,.2f}\n"
            f"- Bonus: Rs. {bonus:,.2f}\n"
            f"- Last Paid: {payroll.last_paid_date.strftime('%B %d, %Y')}\n"
            f"- Next Salary Credit: {next_pay.strftime('%B %d, %Y')}\n\n"
            f"For a detailed breakdown, try asking 'Show my salary breakdown'."
        )

    elif subintent == "breakdown":
        return _response(
            f"Hi {employee.name}, here is your detailed salary breakdown "
            f"as of {today.strftime('%B %d, %Y')}:\n\n"
            f"--- Earnings ---\n"
            f"- Basic Salary: Rs. {basic:,.2f}\n"
            f"- House Rent Allowance (HRA): Rs. {hra:,.2f}\n"
            f"- Dearness Allowance (DA): Rs. {da:,.2f}\n"
            f"- Special Allowance: Rs. {special_allowance:,.2f}\n"
            f"- Gross Salary: Rs. {gross:,.2f}\n\n"
            f"--- Deductions ---\n"
            f"- Provident Fund (PF): Rs. {pf:,.2f}\n"
            f"- Professional Tax: Rs. {pt:,.2f}\n"
            f"- Income Tax (estimated): Rs. {income_tax:,.2f}\n"
            f"- Total Deductions: Rs. {total_deductions:,.2f}\n\n"
            f"--- Net Salary ---\n"
            f"- Take Home Pay: Rs. {net_salary:,.2f}"
        )

    elif subintent == "deductions":
        return _response(
            f"Hi {employee.name}, here are your monthly deductions "
            f"as of {today.strftime('%B %d, %Y')}:\n\n"
            f"- Provident Fund (12% of Basic): Rs. {pf:,.2f}\n"
            f"- Professional Tax: Rs. {pt:,.2f}\n"
            f"- Income Tax (estimated at 10%): Rs. {income_tax:,.2f}\n"
            f"- Total Monthly Deductions: Rs. {total_deductions:,.2f}\n\n"
            f"Your gross salary is Rs. {gross:,.2f} and after all deductions, "
            f"your net salary is Rs. {net_salary:,.2f}."
        )

    elif subintent == "net_salary":
        return _response(
            f"Hi {employee.name}, your net salary (take home pay) "
            f"as of {today.strftime('%B %d, %Y')}:\n\n"
            f"- Gross Salary: Rs. {gross:,.2f}\n"
            f"- Total Deductions: Rs. {total_deductions:,.2f}\n"
            f"- Net Salary: Rs. {net_salary:,.2f}\n\n"
            f"This is the amount credited to your account after "
            f"all statutory deductions."
        )

    elif subintent == "credit_date":
        return _response(
            f"Hi {employee.name}, your salary credit details:\n\n"
            f"- Last Salary Credited: {payroll.last_paid_date.strftime('%B %d, %Y')}\n"
            f"- Next Expected Credit: {next_pay.strftime('%B %d, %Y')}\n"
            f"- Amount: Rs. {net_salary:,.2f} (net)\n\n"
            f"Salaries are typically credited on the {pay_day}th of every month."
        )

    elif subintent == "last_month":
        last_month_date = payroll.last_paid_date
        return _response(
            f"Hi {employee.name}, your last salary payment details:\n\n"
            f"- Payment Date: {last_month_date.strftime('%B %d, %Y')}\n"
            f"- Gross Amount: Rs. {gross:,.2f}\n"
            f"- Deductions: Rs. {total_deductions:,.2f}\n"
            f"- Net Amount Credited: Rs. {net_salary:,.2f}\n"
            f"- Bonus (if applicable): Rs. {bonus:,.2f}"
        )

    elif subintent == "allowances":
        total_allowances = hra + da + special_allowance
        return _response(
            f"Hi {employee.name}, here are the allowances included "
            f"in your monthly salary:\n\n"
            f"- House Rent Allowance (HRA): Rs. {hra:,.2f}\n"
            f"- Dearness Allowance (DA): Rs. {da:,.2f}\n"
            f"- Special Allowance: Rs. {special_allowance:,.2f}\n"
            f"- Total Allowances: Rs. {total_allowances:,.2f}\n\n"
            f"These are in addition to your Basic Salary of Rs. {basic:,.2f}."
        )

    elif subintent == "annual":
        annual_gross = gross * 12
        annual_bonus = bonus
        ctc = annual_gross + annual_bonus
        annual_deductions = total_deductions * 12
        annual_net = net_salary * 12
        return _response(
            f"Hi {employee.name}, your annual salary package:\n\n"
            f"- Annual Gross Salary: Rs. {annual_gross:,.2f}\n"
            f"- Annual Bonus: Rs. {annual_bonus:,.2f}\n"
            f"- Cost to Company (CTC): Rs. {ctc:,.2f}\n"
            f"- Annual Deductions: Rs. {annual_deductions:,.2f}\n"
            f"- Annual Net Take Home: Rs. {annual_net:,.2f}"
        )

    # Fallback
    return _response(
        f"Hi {employee.name}, your current monthly salary is "
        f"Rs. {gross:,.2f}. For more details, try asking about "
        f"salary breakdown, deductions, allowances, or annual package."
    )


def _handle_policy(employee):
    return _response(COMPANY_POLICIES["general"])


def _handle_unknown(employee):
    return _response(
        f"I am sorry {employee.name}, I did not understand your request. "
        f"You can ask me about:\n"
        f"- Leave balance (casual, medical, earned)\n"
        f"- Applying for leave\n"
        f"- Attendance status\n"
        f"- Salary, payroll breakdown, deductions, or allowances\n"
        f"- Company policies\n"
        f"Please try again."
    )


# --------------------------------------------------
# Intent -> Handler dispatch map
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
