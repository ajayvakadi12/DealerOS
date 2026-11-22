from decimal import Decimal
from datetime import date
import pytest
from reconcile.comparison import reconcile_records, Disagreement


@pytest.fixture
def loc_map():
    return {
        'LOC-101': 'ORG-A',
        'LOC-102': 'ORG-A',
        'LOC-103': 'ORG-A',
        'LOC-201': 'ORG-B',
        'LOC-202': 'ORG-B',
    }


def test_clean_matching_row(loc_map):
    """Test 9: Clean matching row produces no disagreement."""
    a_records = [{
        'record_id': 'REC-1001',
        'location_id': 'LOC-101',
        'event_date': date(2026, 3, 20),
        'total_value': Decimal('150.00'),
        'state': 'CONFIRMED'
    }]
    b_entries = [{
        'entry_id': 'ENT/2026/4001',
        'record_ref': 'REC-1001',
        'location_id': 'LOC-101',
        'recorded_on': date(2026, 3, 20),
        'value': Decimal('150.00'),
        'label': 'Normal entry'
    }]
    disagreements = reconcile_records(a_records, b_entries, loc_map)
    assert len(disagreements) == 0


def test_missing_in_b_detection(loc_map):
    """Test 1: System A record with no System B entry is flagged MISSING_IN_B."""
    a_records = [{
        'record_id': 'REC-1015',
        'location_id': 'LOC-103',
        'event_date': date(2026, 4, 2),
        'total_value': Decimal('41095.33'),
        'state': 'CONFIRMED'
    }]
    b_entries = []
    disagreements = reconcile_records(a_records, b_entries, loc_map)
    assert len(disagreements) == 1
    d = disagreements[0]
    assert d.reason == 'MISSING_IN_B'
    assert d.record_id == 'REC-1015'
    assert d.owning_org == 'ORG-A'
    assert d.a_value == Decimal('41095.33')
    assert d.b_value is None


def test_orphan_in_b_detection(loc_map):
    """Test 2 & 20: Orphan B entry references non-existent record, owned by B's location org."""
    a_records = []
    b_entries = [{
        'entry_id': 'ENT/2026/4901',
        'record_ref': 'REC-1999',
        'location_id': 'LOC-102',
        'recorded_on': date(2026, 3, 18),
        'value': Decimal('41250.00'),
        'label': 'Orphan'
    }]
    disagreements = reconcile_records(a_records, b_entries, loc_map)
    assert len(disagreements) == 1
    d = disagreements[0]
    assert d.reason == 'ORPHAN_IN_B'
    assert d.record_id == 'REC-1999'
    assert d.entry_id == 'ENT/2026/4901'
    assert d.owning_org == 'ORG-A'  # LOC-102 belongs to ORG-A
    assert d.b_value == Decimal('41250.00')
    assert d.a_value is None


def test_duplicate_b_entries_identical_amounts(loc_map):
    """Test 3: Multiple B entries with identical amounts that do not equal split sum flag DUPLICATE_IN_B."""
    a_records = [{
        'record_id': 'REC-1042',
        'location_id': 'LOC-101',
        'event_date': date(2026, 3, 4),
        'total_value': Decimal('112837.06'),
        'state': 'CONFIRMED'
    }]
    b_entries = [
        {
            'entry_id': 'ENT/2026/4042',
            'record_ref': 'REC-1042',
            'location_id': 'LOC-101',
            'recorded_on': date(2026, 3, 4),
            'value': Decimal('112837.06'),
        },
        {
            'entry_id': 'ENT/2026/4902',
            'record_ref': 'REC-1042',
            'location_id': 'LOC-101',
            'recorded_on': date(2026, 3, 4),
            'value': Decimal('112837.06'),
        }
    ]
    disagreements = reconcile_records(a_records, b_entries, loc_map)
    assert len(disagreements) == 1
    d = disagreements[0]
    assert d.reason == 'DUPLICATE_IN_B'
    assert d.record_id == 'REC-1042'
    assert 'ENT/2026/4042' in d.entry_id
    assert 'ENT/2026/4902' in d.entry_id
    assert d.a_value == Decimal('112837.06')
    assert d.b_value == Decimal('225674.12')
    assert d.difference == Decimal('112837.06')


def test_valid_split_entries_not_flagged(loc_map):
    """Test 7: Valid split entries whose Decimal sum equals A total_value are NOT flagged."""
    a_records = [{
        'record_id': 'REC-1055',
        'location_id': 'LOC-103',
        'event_date': date(2026, 3, 14),
        'total_value': Decimal('179877.32'),
        'state': 'CONFIRMED'
    }]
    b_entries = [
        {
            'entry_id': 'ENT/2026/4055',
            'record_ref': 'REC-1055',
            'location_id': 'LOC-103',
            'recorded_on': date(2026, 3, 14),
            'value': Decimal('71950.93'),
        },
        {
            'entry_id': 'ENT/2026/4903',
            'record_ref': 'REC-1055',
            'location_id': 'LOC-103',
            'recorded_on': date(2026, 3, 14),
            'value': Decimal('107926.39'),
        }
    ]
    disagreements = reconcile_records(a_records, b_entries, loc_map)
    assert len(disagreements) == 0


