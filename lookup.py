import re

from mock_data import MOMO_DB


def normalize_number(number):
    digits = re.sub(r"\D", "", number or "")

    if digits.startswith("233") and len(digits) == 12:
        digits = f"0{digits[3:]}"

    return digits


def extract_number(text):
    cleaned = normalize_number(text)
    match = re.search(r"(0[2357][0-9]{8})", cleaned)
    return match.group(1) if match else None


def lookup_name(number):
    return MOMO_DB.get(normalize_number(number))
