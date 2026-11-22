# DealerOS Project Rules

- **Precision**: Use Python `Decimal` for all financial values; never use floating-point types for monetary arithmetic.
- **Comparison Standard**: Reconcile System B `value` against System A `total_value` (`base_value + adjustment`).
- **Data Ingestion**: Never silently drop or skip rows. Preserve raw values in `*_raw` attributes. Blank or unparseable numbers must remain `None`, never zero.
- **Valid Splits**: Do not flag multiple entries as duplicates if their Decimal sum exactly equals System A `total_value`.
- **Tenant Isolation**: Scope all queries strictly by `Location.org_id` in backend database queries. Redact foreign-side location data in cross-tenant mismatches.
- **Stack Boundaries**: Pure Python comparison in `comparison.py`; Django REST Framework for API; React + Vite for UI. Keep the backend as the single source of truth.
