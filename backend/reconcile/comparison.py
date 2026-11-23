"""
Core Reconciliation Engine for DealerOS.

Pure Python comparison engine:
- Does NOT depend on Django requests, views, or HTTP responses.
- Accepts normalized data structures and returns structured disagreement results.
- Preserves exact Decimal arithmetic (never floats for money).
- Implements strict multi-tenant isolation rules and redaction.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from datetime import date
from typing import Dict, List, Optional, Any


@dataclass
class Disagreement:
    reason: str
    record_id: Optional[str]
    entry_id: Optional[str]
    owning_org: str
    a_location_id: Optional[str]
    b_location_id: Optional[str]
    a_value: Optional[Decimal]
    b_value: Optional[Decimal]
    difference: Optional[Decimal]
    a_date: Optional[date]
    b_date: Optional[date]
    description: str
    is_cross_tenant: bool = False
    details: Optional[Dict[str, Any]] = None

    def to_dict(self, target_org: Optional[str] = None) -> Dict[str, Any]:
        """
        Serializes disagreement to dictionary.
        If target_org is provided and this is a cross-tenant disagreement,
        foreign tenant location details are redacted across all fields including description.
        """
        b_loc = self.b_location_id
        desc = self.description
        if self.is_cross_tenant and target_org and self.owning_org == target_org:
            b_loc = "[REDACTED - FOREIGN TENANT]"
            if self.b_location_id:
                desc = desc.replace(self.b_location_id, "[REDACTED - FOREIGN TENANT]")

        # Format combined location display
        if self.reason == 'LOCATION_MISMATCH':
            location_display = f"{self.a_location_id} (System A) / {b_loc} (System B)"
        elif self.a_location_id:
            location_display = self.a_location_id
        elif b_loc:
            location_display = b_loc
        else:
            location_display = "Unknown"

        # Non-monetary disagreements without value differences should yield None (dash in UI)
        diff_str = None
        if self.difference is not None and self.difference != Decimal('0.00'):
            diff_str = str(self.difference)
        elif self.reason in ('VALUE_MISMATCH', 'DUPLICATE_IN_B') and self.difference is not None:
            diff_str = str(self.difference)

        return {
            'reason': self.reason,
            'record_id': self.record_id,
            'entry_id': self.entry_id,
            'owning_org': self.owning_org,
            'location': location_display,
            'a_location': self.a_location_id,
            'b_location': b_loc,
            'a_value': str(self.a_value) if self.a_value is not None else None,
            'b_value': str(self.b_value) if self.b_value is not None else None,
            'difference': diff_str,
            'a_date': self.a_date.isoformat() if self.a_date else None,
            'b_date': self.b_date.isoformat() if self.b_date else None,
            'description': desc,
            'is_cross_tenant': self.is_cross_tenant,
            'details': self.details,
        }


def _extract(obj: Any, key: str, default: Any = None) -> Any:
    """Helper to read from object attributes or dictionary keys."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    if hasattr(obj, key):
        val = getattr(obj, key)
        return val() if callable(val) else val
    return default


def _get_location_id(obj: Any) -> Optional[str]:
    """Helper to extract location_id string from model instance or dict."""
    loc = _extract(obj, 'location')
    if loc:
        if isinstance(loc, str):
            return loc
        if hasattr(loc, 'location_id'):
            return loc.location_id
        if isinstance(loc, dict):
            return loc.get('location_id')
    loc_raw = _extract(obj, 'location_id') or _extract(obj, 'location_id_raw')
    if loc_raw:
        return str(loc_raw).strip()
    return None


