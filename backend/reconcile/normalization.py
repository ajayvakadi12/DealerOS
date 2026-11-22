import re
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from typing import Optional


def parse_amount(raw: Optional[str]) -> Optional[Decimal]:
    """
    Parses a monetary amount string into a Decimal.
    
    Rules:
    - Strips whitespace.
    - Removes commas (supports standard international and Indian numbering formats like 1,25,400.00).
    - Blank or whitespace-only strings return None (unknown, NOT zero).
    - Unparseable or malformed values return None (NOT zero).
    - Never uses float to preserve exact financial precision.
    """
    if raw is None:
        return None
    cleaned = str(raw).strip()
    if not cleaned:
        return None
    # Remove commas used as thousands / lakh separators
    cleaned = cleaned.replace(',', '')
    try:
        val = Decimal(cleaned)
        if not val.is_finite():
            return None
        return val
    except (InvalidOperation, TypeError, ValueError):
        return None


def normalize_ref(raw: Optional[str]) -> Optional[str]:
    """
    Normalizes a System B record reference into standard 'REC-<digits>' format.
    
    Examples:
    - "REC-1034" -> "REC-1034"
    - "rec1034" -> "REC-1034"
    - " REC - 1070 " -> "REC-1070"
    - "1112" -> "REC-1112"
    - References without identifiable digits return None.
    """
    if raw is None:
        return None
    cleaned = str(raw).strip()
    if not cleaned:
        return None
    match = re.search(r'(\d+)', cleaned)
    if match:
        return f"REC-{match.group(1)}"
    return None


def parse_date(raw: Optional[str]) -> Optional[date]:
    """
    Safely parses date strings into datetime.date.
    
    Rules:
    - Returns None for blank or invalid dates.
    - Does not raise exceptions on malformed dates.
    """
    if raw is None:
        return None
    cleaned = str(raw).strip()
    if not cleaned:
        return None
    for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%d-%m-%Y', '%d/%m/%Y'):
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    return None


def clean_string(raw: Optional[str]) -> Optional[str]:
    """
    Trims whitespace and returns None if string is empty.
    """
    if raw is None:
        return None
    cleaned = str(raw).strip()
    return cleaned if cleaned else None
