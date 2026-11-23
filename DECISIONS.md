# DealerOS: Architectural & Engineering Decisions

This document outlines key technical decisions made during the design and implementation of DealerOS, detailing the decision, rejected alternatives, and underlying rationale.

---

## 1. Django and SQLite Selection
- **Decision**: Used Django 5.x with Django REST Framework and SQLite database.
- **Alternative Rejected**: PostgreSQL, MySQL, Dockerized setups, or microframeworks (e.g., Flask/FastAPI with SQLAlchemy).
- **Reasoning**: The dataset consists of exactly 120 System A rows, 121 System B entries, and 5 locations. SQLite provides zero-configuration, robust ACID guarantees, and zero network latency. Introducing Docker or external database engines adds operational fragility without performance benefit.

---

## 2. Using `Decimal` for Monetary Values
- **Decision**: Stored and calculated all financial amounts using Python's `Decimal` and Django's `DecimalField(max_digits=14, decimal_places=2)`.
- **Alternative Rejected**: Python `float` or database floating-point types (`FloatField`).
- **Reasoning**: IEEE 754 floating-point arithmetic introduces binary rounding errors (e.g. `0.1 + 0.2 != 0.3`). Financial reconciliation requires exact base-10 precision to correctly detect discrepancies down to the cent and validate split allocations.

---

## 3. Comparing System B Against System A `total_value`
- **Decision**: Reconciled System B `value` against System A `total_value` (`base_value + adjustment`).
- **Alternative Rejected**: Comparing against System A `base_value`.
- **Reasoning**: System A represents financial events where adjustments modify base amounts into a net transaction figure (`total_value`). In System B, entries reflect final settlement charges (as evidenced by REC-1003, where System B entered base_value and is flagged as a value mismatch).

---

## 4. Normalizing System B References Without Modifying Raw Data
- **Decision**: Implemented `normalize_ref(raw)` using regular expressions to extract numeric identifiers into standard `REC-<digits>` format, while saving the original reference string in `record_ref_raw`.
- **Alternative Rejected**: Rejecting irregular references or mutating source CSV data.
- **Reasoning**: Real exports contain varied formats (`rec1034`, ` REC - 1070 `, `1112`). Normalizing enables deterministic grouping while raw storage guarantees auditability. References without identifiable digits return `None`, correctly classifying them as orphans.

---

## 5. Dual-Field Storage (Preserving Raw Values)
- **Decision**: Designed the database schema with paired fields (e.g., `event_date` + `event_date_raw`, `value` + `value_raw`, `location` FK + `location_id_raw`).
- **Alternative Rejected**: Overwriting or discarding unparseable values during import.
- **Reasoning**: Real-world data ingestion pipelines must survive corrupt inputs without silent data loss. Storing raw values ensures unparseable rows are preserved and visible for forensic auditing.

---

## 6. Validating Split Entries as Non-Errors
- **Decision**: Allowed multiple System B entries for a single System A record to be accepted as a `VALID SPLIT` if and only if all B entry values are present and their Decimal sum exactly equals System A `total_value`.
- **Alternative Rejected**: Relying solely on the `label` text (e.g., "part 1 of 2") or flagging all multi-entry records as duplicates.
- **Reasoning**: Transactional splits frequently occur in settlement systems. If multiple entries sum to the exact event total (e.g., REC-1055: 71,950.93 + 107,926.39 = 179,877.32), flagging them as duplicates or value mismatches would be a false positive. If amounts are missing or do not sum to the total, `DUPLICATE_IN_B` is generated.

---

## 7. Categorization of Missing System B Values and Voided Records
- **Decision**: Entries in System B with blank or missing values are categorized as `MISSING_IN_B` (with difference set to System A's `total_value`). In addition, records marked `VOIDED` in System A that have matching entries in System B (e.g., REC-1019) are reconciled by financial value, location, and date rather than flagged as void errors, since System B has no void concept. Cancelled System A records without System B entries do not generate disagreements.
- **Alternative Rejected**: Flagging missing B values as `VALUE_MISMATCH` with undefined differences, or manufacturing a custom `VOIDED_RECORD_IN_B` error for valid settlement entries.
- **Reasoning**: A missing value in System B represents an unrecorded or missing financial amount, making `MISSING_IN_B` the accurate category with clear monetary difference. Because System B does not record transaction lifecycle states (like VOIDED), treating identical matching records as errors creates false positives in tenant audits.

---

## 8. Backend-Enforced Multi-Tenant Isolation & Redaction
- **Decision**: Scoped all queries strictly by `Location.org_id` at the database level before serialization, and redacted foreign-tenant location details (`[REDACTED - FOREIGN TENANT]`) on cross-tenant mismatches.
- **Alternative Rejected**: Fetching all records and filtering in the React frontend.
- **Reasoning**: Client-side filtering leaks data across tenant boundaries in network payloads. The authoritative ownership mapping (`locations.csv`) dictates tenant ownership: matched records belong to System A's location tenant, while orphans belong to System B's location tenant. Foreign location information is withheld to prevent reconnaissance.

---

## 9. Excluding Authentication and Containerization
- **Decision**: Excluded authentication frameworks (JWT/OAuth) and Docker containerization.
- **Alternative Rejected**: Adding full user login sessions and multi-container Docker Compose.
- **Reasoning**: The take-home brief explicitly stated that authentication, visual design, and performance are not tested. Adding authentication tokens would obscure tenant evaluation; specifying `?org=ORG-A` as an explicit tenant scope provides a clear, inspectable interface.
