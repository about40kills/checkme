import re
from mock_data import MOMO_DB

PHONE_PATTERN = re.compile(r"^0[2357][0-9]{8}$")
CANDIDATE_PATTERN = re.compile(r"\+?\d[\d\s\-()]{7,}\d")


def normalize_ghana_mobile(raw):
    """Normalize mobile numbers to canonical 0XXXXXXXXX format."""
    if not raw:
        return None

    digits = re.sub(r"\D", "", raw)
    candidate = digits

    if digits.startswith("233") and len(digits) == 12:
        candidate = "0" + digits[3:]
    elif len(digits) == 9 and digits[0] in {"2", "3", "5", "7"}:
        candidate = "0" + digits
    elif len(digits) == 10 and digits.startswith("0"):
        candidate = digits

    if PHONE_PATTERN.match(candidate):
        return candidate
    return None


def normalize_number(raw):
    """Backward-compatible alias used by existing tests."""
    return normalize_ghana_mobile(raw)


def extract_number(text):
    """Extract and normalize the first valid Ghanaian mobile number in text."""
    if not text:
        return None

    for chunk in CANDIDATE_PATTERN.findall(text):
        normalized = normalize_ghana_mobile(chunk)
        if normalized:
            return normalized

    # Fallback for compact text with separators removed.
    compact = re.sub(r"[\s\-()]", "", text)
    return normalize_ghana_mobile(compact)


def lookup_record(number):
    """Look up a full record by normalized phone number."""
    normalized = normalize_ghana_mobile(number)
    if not normalized:
        return None
    return MOMO_DB.get(normalized)


def lookup_name(number):
    """Look up display name by normalized phone number."""
    record = lookup_record(number)
    return record["display_name"] if record else None
