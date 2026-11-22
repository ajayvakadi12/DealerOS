import pytest
from decimal import Decimal
from django.core.management import call_command
from reconcile.models import Location, SystemARecord, SystemBEntry
from reconcile.importer import DataImporter


@pytest.mark.django_db
def test_importer_preserves_every_row_and_idempotency():
    """
    Test mandatory items 14 & 15:
    - Importer accounts for 5 locations, 120 System A rows, 121 System B rows.
    - Importer is strictly idempotent: running twice creates zero duplicates.
    """
    importer = DataImporter()
    summary1 = importer.import_all()

    assert summary1.locations_saved == 5
    assert summary1.system_a_saved == 120
    assert summary1.system_b_saved == 121
    assert Location.objects.count() == 5
    assert SystemARecord.objects.count() == 120
    assert SystemBEntry.objects.count() == 121

    # Second run for idempotency
    summary2 = importer.import_all()
    assert summary2.locations_saved == 5
    assert summary2.system_a_saved == 120
    assert summary2.system_b_saved == 121
    assert Location.objects.count() == 5
    assert SystemARecord.objects.count() == 120
    assert SystemBEntry.objects.count() == 121


@pytest.mark.django_db
def test_invalid_values_do_not_crash_importer_and_preserves_raw(tmp_path):
    """
    Test mandatory item 13:
    Invalid amounts, malformed dates, and blank values must not crash importer.
    Raw source strings must be preserved alongside parsed values.
    """
    loc_file = tmp_path / "locations.csv"
    loc_file.write_text("location_id,org_id,location_name\nLOC-999,ORG-TEST,Test Loc\n", encoding="utf-8")

    a_file = tmp_path / "system_a.csv"
    a_file.write_text(
        "record_id,location_id,event_date,category_code,actor_id,base_value,adjustment,total_value,state\n"
        "REC-DIRTY,LOC-999,invalid-date,CAT-01,USR-1,bad-num,10.00,corrupted,CONFIRMED\n",
        encoding="utf-8"
    )

    b_file = tmp_path / "system_b.csv"
    b_file.write_text(
        "entry_id,record_ref,location_id,recorded_on,value,label\n"
        "ENT-DIRTY,recdirty,LOC-999,bad-date,not-a-val,Dirty entry\n",
        encoding="utf-8"
    )

    importer = DataImporter(data_dir=tmp_path)
    summary = importer.import_all()

    assert summary.system_a_saved == 1
    assert summary.system_b_saved == 1

    a_rec = SystemARecord.objects.get(record_id="REC-DIRTY")
    assert a_rec.event_date is None
    assert a_rec.event_date_raw == "invalid-date"
    assert a_rec.base_value is None
    assert a_rec.base_value_raw == "bad-num"
    assert a_rec.total_value is None
    assert a_rec.total_value_raw == "corrupted"

    b_ent = SystemBEntry.objects.get(entry_id="ENT-DIRTY")
    assert b_ent.record_ref is None  # 'recdirty' has no digits, so parsed ref is None
    assert b_ent.record_ref_raw == "recdirty"
    assert b_ent.recorded_on is None
    assert b_ent.recorded_on_raw == "bad-date"
    assert b_ent.value is None
    assert b_ent.value_raw == "not-a-val"


@pytest.mark.django_db
def test_unknown_location_handling(tmp_path):
    """
    Test mandatory item 16:
    Rows with unmapped locations are preserved; location FK is null and raw string retained.
    """
    loc_file = tmp_path / "locations.csv"
    loc_file.write_text("location_id,org_id,location_name\nLOC-101,ORG-A,Loc 101\n", encoding="utf-8")

    a_file = tmp_path / "system_a.csv"
    a_file.write_text(
        "record_id,location_id,event_date,category_code,actor_id,base_value,adjustment,total_value,state\n"
        "REC-UNK,LOC-NONEXISTENT,2026-01-01,CAT-01,USR-1,100.00,0.00,100.00,CONFIRMED\n",
        encoding="utf-8"
    )

    b_file = tmp_path / "system_b.csv"
    b_file.write_text(
        "entry_id,record_ref,location_id,recorded_on,value,label\n"
        "ENT-UNK,REC-UNK,LOC-NONEXISTENT,2026-01-01,100.00,Entry\n",
        encoding="utf-8"
    )

    importer = DataImporter(data_dir=tmp_path)
    summary = importer.import_all()

    assert summary.unknown_locations == 2
    assert summary.system_a_saved == 1
    assert summary.system_b_saved == 1

    a_rec = SystemARecord.objects.get(record_id="REC-UNK")
    assert a_rec.location is None
    assert a_rec.location_id_raw == "LOC-NONEXISTENT"

    b_ent = SystemBEntry.objects.get(entry_id="ENT-UNK")
    assert b_ent.location is None
    assert b_ent.location_id_raw == "LOC-NONEXISTENT"
