import csv
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from django.db import transaction
from .models import Location, SystemARecord, SystemBEntry
from .normalization import parse_amount, normalize_ref, parse_date, clean_string

logger = logging.getLogger(__name__)


class CSVImportSummary:
    def __init__(self):
        self.locations_read = 0
        self.locations_saved = 0
        self.system_a_read = 0
        self.system_a_saved = 0
        self.system_b_read = 0
        self.system_b_saved = 0
        
        self.blank_values = 0
        self.invalid_amounts = 0
        self.invalid_dates = 0
        self.normalized_refs = 0
        self.unrecognized_refs = 0
        self.unknown_locations = 0
        self.import_errors = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            'locations_read': self.locations_read,
            'locations_saved': self.locations_saved,
            'system_a_read': self.system_a_read,
            'system_a_saved': self.system_a_saved,
            'system_b_read': self.system_b_read,
            'system_b_saved': self.system_b_saved,
            'blank_values': self.blank_values,
            'invalid_amounts': self.invalid_amounts,
            'invalid_dates': self.invalid_dates,
            'normalized_refs': self.normalized_refs,
            'unrecognized_refs': self.unrecognized_refs,
            'unknown_locations': self.unknown_locations,
            'import_errors_count': len(self.import_errors),
            'import_errors': self.import_errors,
        }


