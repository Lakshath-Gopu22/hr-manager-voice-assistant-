"""
Intent Service – Hybrid NLP Intent Classifier (spaCy + Regex Fallback).

Uses spaCy's PhraseMatcher and token Matcher for smart, linguistically-
aware intent detection.  Falls back to regex patterns when spaCy finds
no match.  The public API (detect_intent) is unchanged.

Supported intents:
    - greeting
    - leave_balance
    - apply_leave
    - attendance_status
    - payroll_query
    - policy_question
    - unknown  (fallback)
"""

import re
import logging

import spacy
from spacy.matcher import PhraseMatcher, Matcher

logger = logging.getLogger(__name__)

# --------------------------------------------------
# 1. LOAD SPACY MODEL (once at import time)
# --------------------------------------------------
try:
    nlp = spacy.load("en_core_web_sm")
    logger.info("spaCy model 'en_core_web_sm' loaded successfully.")
except OSError:
    logger.warning(
        "spaCy model 'en_core_web_sm' not found. "
        "Run: python -m spacy download en_core_web_sm"
    )
    nlp = None

# --------------------------------------------------
# 2. PHRASE MATCHER – exact multi-word phrases
#    (case-insensitive via LOWER attribute)
# --------------------------------------------------
PHRASE_INTENT_MAP: dict[str, list[str]] = {
    "greeting": [
        "hi", "hello", "hey", "good morning",
        "good afternoon", "good evening",
    ],
    "leave_balance": [
        "leave balance", "remaining leave", "leaves left",
        "leaves remaining", "leaves available",
        "leave remaining", "leave available",
    ],
    "apply_leave": [
        "apply leave", "apply for leave", "request leave",
        "take leave", "take a leave", "day off",
        "need a day off", "time off",
    ],
    "attendance_status": [
        "attendance", "present percentage",
        "my attendance", "attendance status",
        "days present", "days absent",
    ],
    "payroll_query": [
        "salary", "payroll", "pay slip", "payslip",
        "bonus", "compensation", "my pay",
        "salary slip", "salary details",
    ],
    "policy_question": [
        "policy", "rule", "guideline", "work from home",
        "wfh", "remote work", "dress code", "working hours",
        "company policy", "company rules",
    ],
}

# --------------------------------------------------
# 3. TOKEN MATCHER – lemma / POS patterns
#    Catches natural variations like:
#      "I want to apply for a leave" / "check my leaves"
# --------------------------------------------------
TOKEN_PATTERNS: dict[str, list[list[dict]]] = {
    "leave_balance": [
        # "how many leaves (do I have / left / remaining)"
        [
            {"LOWER": "how"},
            {"LOWER": "many"},
            {"LEMMA": {"IN": ["leave", "leaf"]}},
        ],
        # "check/show my leave(s)"
        [
            {"LEMMA": {"IN": ["check", "show", "view", "see", "tell"]}},
            {"OP": "?"},  # optional word like "me" / "my"
            {"OP": "?"},
            {"LEMMA": {"IN": ["leave", "leaf"]}},
        ],
        # "remaining/available leave(s)" – any word order
        [
            {"LEMMA": {"IN": ["remaining", "available", "left"]}},
            {"OP": "?"},
            {"LEMMA": {"IN": ["leave", "leaf"]}},
        ],
        # "leave(s) remaining/available/left"
        [
            {"LEMMA": {"IN": ["leave", "leaf"]}},
            {"OP": "?"},
            {"LEMMA": {"IN": ["remaining", "available", "left"]}},
        ],
        # "my leave(s)" – simple possessive
        [
            {"LOWER": "my"},
            {"OP": "?"},
            {"LEMMA": {"IN": ["leave", "leaf"]}},
        ],
    ],
    "apply_leave": [
        # "apply / request / submit (for) (a) leave"
        [
            {"LEMMA": {"IN": ["apply", "request", "submit"]}},
            {"OP": "?"},
            {"OP": "?"},
            {"LEMMA": {"IN": ["leave", "leaf"]}},
        ],
        # "want/need (to take) (a) leave / day off"
        [
            {"LEMMA": {"IN": ["want", "need"]}},
            {"OP": "?"},
            {"OP": "?"},
            {"LEMMA": {"IN": ["leave", "leaf", "off"]}},
        ],
        # "take a day off / take time off"
        [
            {"LEMMA": "take"},
            {"OP": "?"},
            {"OP": "?"},
            {"LOWER": "off"},
        ],
    ],
    "attendance_status": [
        # "my attendance / attendance percentage"
        [
            {"OP": "?"},
            {"LOWER": "attendance"},
            {"OP": "?"},
        ],
    ],
    "payroll_query": [
        # "when will I get paid"
        [
            {"LOWER": "when"},
            {"OP": "?"},
            {"OP": "?"},
            {"LEMMA": {"IN": ["pay", "paid"]}},
        ],
        # "show/tell my salary / pay"
        [
            {"LEMMA": {"IN": ["show", "tell", "check", "view", "see"]}},
            {"OP": "?"},
            {"OP": "?"},
            {"LEMMA": {"IN": ["salary", "pay", "payroll", "compensation"]}},
        ],
    ],
    "policy_question": [
        # "what is the _ policy / rules"
        [
            {"OP": "?"},
            {"OP": "?"},
            {"OP": "?"},
            {"LEMMA": {"IN": ["policy", "rule", "guideline"]}},
        ],
    ],
}

