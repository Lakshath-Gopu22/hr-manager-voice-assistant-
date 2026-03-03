"""
Intent Service – Lightweight NLP Intent Classifier.

Uses keyword mapping and regex patterns to detect the
employee's intent from transcribed text. Easily extensible:
just add new entries to INTENT_PATTERNS.

Supported intents:
    - leave_balance
    - apply_leave
    - attendance_status
    - payroll_query
    - policy_question
    - greeting
    - unknown  (fallback)
"""

import re
import logging

logger = logging.getLogger(__name__)

# --------------------------------------------------
# INTENT PATTERNS
# Each intent maps to a list of regex patterns.
# Patterns are matched case-insensitively.
# --------------------------------------------------
INTENT_PATTERNS = {
    "greeting": [
        r"\b(hi|hello|hey|good\s*(morning|afternoon|evening))\b",
    ],
    "leave_balance": [
        r"\bleave\s*balance\b",
        r"\bhow\s*many\s*leaves?\b",
        r"\bremaining\s*leave\b",
        r"\bleaves?\s*(left|remaining|available)\b",
    ],
    "apply_leave": [
        r"\bapply\s*(for\s*)?leave\b",
        r"\brequest\s*leave\b",
        r"\btake\s*(a\s*)?leave\b",
        r"\bwant\s*(to\s*)?leave\b",
        r"\bneed\s*(a\s*)?day\s*off\b",
    ],
    "attendance_status": [
        r"\battendance\b",
        r"\bpresent\s*percentage\b",
        r"\bhow\s*many\s*days\s*(present|absent)\b",
        r"\bmy\s*attendance\b",
    ],
    "payroll_query": [
        r"\bsalary\b",
        r"\bpayroll\b",
        r"\bpay\s*slip\b",
        r"\bwhen\s*(will\s*)?(i\s*)?(get\s*)?paid\b",
        r"\blast\s*paid\b",
        r"\bbonus\b",
        r"\bcompensation\b",
    ],
    "policy_question": [
        r"\bpolicy\b",
        r"\brule\b",
        r"\bguideline\b",
        r"\bwork\s*from\s*home\b",
        r"\bwfh\b",
        r"\bremote\s*work\b",
        r"\bdress\s*code\b",
        r"\bworking\s*hours?\b",
    ],
}


def detect_intent(text: str) -> str:
    """
    Detect the intent of the given text.

    Args:
        text: Transcribed speech text from the employee.

    Returns:
        Intent string (e.g. 'leave_balance', 'payroll_query', 'unknown').
    """
    text_lower = text.lower().strip()

    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                logger.info(f"Intent detected: {intent} (matched: {pattern})")
                return intent

    logger.info("Intent: unknown – no pattern matched.")
    return "unknown"