class DataImporter:
    """
    Robust, idempotent CSV importer for DealerOS.
    Survives all dirty data without silently dropping rows.
    """
    def __init__(self, data_dir: Optional[Path] = None):
        if data_dir is None:
            # Default to backend/data directory
            data_dir = Path(__file__).resolve().parent.parent / 'data'
        self.data_dir = Path(data_dir)
        self.summary = CSVImportSummary()

    def import_all(self) -> CSVImportSummary:
        """
        Imports in strict order:
        1. locations.csv
        2. system_a.csv
        3. system_b.csv
        """
        self.summary = CSVImportSummary()
        locations_file = self.data_dir / 'locations.csv'
        system_a_file = self.data_dir / 'system_a.csv'
        system_b_file = self.data_dir / 'system_b.csv'

        self.import_locations(locations_file)
        self.import_system_a(system_a_file)
        self.import_system_b(system_b_file)

        return self.summary

    def import_locations(self, file_path: Path):
        logger.info(f"Importing locations from {file_path}")
        with open(file_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row_idx, row in enumerate(reader, start=2):
                self.summary.locations_read += 1
                try:
                    loc_id = clean_string(row.get('location_id'))
                    org_id = clean_string(row.get('org_id'))
                    name = clean_string(row.get('location_name') or row.get('name'))

                    if not loc_id or not org_id:
                        self.summary.import_errors.append(f"Row {row_idx}: Missing location_id or org_id: {row}")
                        continue

                    Location.objects.update_or_create(
                        location_id=loc_id,
                        defaults={
                            'org_id': org_id,
                            'name': name
                        }
                    )
                    self.summary.locations_saved += 1
                except Exception as e:
                    logger.exception(f"Error importing location row {row_idx}: {e}")
                    self.summary.import_errors.append(f"Row {row_idx}: Exception {str(e)}")

    def import_system_a(self, file_path: Path):
        logger.info(f"Importing System A records from {file_path}")
        # Cache locations
        location_cache = {loc.location_id: loc for loc in Location.objects.all()}

        with open(file_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row_idx, row in enumerate(reader, start=2):
                self.summary.system_a_read += 1
                try:
                    record_id = clean_string(row.get('record_id'))
                    if not record_id:
                        self.summary.import_errors.append(f"System A Row {row_idx}: Missing record_id")
                        continue

                    loc_raw = row.get('location_id')
                    loc_cleaned = clean_string(loc_raw)
                    location_obj = location_cache.get(loc_cleaned) if loc_cleaned else None
                    if loc_cleaned and not location_obj:
                        self.summary.unknown_locations += 1

                    # Date parsing
                    event_date_raw = row.get('event_date')
                    event_date = parse_date(event_date_raw)
                    if clean_string(event_date_raw) and event_date is None:
                        self.summary.invalid_dates += 1

                    # Amounts parsing
                    base_val_raw = row.get('base_value')
                    base_val = parse_amount(base_val_raw)
                    if clean_string(base_val_raw) and base_val is None:
                        self.summary.invalid_amounts += 1

                    adj_raw = row.get('adjustment')
                    adj_val = parse_amount(adj_raw)
                    if clean_string(adj_raw) and adj_val is None:
                        self.summary.invalid_amounts += 1

                    tot_raw = row.get('total_value')
                    tot_val = parse_amount(tot_raw)
                    if clean_string(tot_raw) and tot_val is None:
                        self.summary.invalid_amounts += 1

                    # Track blank values
                    for field in ('event_date', 'category_code', 'actor_id', 'base_value', 'adjustment', 'total_value'):
                        if not clean_string(row.get(field)):
                            self.summary.blank_values += 1

                    state = clean_string(row.get('state')) or 'CONFIRMED'

                    SystemARecord.objects.update_or_create(
                        record_id=record_id,
                        defaults={
                            'location': location_obj,
                            'location_id_raw': loc_raw,
                            'event_date': event_date,
                            'event_date_raw': event_date_raw,
                            'category_code': clean_string(row.get('category_code')),
                            'actor_id': clean_string(row.get('actor_id')),
                            'base_value': base_val,
                            'base_value_raw': base_val_raw,
                            'adjustment': adj_val,
                            'adjustment_raw': adj_raw,
                            'total_value': tot_val,
                            'total_value_raw': tot_raw,
                            'state': state,
                        }
                    )
                    self.summary.system_a_saved += 1
                except Exception as e:
                    logger.exception(f"Error importing System A row {row_idx}: {e}")
                    self.summary.import_errors.append(f"System A Row {row_idx}: {str(e)}")

    def import_system_b(self, file_path: Path):
        logger.info(f"Importing System B entries from {file_path}")
        location_cache = {loc.location_id: loc for loc in Location.objects.all()}

        with open(file_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row_idx, row in enumerate(reader, start=2):
                self.summary.system_b_read += 1
                try:
                    entry_id = clean_string(row.get('entry_id'))
                    if not entry_id:
                        self.summary.import_errors.append(f"System B Row {row_idx}: Missing entry_id")
                        continue

                    ref_raw = row.get('record_ref')
                    norm_ref = normalize_ref(ref_raw)
                    if not norm_ref and clean_string(ref_raw):
                        self.summary.unrecognized_refs += 1
                    elif norm_ref and norm_ref != ref_raw:
                        self.summary.normalized_refs += 1

                    loc_raw = row.get('location_id')
                    loc_cleaned = clean_string(loc_raw)
                    location_obj = location_cache.get(loc_cleaned) if loc_cleaned else None
                    if loc_cleaned and not location_obj:
                        self.summary.unknown_locations += 1

                    # Date parsing
                    rec_on_raw = row.get('recorded_on')
                    rec_on = parse_date(rec_on_raw)
                    if clean_string(rec_on_raw) and rec_on is None:
                        self.summary.invalid_dates += 1

                    # Value parsing
                    val_raw = row.get('value')
                    val = parse_amount(val_raw)
                    if clean_string(val_raw) and val is None:
                        self.summary.invalid_amounts += 1

                    # Blank checks
                    if not clean_string(ref_raw):
                        self.summary.blank_values += 1
                    if not clean_string(loc_raw):
                        self.summary.blank_values += 1
                    if not clean_string(rec_on_raw):
                        self.summary.blank_values += 1
                    if not clean_string(val_raw):
                        self.summary.blank_values += 1

                    label = clean_string(row.get('label'))

                    SystemBEntry.objects.update_or_create(
                        entry_id=entry_id,
                        defaults={
                            'record_ref_raw': ref_raw,
                            'record_ref': norm_ref,
                            'location': location_obj,
                            'location_id_raw': loc_raw,
                            'recorded_on': rec_on,
                            'recorded_on_raw': rec_on_raw,
                            'value': val,
                            'value_raw': val_raw,
                            'label': label,
                        }
                    )
                    self.summary.system_b_saved += 1
                except Exception as e:
                    logger.exception(f"Error importing System B row {row_idx}: {e}")
                    self.summary.import_errors.append(f"System B Row {row_idx}: {str(e)}")
