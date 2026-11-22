from decimal import Decimal
from datetime import date
import pytest
from reconcile.normalization import parse_amount, normalize_ref, parse_date, clean_string


def test_amount_parsing_standard():
    assert parse_amount("100.00") == Decimal("100.00")
    assert parse_amount(" 45.50 ") == Decimal("45.50")
    assert parse_amount("1000") == Decimal("1000")


def test_amount_parsing_indian_style():
    """Test mandatory item 6: Indian-style amount parsing (1,25,400.00 -> Decimal('125400.00'))"""
    assert parse_amount("1,25,400.00") == Decimal("125400.00")
    assert parse_amount(" 1,50,00,000.50 ") == Decimal("15000000.50")


def test_amount_parsing_blank_and_invalid():
    """Test mandatory item 5: Blank amounts must return None, NEVER Decimal(0)"""
    assert parse_amount("") is None
    assert parse_amount("   ") is None
    assert parse_amount(None) is None
    assert parse_amount("invalid") is None
    assert parse_amount("N/A") is None


def test_messy_reference_normalization():
    """
    Test mandatory item 8:
    'REC-1034' -> 'REC-1034'
    'rec1034' -> 'REC-1034'
    ' REC - 1070 ' -> 'REC-1070'
    '1112' -> 'REC-1112'
    References without identifiable digits return None.
    """
    assert normalize_ref("REC-1034") == "REC-1034"
    assert normalize_ref("rec1034") == "REC-1034"
    assert normalize_ref(" REC - 1070 ") == "REC-1070"
    assert normalize_ref("1112") == "REC-1112"
    assert normalize_ref("entry_only") is None
    assert normalize_ref("") is None
    assert normalize_ref(None) is None


def test_date_parsing_safe():
    assert parse_date("2026-03-24") == date(2026, 3, 24)
    assert parse_date("2026/04/03") == date(2026, 4, 3)
    assert parse_date("not-a-date") is None
    assert parse_date("") is None
    assert parse_date(None) is None


def test_clean_string():
    assert clean_string("  hello  ") == "hello"
    assert clean_string("   ") is None
    assert clean_string(None) is None
