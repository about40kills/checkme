import json
import re
from pathlib import Path

PHONE_PATTERN = re.compile(r"^0[2357][0-9]{8}$")
DATA_FILE = Path(__file__).resolve().parent / "data" / "momo_db.json"


def _load_records():
    with DATA_FILE.open("r", encoding="utf-8") as f:
        records = json.load(f)

    if not isinstance(records, list):
        raise ValueError("momo_db.json must contain a list of records.")

    seen = set()
    normalized = []
    for record in records:
        phone = record.get("phone", "")
        display_name = record.get("display_name", "")
        if not PHONE_PATTERN.match(phone):
            raise ValueError(f"Invalid Ghana mobile number in data: {phone}")
        if not display_name:
            raise ValueError(f"Missing display_name for {phone}")
        if phone in seen:
            raise ValueError(f"Duplicate phone in momo_db.json: {phone}")
        seen.add(phone)
        normalized.append(record)
    return normalized


MOMO_RECORDS = _load_records()
MOMO_DB = {record["phone"]: record for record in MOMO_RECORDS}
