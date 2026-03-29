import re
from mock_data import MOMO_DB

PHONE_PATTERN = re.compile(r"^0[2357][0-9]{8}$")
CANDIDATE_PATTERN = re.compile(r"\+?\d[\d\s\-()]{7,}\d")

# Twi/English spoken digit words → digit character.
# Covers ASR output where numbers are spoken digit-by-digit.
_DIGIT_WORDS = {
    # Twi phonetic forms
    "sero": "0", "sirow": "0", "sɛro": "0",
    "wɔn": "1", "won": "1",
    "tu": "2", "tuu": "2",
    "tri": "3", "tiri": "3",
    "fɔ": "4", "fo": "4", "foa": "4",
    "faif": "5", "faifi": "5",
    "seks": "6", "sɛks": "6",
    "sɛvɛn": "7", "seven": "7", "sɛvɛ": "7",
    "eit": "8", "ɛit": "8", "eight": "8",
    "nain": "9", "naen": "9",
    # English fallbacks
    "zero": "0", "one": "1", "two": "2", "three": "3",
    "four": "4", "five": "5", "six": "6",
    "nine": "9",
}

def _parse_token(token):
    """
    Try to resolve a single ASR token to one or more digit characters.
    Handles exact matches, greedy prefix matches for compound tokens
    (e.g. ASR collapses 'four four' → 'foɔfɔɔ').
    Returns a digit string or None.
    """
    if not token:
        return None
    if re.fullmatch(r"\d+", token):
        return token  # already a digit string
    if token in _DIGIT_WORDS:
        return _DIGIT_WORDS[token]

    # Greedy prefix scan: try to consume the token by matching known words
    result = []
    remaining = token
    # Sort by length descending so longer words are tried first
    sorted_words = sorted(_DIGIT_WORDS.keys(), key=len, reverse=True)
    while remaining:
        matched = False
        for word in sorted_words:
            if remaining.startswith(word):
                result.append(_DIGIT_WORDS[word])
                remaining = remaining[len(word):]
                matched = True
                break
        if not matched:
            # Skip a single character (handles ɔ/o vowel suffixes the ASR appends)
            remaining = remaining[1:]
    return "".join(result) if result else None


def spoken_words_to_digits(text):
    """
    Convert a string of spoken digit words (from ASR) into a digit string.

    Uses a sliding-window approach so filler words before/after the number
    (e.g. "me number ne sero tu foɔfoɔ...") don't discard the whole utterance.
    Returns the first contiguous run of digit tokens whose total digit length
    falls in the plausible phone-number range (9-12 digits), or None.
    """
    raw_tokens = re.split(r"[\s,]+", text.lower().strip())
    tokens = [t.strip(".,!?") for t in raw_tokens if t.strip(".,!?")]

    for start in range(len(tokens)):
        digits = []
        for token in tokens[start:]:
            parsed = _parse_token(token)
            if parsed:
                digits.append(parsed)
            else:
                break  # end of this contiguous run
        digit_str = "".join(digits)
        if 9 <= len(digit_str) <= 12:
            return digit_str

    return None


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

    # 1. Look for digit sequences (works for typed text)
    for chunk in CANDIDATE_PATTERN.findall(text):
        normalized = normalize_ghana_mobile(chunk)
        if normalized:
            return normalized

    # 2. Compact fallback (separators removed)
    compact = re.sub(r"[\s\-()]", "", text)
    result = normalize_ghana_mobile(compact)
    if result:
        return result

    # 3. Spoken digit words from ASR (e.g. "sero tu foɔfɔɔ wɔn tu tri fɔ faif seks")
    digit_str = spoken_words_to_digits(text)
    if digit_str:
        return normalize_ghana_mobile(digit_str)

    return None


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
