import pytest
from decimal import Decimal
from datetime import date
from reconcile.models import Location, SystemARecord, SystemBEntry
from reconcile.services import ReconciliationService
from reconcile.importer import DataImporter


@pytest.fixture(autouse=True)
def load_db_data(db):
    """Load baseline CSV dataset into DB for tenant tests."""
    importer = DataImporter()
    importer.import_all()


def test_org_a_and_org_b_isolation():
    """
    Test mandatory items 17 & 18:
    - ORG-A results contain only ORG-A owned records.
    - ORG-B results contain only ORG-B owned records.
    - Zero data leaks across organizational boundaries.
    """
    org_a_results = ReconciliationService.get_disagreements_for_tenant('ORG-A')
    org_b_results = ReconciliationService.get_disagreements_for_tenant('ORG-B')

    assert len(org_a_results) > 0
    assert len(org_b_results) > 0

    # Ensure every single result returned for ORG-A has owning_org == 'ORG-A'
    for item in org_a_results:
        assert item['owning_org'] == 'ORG-A'

    # Ensure every single result returned for ORG-B has owning_org == 'ORG-B'
    for item in org_b_results:
        assert item['owning_org'] == 'ORG-B'

    # Ensure distinct disjoint record sets
    a_rec_ids = {item['record_id'] for item in org_a_results if item['record_id']}
    b_rec_ids = {item['record_id'] for item in org_b_results if item['record_id']}
    assert a_rec_ids.isdisjoint(b_rec_ids)


def test_cross_tenant_location_redaction():
    """
    Test mandatory item 19:
    System A: REC-1077 (LOC-102 -> ORG-A)
    System B: ENT/2026/4077 (LOC-201 -> ORG-B)
    - Matched record belongs to ORG-A.
    - ORG-A sees disagreement with foreign location redacted.
    - ORG-B cannot see REC-1077 at all.
    """
    org_a_results = ReconciliationService.get_disagreements_for_tenant('ORG-A')
    rec1077_a = [r for r in org_a_results if r['record_id'] == 'REC-1077']
    assert len(rec1077_a) == 1
    item = rec1077_a[0]
    assert item['reason'] == 'LOCATION_MISMATCH'
    assert item['owning_org'] == 'ORG-A'
    assert item['a_location'] == 'LOC-102'
    assert item['b_location'] == '[REDACTED - FOREIGN TENANT]'
    assert 'LOC-201' not in item['b_location']
    assert 'LOC-201' not in item['location']

    # Confirm ORG-B does not receive REC-1077
    org_b_results = ReconciliationService.get_disagreements_for_tenant('ORG-B')
    rec1077_b = [r for r in org_b_results if r['record_id'] == 'REC-1077']
    assert len(rec1077_b) == 0


def test_orphan_ownership():
    """
    Test mandatory item 20:
    Orphan B entry ENT/2026/4901 has location LOC-102 (ORG-A).
    Must belong to ORG-A, invisible to ORG-B.
    """
    org_a_results = ReconciliationService.get_disagreements_for_tenant('ORG-A')
    orphan_a = [r for r in org_a_results if r['entry_id'] == 'ENT/2026/4901']
    assert len(orphan_a) == 1
    assert orphan_a[0]['reason'] == 'ORPHAN_IN_B'
    assert orphan_a[0]['owning_org'] == 'ORG-A'

    org_b_results = ReconciliationService.get_disagreements_for_tenant('ORG-B')
    orphan_b = [r for r in org_b_results if r['entry_id'] == 'ENT/2026/4901']
    assert len(orphan_b) == 0


def test_invalid_organization_parameter():
    """Test mandatory item 21: Invalid organization raises ValueError."""
    with pytest.raises(ValueError, match="Invalid organization"):
        ReconciliationService.get_disagreements_for_tenant('ORG-INVALID')

    with pytest.raises(ValueError, match="mandatory"):
        ReconciliationService.get_disagreements_for_tenant('')


def test_reason_filtering():
    """Test mandatory item 22: Filter disagreements by reason."""
    missing_results = ReconciliationService.get_disagreements_for_tenant('ORG-A', reason='MISSING_IN_B')
    assert len(missing_results) == 1
    assert missing_results[0]['reason'] == 'MISSING_IN_B'
    assert missing_results[0]['record_id'] == 'REC-1015'

    # Filter with non-existent reason returns empty list
    nonexistent = ReconciliationService.get_disagreements_for_tenant('ORG-A', reason='NONEXISTENT_REASON')
    assert nonexistent == []


def test_sorting_behavior():
    """
    Test mandatory item 23:
    Sort by value ascending and descending.
    """
    asc_results = ReconciliationService.get_disagreements_for_tenant('ORG-A', sort_by='value')
    desc_results = ReconciliationService.get_disagreements_for_tenant('ORG-A', sort_by='-value')

    assert len(asc_results) == len(desc_results)
    assert len(asc_results) > 1

    # Extract non-null difference values
    asc_diffs = [Decimal(r['difference']) for r in asc_results if r['difference'] is not None]
    desc_diffs = [Decimal(r['difference']) for r in desc_results if r['difference'] is not None]

    # Verify order
    assert asc_diffs == sorted(asc_diffs)
    assert desc_diffs == sorted(desc_diffs, reverse=True)
