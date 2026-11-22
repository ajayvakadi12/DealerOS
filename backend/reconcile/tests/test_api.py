import pytest
from rest_framework.test import APIClient
from reconcile.importer import DataImporter


@pytest.fixture(autouse=True)
def setup_db(db):
    importer = DataImporter()
    importer.import_all()


def test_api_missing_org_parameter():
    client = APIClient()
    response = client.get('/api/disagreements/')
    assert response.status_code == 400
    assert "mandatory" in response.data['error']


def test_api_invalid_org_parameter():
    client = APIClient()
    response = client.get('/api/disagreements/?org=ORG-UNKNOWN')
    assert response.status_code == 400
    assert "Invalid organization" in response.data['error']


def test_api_valid_org_a_returns_disagreements():
    client = APIClient()
    response = client.get('/api/disagreements/?org=ORG-A')
    assert response.status_code == 200
    assert isinstance(response.data, list)
    assert len(response.data) == 7
    for item in response.data:
        assert item['owning_org'] == 'ORG-A'


def test_api_valid_org_b_returns_disagreements():
    client = APIClient()
    response = client.get('/api/disagreements/?org=ORG-B')
    assert response.status_code == 200
    assert isinstance(response.data, list)
    assert len(response.data) == 5
    for item in response.data:
        assert item['owning_org'] == 'ORG-B'


def test_api_reason_filtering():
    client = APIClient()
    # Filter by VALUE_MISMATCH
    response = client.get('/api/disagreements/?org=ORG-A&reason=VALUE_MISMATCH')
    assert response.status_code == 200
    assert len(response.data) == 3
    for item in response.data:
        assert item['reason'] == 'VALUE_MISMATCH'

    # Filter with invalid reason
    bad_resp = client.get('/api/disagreements/?org=ORG-A&reason=INVALID_REASON')
    assert bad_resp.status_code == 400
    assert "Invalid reason" in bad_resp.data['error']


def test_api_sorting():
    client = APIClient()
    response_asc = client.get('/api/disagreements/?org=ORG-A&sort=value')
    assert response_asc.status_code == 200
    assert len(response_asc.data) == 7

    response_desc = client.get('/api/disagreements/?org=ORG-A&sort=-value')
    assert response_desc.status_code == 200
    assert len(response_desc.data) == 7

    # Bad sort parameter
    bad_sort = client.get('/api/disagreements/?org=ORG-A&sort=invalid_col')
    assert bad_sort.status_code == 400
    assert "Invalid sort" in bad_sort.data['error']


def test_api_cross_tenant_redaction():
    client = APIClient()
    response = client.get('/api/disagreements/?org=ORG-A')
    assert response.status_code == 200
    rec1077 = [d for d in response.data if d['record_id'] == 'REC-1077']
    assert len(rec1077) == 1
    assert rec1077[0]['b_location'] == '[REDACTED - FOREIGN TENANT]'
    assert 'LOC-201' not in rec1077[0]['location']
    assert 'LOC-201' not in rec1077[0]['description']
    assert 'LOC-201' not in str(response.data)
    assert rec1077[0]['difference'] is None  # Non-monetary mismatch difference is null (dash in UI)


def test_api_summary_metrics():
    client = APIClient()
    response = client.get('/api/summary/?org=ORG-A')
    assert response.status_code == 200
    data = response.data
    assert data['total_disagreements'] == 7
    assert data['missing_in_b'] == 1
    assert data['orphan_in_b'] == 1
    assert data['duplicate_in_b'] == 1
    assert data['value_mismatch'] == 3
    assert data['location_mismatch'] == 1


def test_api_organizations_list():
    client = APIClient()
    response = client.get('/api/organizations/')
    assert response.status_code == 200
    assert response.data['organizations'] == ['ORG-A', 'ORG-B']
