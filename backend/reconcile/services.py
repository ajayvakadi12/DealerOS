"""
Reconciliation Service Layer.

Bridges Django ORM queries with the pure comparison engine,
enforcing strict multi-tenant database scoping and data redaction.
"""

from typing import List, Dict, Any, Optional
from decimal import Decimal
from django.db.models import Q
from .models import Location, SystemARecord, SystemBEntry
from .comparison import reconcile_records, Disagreement


class ReconciliationService:
    @staticmethod
    def get_location_org_map() -> Dict[str, str]:
        """Returns mapping of location_id -> org_id from database."""
        return {loc.location_id: loc.org_id for loc in Location.objects.all()}

    @classmethod
    def get_disagreements_for_tenant(
        cls,
        org_id: str,
        reason: Optional[str] = None,
        sort_by: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves tenant-isolated disagreements for a specific organization.
        
        Strict tenant scoping:
        1. Query System A records owned by org_id (via location__org_id).
        2. Query corresponding System B entries that reference those System A records.
        3. Query orphan System B entries whose B location belongs to org_id.
        4. Pass only these scoped records into the reconciliation engine.
        5. Filter by reason and sort by value if requested.
        6. Redact foreign-tenant location data before returning results.
        """
        if not org_id:
            raise ValueError("Organization parameter 'org' is mandatory.")

        # Validate org exists in database
        valid_orgs = set(Location.objects.values_list('org_id', flat=True).distinct())
        if org_id not in valid_orgs:
            raise ValueError(f"Invalid organization '{org_id}'. Available organizations: {sorted(list(valid_orgs))}")

        location_org_map = cls.get_location_org_map()

        # 1. System A records owned by org_id
        a_records = list(
            SystemARecord.objects.filter(location__org_id=org_id)
            .select_related('location')
        )
        a_record_ids = [a.record_id for a in a_records]

        # 2. B entries referencing this tenant's A records + orphan B entries belonging to this tenant's locations
        # B entries that match tenant's A records:
        b_matched_entries = list(
            SystemBEntry.objects.filter(record_ref__in=a_record_ids)
            .select_related('location')
        )

        # All existing A record IDs in the entire system (to identify true orphans)
        all_a_record_ids = set(SystemARecord.objects.values_list('record_id', flat=True))

        # Orphan B entries owned by this tenant (location belongs to this org, but ref not in System A)
        b_orphan_entries = list(
            SystemBEntry.objects.filter(location__org_id=org_id)
            .exclude(record_ref__in=all_a_record_ids)
            .select_related('location')
        )

        # Combine B entries for reconciliation
        scoped_b_entries = list({b.entry_id: b for b in (b_matched_entries + b_orphan_entries)}.values())

        # Run pure comparison engine
        raw_disagreements = reconcile_records(
            a_records=a_records,
            b_entries=scoped_b_entries,
            location_org_map=location_org_map
        )

        # Enforce that all results returned belong to org_id
        tenant_disagreements = [d for d in raw_disagreements if d.owning_org == org_id]

        # Filter by reason if requested
        if reason:
            reason_upper = reason.strip().upper()
            tenant_disagreements = [d for d in tenant_disagreements if d.reason == reason_upper]

        # Convert to serialized dicts with cross-tenant redaction
        serialized = [d.to_dict(target_org=org_id) for d in tenant_disagreements]

        # Sorting
        if sort_by:
            descending = sort_by.startswith('-')
            field_name = sort_by.lstrip('-').lower()

            def sort_key(item):
                if field_name == 'value':
                    # Determine value for sorting: prefer difference, else b_value, else a_value
                    diff = item.get('difference')
                    if diff is not None:
                        try:
                            return Decimal(diff)
                        except Exception:
                            pass
                    val_b = item.get('b_value')
                    if val_b is not None:
                        try:
                            return Decimal(val_b)
                        except Exception:
                            pass
                    val_a = item.get('a_value')
                    if val_a is not None:
                        try:
                            return Decimal(val_a)
                        except Exception:
                            pass
                    return Decimal('-Infinity') if descending else Decimal('Infinity')
                elif field_name == 'record_id':
                    return item.get('record_id') or ''
                elif field_name == 'reason':
                    return item.get('reason') or ''
                return ''

            serialized.sort(key=sort_key, reverse=descending)

        return serialized

    @classmethod
    def get_summary_metrics(cls, org_id: str) -> Dict[str, int]:
        """
        Returns summary card statistics strictly for the specified tenant.
        Does not count foreign tenant records.
        """
        disagreements = cls.get_disagreements_for_tenant(org_id=org_id)
        counts = {
            'total_disagreements': len(disagreements),
            'missing_in_b': sum(1 for d in disagreements if d['reason'] == 'MISSING_IN_B'),
            'orphan_in_b': sum(1 for d in disagreements if d['reason'] == 'ORPHAN_IN_B'),
            'duplicate_in_b': sum(1 for d in disagreements if d['reason'] == 'DUPLICATE_IN_B'),
            'value_mismatch': sum(1 for d in disagreements if d['reason'] == 'VALUE_MISMATCH'),
            'location_mismatch': sum(1 for d in disagreements if d['reason'] == 'LOCATION_MISMATCH'),
            'date_mismatch': sum(1 for d in disagreements if d['reason'] == 'DATE_MISMATCH'),
        }
        return counts