def test_value_mismatch_detection(loc_map):
    """Test 4: Value mismatch when B reports different amount from A total_value."""
    a_records = [{
        'record_id': 'REC-1003',
        'location_id': 'LOC-202',
        'event_date': date(2026, 3, 4),
        'total_value': Decimal('121388.01'),
        'state': 'CONFIRMED'
    }]
    b_entries = [{
        'entry_id': 'ENT/2026/4003',
        'record_ref': 'REC-1003',
        'location_id': 'LOC-202',
        'recorded_on': date(2026, 3, 4),
        'value': Decimal('94834.38'),  # matches base_value, not total_value!
    }]
    disagreements = reconcile_records(a_records, b_entries, loc_map)
    assert len(disagreements) == 1
    d = disagreements[0]
    assert d.reason == 'VALUE_MISMATCH'
    assert d.record_id == 'REC-1003'
    assert d.a_value == Decimal('121388.01')
    assert d.b_value == Decimal('94834.38')
    assert d.difference == Decimal('26553.63')


def test_blank_b_value_handling(loc_map):
    """Test 5: Blank B value flagged as VALUE_MISMATCH, not converted to 0."""
    a_records = [{
        'record_id': 'REC-1050',
        'location_id': 'LOC-202',
        'event_date': date(2026, 3, 20),
        'total_value': Decimal('160405.85'),
        'state': 'CONFIRMED'
    }]
    b_entries = [{
        'entry_id': 'ENT/2026/4050',
        'record_ref': 'REC-1050',
        'location_id': 'LOC-202',
        'recorded_on': date(2026, 3, 20),
        'value': None,  # Blank amount
    }]
    disagreements = reconcile_records(a_records, b_entries, loc_map)
    assert len(disagreements) == 1
    d = disagreements[0]
    assert d.reason == 'VALUE_MISMATCH'
    assert d.record_id == 'REC-1050'
    assert d.b_value is None
    assert d.difference is None  # Unknown, NOT a - 0!


def test_location_mismatch(loc_map):
    """Test 10: Location mismatch detected when A and B report different locations."""
    a_records = [{
        'record_id': 'REC-1077',
        'location_id': 'LOC-102',
        'event_date': date(2026, 3, 19),
        'total_value': Decimal('83361.40'),
        'state': 'CONFIRMED'
    }]
    b_entries = [{
        'entry_id': 'ENT/2026/4077',
        'record_ref': 'REC-1077',
        'location_id': 'LOC-201',
        'recorded_on': date(2026, 3, 19),
        'value': Decimal('83361.40'),
    }]
    disagreements = reconcile_records(a_records, b_entries, loc_map)
    assert len(disagreements) == 1
    d = disagreements[0]
    assert d.reason == 'LOCATION_MISMATCH'
    assert d.record_id == 'REC-1077'
    assert d.a_location_id == 'LOC-102'
    assert d.b_location_id == 'LOC-201'
    assert d.is_cross_tenant is True


def test_date_mismatch(loc_map):
    """Test 11: Date mismatch detected when A event_date != B recorded_on."""
    a_records = [{
        'record_id': 'REC-1009',
        'location_id': 'LOC-201',
        'event_date': date(2026, 3, 31),
        'total_value': Decimal('111699.30'),
        'state': 'CONFIRMED'
    }]
    b_entries = [{
        'entry_id': 'ENT/2026/4009',
        'record_ref': 'REC-1009',
        'location_id': 'LOC-201',
        'recorded_on': date(2026, 4, 2),
        'value': Decimal('111699.30'),
    }]
    disagreements = reconcile_records(a_records, b_entries, loc_map)
    assert len(disagreements) == 1
    d = disagreements[0]
    assert d.reason == 'DATE_MISMATCH'
    assert d.record_id == 'REC-1009'
    assert d.a_date == date(2026, 3, 31)
    assert d.b_date == date(2026, 4, 2)


def test_voided_record_behavior(loc_map):
    """
    Test 12:
    - VOIDED record without B entry does not generate MISSING_IN_B.
    - VOIDED record with active B entry generates VOIDED_RECORD_IN_B.
    """
    # Case 1: VOIDED with B entry -> VOIDED_RECORD_IN_B
    a_voided_with_b = [{
        'record_id': 'REC-1019',
        'location_id': 'LOC-202',
        'event_date': date(2026, 4, 5),
        'total_value': Decimal('57092.35'),
        'state': 'VOIDED'
    }]
    b_active = [{
        'entry_id': 'ENT/2026/4019',
        'record_ref': 'REC-1019',
        'location_id': 'LOC-202',
        'recorded_on': date(2026, 4, 5),
        'value': Decimal('57092.35'),
    }]
    res1 = reconcile_records(a_voided_with_b, b_active, loc_map)
    assert len(res1) == 1
    assert res1[0].reason == 'VOIDED_RECORD_IN_B'
    assert res1[0].record_id == 'REC-1019'

    # Case 2: VOIDED without B entry -> NO disagreement generated
    res2 = reconcile_records(a_voided_with_b, [], loc_map)
    assert len(res2) == 0