def reconcile_records(
    a_records: List[Any],
    b_entries: List[Any],
    location_org_map: Dict[str, str]
) -> List[Disagreement]:
    """
    Core reconciliation algorithm.
    
    Parameters:
    - a_records: List of System A records.
    - b_entries: List of System B entries.
    - location_org_map: Dict mapping location_id -> org_id (authoritative tenant mapping).
    
    Returns:
    - List[Disagreement]
    """
    disagreements: List[Disagreement] = []

    # Step 1 & 2: Group System B entries by normalized reference
    b_by_ref: Dict[str, List[Any]] = {}
    for b in b_entries:
        ref = _extract(b, 'record_ref')
        if ref:
            b_by_ref.setdefault(ref, []).append(b)
        else:
            # Entry has no recognizable reference at all -> ORPHAN_IN_B
            b_loc_id = _get_location_id(b)
            owning_org = location_org_map.get(b_loc_id, 'UNKNOWN_ORG')
            entry_id = _extract(b, 'entry_id')
            b_val = _extract(b, 'value')
            b_date = _extract(b, 'recorded_on')
            disagreements.append(
                Disagreement(
                    reason='ORPHAN_IN_B',
                    record_id=None,
                    entry_id=entry_id,
                    owning_org=owning_org,
                    a_location_id=None,
                    b_location_id=b_loc_id,
                    a_value=None,
                    b_value=b_val,
                    difference=b_val,
                    a_date=None,
                    b_date=b_date,
                    description=f"Entry {entry_id} has no valid record reference."
                )
            )

    matched_refs = set()

    # Step 3 & 4: Iterate through System A records
    for a in a_records:
        rec_id = _extract(a, 'record_id')
        a_loc_id = _get_location_id(a)
        owning_org = location_org_map.get(a_loc_id, 'UNKNOWN_ORG')
        a_state = _extract(a, 'state')
        a_total = _extract(a, 'total_value')
        a_date = _extract(a, 'event_date')

        corresponding_b = b_by_ref.get(rec_id, [])
        if rec_id in b_by_ref:
            matched_refs.add(rec_id)

        # VOIDED Record Handling Policy:
        # System A records marked VOIDED with no B entry do not generate MISSING_IN_B (expected cancellation).
        # If an entry exists in B, it proceeds to normal comparison (financial/date/location matching).
        if a_state == 'VOIDED' and not corresponding_b:
            continue

        # 6.1 MISSING_IN_B (No entry at all in System B)
        if not corresponding_b:
            disagreements.append(
                Disagreement(
                    reason='MISSING_IN_B',
                    record_id=rec_id,
                    entry_id=None,
                    owning_org=owning_org,
                    a_location_id=a_loc_id,
                    b_location_id=None,
                    a_value=a_total,
                    b_value=None,
                    difference=a_total,
                    a_date=a_date,
                    b_date=None,
                    description=f"Record {rec_id} exists in System A but has no corresponding entry in System B."
                )
            )
            continue

        # Multiple entries handling (6.3 DUPLICATE_IN_B vs 6.4 VALID SPLIT)
        if len(corresponding_b) > 1:
            entry_ids = ", ".join([str(_extract(b, 'entry_id')) for b in corresponding_b])
            b_values = [_extract(b, 'value') for b in corresponding_b]
            has_unknown_b_val = any(v is None for v in b_values)
            
            # Check if valid split:
            # All values present, sum == a_total
            if not has_unknown_b_val and a_total is not None:
                sum_b = sum(b_values, Decimal('0.00'))
                if sum_b == a_total:
                    # VALID SPLIT!
                    # "A valid split is not an error."
                    # "Do not flag the entries as duplicates or value mismatches."
                    # However, verify location and date consistency across entries
                    for b in corresponding_b:
                        b_loc = _get_location_id(b)
                        b_ent_id = _extract(b, 'entry_id')
                        b_org = location_org_map.get(b_loc)
                        is_cross = bool(b_loc and a_loc_id and b_org and b_org != owning_org)
                        if b_loc and a_loc_id and b_loc != a_loc_id:
                            disagreements.append(
                                Disagreement(
                                    reason='LOCATION_MISMATCH',
                                    record_id=rec_id,
                                    entry_id=b_ent_id,
                                    owning_org=owning_org,
                                    a_location_id=a_loc_id,
                                    b_location_id=b_loc,
                                    a_value=a_total,
                                    b_value=_extract(b, 'value'),
                                    difference=None,
                                    a_date=a_date,
                                    b_date=_extract(b, 'recorded_on'),
                                    description=f"Split entry {b_ent_id} location ({b_loc}) does not match System A ({a_loc_id}).",
                                    is_cross_tenant=is_cross
                                )
                            )
                        b_d = _extract(b, 'recorded_on')
                        if a_date and b_d and a_date != b_d:
                            disagreements.append(
                                Disagreement(
                                    reason='DATE_MISMATCH',
                                    record_id=rec_id,
                                    entry_id=b_ent_id,
                                    owning_org=owning_org,
                                    a_location_id=a_loc_id,
                                    b_location_id=b_loc,
                                    a_value=a_total,
                                    b_value=_extract(b, 'value'),
                                    difference=None,
                                    a_date=a_date,
                                    b_date=b_d,
                                    description=f"Split entry {b_ent_id} date ({b_d}) does not match System A date ({a_date}).",
                                    is_cross_tenant=is_cross
                                )
                            )
                    continue
                else:
                    # Sum does not equal A total -> DUPLICATE_IN_B
                    b_loc = _get_location_id(corresponding_b[0])
                    b_org = location_org_map.get(b_loc)
                    is_cross = bool(b_loc and a_loc_id and b_org and b_org != owning_org)
                    disagreements.append(
                        Disagreement(
                            reason='DUPLICATE_IN_B',
                            record_id=rec_id,
                            entry_id=entry_ids,
                            owning_org=owning_org,
                            a_location_id=a_loc_id,
                            b_location_id=b_loc,
                            a_value=a_total,
                            b_value=sum_b,
                            difference=abs(a_total - sum_b),
                            a_date=a_date,
                            b_date=_extract(corresponding_b[0], 'recorded_on'),
                            description=f"Multiple entries ({entry_ids}) in System B for record {rec_id} do not form a valid split (sum={sum_b}, A total={a_total}).",
                            is_cross_tenant=is_cross,
                            details={'entries': [{'entry_id': _extract(b, 'entry_id'), 'value': str(_extract(b, 'value'))} for b in corresponding_b]}
                        )
                    )
                    continue
            else:
                # One or more values unknown -> DUPLICATE_IN_B / cannot be split
                b_loc = _get_location_id(corresponding_b[0])
                b_org = location_org_map.get(b_loc)
                is_cross = bool(b_loc and a_loc_id and b_org and b_org != owning_org)
                disagreements.append(
                    Disagreement(
                        reason='DUPLICATE_IN_B',
                        record_id=rec_id,
                        entry_id=entry_ids,
                        owning_org=owning_org,
                        a_location_id=a_loc_id,
                        b_location_id=b_loc,
                        a_value=a_total,
                        b_value=None,
                        difference=None,
                        a_date=a_date,
                        b_date=_extract(corresponding_b[0], 'recorded_on'),
                        description=f"Multiple entries ({entry_ids}) in System B for record {rec_id} with missing values cannot be validated as a split.",
                        is_cross_tenant=is_cross
                    )
                )
                continue

        # Single corresponding B entry
        b = corresponding_b[0]
        entry_id = _extract(b, 'entry_id')
        b_val = _extract(b, 'value')
        b_loc_id = _get_location_id(b)
        b_date = _extract(b, 'recorded_on')

        b_org = location_org_map.get(b_loc_id)
        is_cross_tenant = bool(b_loc_id and a_loc_id and b_org and b_org != owning_org)

        # 6.5 Blank or missing value in System B -> MISSING_IN_B
        if b_val is None:
            disagreements.append(
                Disagreement(
                    reason='MISSING_IN_B',
                    record_id=rec_id,
                    entry_id=entry_id,
                    owning_org=owning_org,
                    a_location_id=a_loc_id,
                    b_location_id=b_loc_id,
                    a_value=a_total,
                    b_value=None,
                    difference=a_total,
                    a_date=a_date,
                    b_date=b_date,
                    description=f"Record {rec_id} has value missing in System B (Entry {entry_id}).",
                    is_cross_tenant=is_cross_tenant
                )
            )
        # 6.6 VALUE_MISMATCH
        # Compare SystemBEntry.value against SystemARecord.total_value (never base_value)
        elif a_total is None or b_val != a_total:
            diff = abs(a_total - b_val) if a_total is not None else None
            disagreements.append(
                Disagreement(
                    reason='VALUE_MISMATCH',
                    record_id=rec_id,
                    entry_id=entry_id,
                    owning_org=owning_org,
                    a_location_id=a_loc_id,
                    b_location_id=b_loc_id,
                    a_value=a_total,
                    b_value=b_val,
                    difference=diff,
                    a_date=a_date,
                    b_date=b_date,
                    description=f"Value mismatch for record {rec_id}: System A total is {a_total}, System B reported {b_val}.",
                    is_cross_tenant=is_cross_tenant
                )
            )

        # 6.6 LOCATION_MISMATCH
        if a_loc_id and b_loc_id and a_loc_id != b_loc_id:
            loc_diff = abs(a_total - b_val) if (a_total is not None and b_val is not None and a_total != b_val) else None
            disagreements.append(
                Disagreement(
                    reason='LOCATION_MISMATCH',
                    record_id=rec_id,
                    entry_id=entry_id,
                    owning_org=owning_org,
                    a_location_id=a_loc_id,
                    b_location_id=b_loc_id,
                    a_value=a_total,
                    b_value=b_val,
                    difference=loc_diff,
                    a_date=a_date,
                    b_date=b_date,
                    description=f"Location mismatch for record {rec_id}: System A at {a_loc_id}, System B at {b_loc_id}.",
                    is_cross_tenant=is_cross_tenant
                )
            )

        # 6.7 DATE_MISMATCH
        # Only compare valid parsed dates
        if a_date and b_date and a_date != b_date:
            date_diff = abs(a_total - b_val) if (a_total is not None and b_val is not None and a_total != b_val) else None
            disagreements.append(
                Disagreement(
                    reason='DATE_MISMATCH',
                    record_id=rec_id,
                    entry_id=entry_id,
                    owning_org=owning_org,
                    a_location_id=a_loc_id,
                    b_location_id=b_loc_id,
                    a_value=a_total,
                    b_value=b_val,
                    difference=date_diff,
                    a_date=a_date,
                    b_date=b_date,
                    description=f"Date mismatch for record {rec_id}: System A date is {a_date}, System B date is {b_date}.",
                    is_cross_tenant=is_cross_tenant
                )
            )

    # Step 6: Detect orphan entries in B
    # When a B entry references a record that does not exist in A
    for ref, b_list in b_by_ref.items():
        if ref not in matched_refs:
            for b in b_list:
                b_loc_id = _get_location_id(b)
                owning_org = location_org_map.get(b_loc_id, 'UNKNOWN_ORG')
                entry_id = _extract(b, 'entry_id')
                b_val = _extract(b, 'value')
                b_date = _extract(b, 'recorded_on')
                disagreements.append(
                    Disagreement(
                        reason='ORPHAN_IN_B',
                        record_id=ref,
                        entry_id=entry_id,
                        owning_org=owning_org,
                        a_location_id=None,
                        b_location_id=b_loc_id,
                        a_value=None,
                        b_value=b_val,
                        difference=b_val,
                        a_date=None,
                        b_date=b_date,
                        description=f"Orphan entry {entry_id} in System B references record {ref} which does not exist in System A."
                    )
                )

    return disagreements