# --------------------------------------------------
# 4. BUILD MATCHERS (only if model loaded)
# --------------------------------------------------
_phrase_matcher = None
_token_matcher = None
_phrase_intent_lookup: dict[str, str] = {}

if nlp is not None:
    _phrase_matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    _token_matcher = Matcher(nlp.vocab)

    # Register phrase patterns
    for intent, phrases in PHRASE_INTENT_MAP.items():
        patterns = [nlp.make_doc(phrase) for phrase in phrases]
        _phrase_matcher.add(intent, patterns)

    # Register token patterns
    for intent, patterns in TOKEN_PATTERNS.items():
        _token_matcher.add(intent, patterns)

    logger.info(
        f"spaCy matchers initialised – "
        f"{sum(len(v) for v in PHRASE_INTENT_MAP.values())} phrases, "
        f"{sum(len(v) for v in TOKEN_PATTERNS.values())} token patterns."
    )

# --------------------------------------------------
# 5. REGEX FALLBACK PATTERNS (unchanged from original)
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


# ==================================================
# PUBLIC API
# ==================================================

def detect_intent(text: str) -> str:
    """
    Detect the intent of the given text.

    Strategy:
        1. spaCy PhraseMatcher  (exact multi-word phrases)
        2. spaCy token Matcher   (lemma / POS patterns)
        3. Regex fallback        (original patterns)
        4. Return 'unknown'

    Args:
        text: Transcribed speech text from the employee.

    Returns:
        Intent string (e.g. 'leave_balance', 'payroll_query', 'unknown').
    """
    text_clean = text.strip()

    # --- Layer 1 & 2: spaCy-based detection ---
    if nlp is not None and _phrase_matcher is not None:
        intent = _spacy_detect(text_clean)
        if intent:
            logger.info(f"Intent detected (spaCy): {intent}")
            return intent

    # --- Layer 3: Regex fallback ---
    intent = _regex_detect(text_clean)
    if intent:
        logger.info(f"Intent detected (regex fallback): {intent}")
        return intent

    logger.info("Intent: unknown – no pattern matched.")
    return "unknown"


# --------------------------------------------------
# PRIVATE HELPERS
# --------------------------------------------------

def _spacy_detect(text: str) -> str | None:
    """Run spaCy PhraseMatcher then token Matcher."""
    doc = nlp(text)

    # --- PhraseMatcher (highest priority) ---
    phrase_matches = _phrase_matcher(doc)
    if phrase_matches:
        # Pick the longest match (most specific)
        best = max(phrase_matches, key=lambda m: m[2] - m[1])
        intent = nlp.vocab.strings[best[0]]
        return intent

    # --- Token Matcher ---
    token_matches = _token_matcher(doc)
    if token_matches:
        intent = nlp.vocab.strings[token_matches[0][0]]
        return intent

    return None


def _regex_detect(text: str) -> str | None:
    """Original regex-based detection (fallback)."""
    text_lower = text.lower()
    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                return intent
    return None


# ==================================================
# LEAVE TYPE EXTRACTION
# ==================================================

# Regex patterns for leave type detection
_LEAVE_TYPE_PATTERNS = {
    "medical": [
        r"\bmedical\s*(leave)?\b",
        r"\bsick\s*(leave)?\b",
        r"\bhealth\b",
        r"\bdoctor\b",
        r"\bhospital\b",
        r"\bnot\s*(feeling\s*)?well\b",
        r"\billness\b",
        r"\bunwell\b",
    ],
    "earned": [
        r"\bearned\s*(leave)?\b",
        r"\bprivilege\s*(leave)?\b",
        r"\bvacation\b",
        r"\bannual\s*(leave)?\b",
        r"\bplanned\s*(leave)?\b",
    ],
    "casual": [
        r"\bcasual\s*(leave)?\b",
        r"\bpersonal\s*(leave|reason)?\b",
        r"\bfamily\s*(reason|function|emergency)?\b",
    ],
}


def extract_leave_type(text: str) -> str | None:
    """
    Extract the type of leave mentioned in the text.

    Args:
        text: Employee's query text.

    Returns:
        'casual', 'medical', 'earned', or None if no type specified.
    """
    text_lower = text.lower().strip()

    for leave_type, patterns in _LEAVE_TYPE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                logger.info(f"Leave type detected: {leave_type}")
                return leave_type

    logger.info("No specific leave type mentioned.")
    return None


# ==================================================
# DATE EXTRACTION
# ==================================================

def extract_dates(text: str) -> tuple:
    """
    Extract start_date and end_date from query text.

    Supports format: YYYY-MM-DD (from HTML date inputs).
    Returns (start_date, end_date) as date objects, or (None, None).
    """
    import re
    from datetime import date as dt_date

    # Match YYYY-MM-DD patterns
    date_matches = re.findall(r"\b(\d{4}-\d{2}-\d{2})\b", text)

    if len(date_matches) >= 2:
        try:
            parts_start = date_matches[0].split("-")
            parts_end = date_matches[1].split("-")
            start = dt_date(int(parts_start[0]), int(parts_start[1]), int(parts_start[2]))
            end = dt_date(int(parts_end[0]), int(parts_end[1]), int(parts_end[2]))
            if end >= start:
                logger.info(f"Dates extracted: {start} to {end}")
                return (start, end)
            else:
                logger.info("End date before start date, swapping.")
                return (end, start)
        except (ValueError, IndexError):
            pass

    if len(date_matches) == 1:
        try:
            parts = date_matches[0].split("-")
            single = dt_date(int(parts[0]), int(parts[1]), int(parts[2]))
            logger.info(f"Single date extracted: {single}")
            return (single, single)
        except (ValueError, IndexError):
            pass

    logger.info("No dates found in text.")
    return (None, None)


# ==================================================
# PAYROLL SUB-INTENT EXTRACTION
# ==================================================

_PAYROLL_SUBINTENT_PATTERNS = {
    "breakdown": [
        r"\bbreakdown\b", r"\bbreak\s*down\b", r"\bdetail(s|ed)?\b",
        r"\bfull\s*(salary|payroll)\b", r"\bsalary\s*structure\b",
        r"\bpay\s*structure\b",
    ],
    "deductions": [
        r"\bdeduction(s)?\b", r"\bdeduct(ed)?\b",
        r"\btax\s*deduction(s)?\b", r"\btax(es)?\b",
        r"\bpf\b", r"\bprovident\s*fund\b",
        r"\bprofessional\s*tax\b",
    ],
    "net_salary": [
        r"\bnet\s*(salary|pay)\b", r"\btake\s*home\b",
        r"\bin\s*hand\b", r"\bafter\s*deduction(s)?\b",
    ],
    "credit_date": [
        r"\bcredit\s*date\b", r"\bwhen\s*(will\s*)?(i\s*)?(get\s*)?paid\b",
        r"\bsalary\s*date\b", r"\bnext\s*pay\b",
        r"\bpay\s*day\b", r"\bpayment\s*date\b",
    ],
    "last_month": [
        r"\blast\s*month\b", r"\bprevious\s*month\b",
        r"\blast\s*(salary|pay)\b",
    ],
    "allowances": [
        r"\ballowance(s)?\b", r"\bhra\b",
        r"\bdearness\s*allowance\b", r"\b(da)\b",
        r"\bspecial\s*allowance\b",
    ],
    "annual": [
        r"\bannual\s*(salary|package|ctc)?\b",
        r"\bctc\b", r"\byearly\b",
        r"\bper\s*(year|annum)\b",
    ],
}


def extract_payroll_subintent(text: str) -> str:
    """
    Detect the specific payroll sub-intent from the query text.

    Returns one of: 'breakdown', 'deductions', 'net_salary',
    'credit_date', 'last_month', 'allowances', 'annual', or 'general'.
    """
    text_lower = text.lower().strip()

    for subintent, patterns in _PAYROLL_SUBINTENT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                logger.info(f"Payroll sub-intent detected: {subintent}")
                return subintent

    logger.info("Payroll sub-intent: general")
    return "general"

