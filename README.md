# DealerOS: Multi-Tenant Data Reconciliation & Disagreement Detection System

A full-stack financial reconciliation platform built to satisfy the **ADOSX Full-Stack Engineering Assessment**.

DealerOS ingests transaction records from two divergent internal sources (**System A** and **System B**), normalizes messy real-world formatting anomalies, executes exact-precision reconciliation comparisons, isolates data strictly across organizational boundaries (**ORG-A** vs **ORG-B**), and surfaces discrepancies through a high-fidelity REST API and React dashboard.

---

## 1. Project Overview
- **System A**: Records transactional events (`120` rows in `system_a.csv`). Primary identifier: `record_id`. Contains base values, adjustments, net total values, and operational states (`CONFIRMED`, `VOIDED`).
- **System B**: Records operational entries (`121` rows in `system_b.csv`). References System A via `record_ref`. Prone to formatting quirks, non-standard number formatting, multiple entries per record, and unlinked references.
- **Locations**: Authoritative tenant mapping (`5` rows in `locations.csv`). Establishes the sole mapping between `location_id` and tenant `org_id` (`ORG-A` and `ORG-B`).

---

## 2. Problem Statement
Neither system is single-handedly authoritative. While most records agree, high-impact discrepancies exist (missing entries, orphan entries, duplicate billings, value discrepancies, cross-tenant location mismatches, and date conflicts). The core engineering objectives are:
1. **Survive Dirty Data**: Never drop or skip a row silently; preserve unparseable raw values.
2. **Reconciliation Correctness**: Catch exact financial disagreements using exact Decimal arithmetic without misclassifying valid split allocations as duplicates.
3. **Multi-Tenant Isolation**: Ensure tenant data never leaks across organizational boundaries, redacting foreign location details in cross-tenant scenarios.

---

## 3. Technology Stack

### Backend
- **Python 3.11+**
- **Django 5.x** & **Django REST Framework (DRF)**
- **SQLite** (Single source of truth)
- **Django ORM**
- Standard Python libraries: `decimal.Decimal`, `re`, `datetime`, `csv`

### Frontend
- **React.js 18**
- **Vite 6**
- **Axios**
- CSS3 (Vanilla, responsive, zero heavy external UI libraries)

### Testing
- **Pytest** & **pytest-django**
- DRF `APIClient` test framework

---

## 4. Architecture

```
dealeros/
├── backend/
│   ├── manage.py
│   ├── pytest.ini
│   ├── config/
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── asgi.py
│   │   └── wsgi.py
│   ├── reconcile/
│   │   ├── models.py             # Location, SystemARecord, SystemBEntry
│   │   ├── importer.py           # Idempotent CSV ingestion pipeline
│   │   ├── normalization.py      # Reference, amount, and date parsing
│   │   ├── comparison.py         # Pure reconciliation engine
│   │   ├── services.py           # Multi-tenant DB query scoping & redaction
│   │   ├── serializers.py        # DRF data serialization
│   │   ├── views.py              # REST API endpoints
│   │   ├── urls.py               # API route routing
│   │   ├── admin.py              # Django admin registration
│   │   ├── management/commands/
│   │   │   └── import_data.py    # CLI import command
│   │   └── tests/
│   │       ├── test_normalization.py
│   │       ├── test_comparison.py
│   │       ├── test_importer.py
│   │       ├── test_tenant_isolation.py
│   │       └── test_api.py
│   └── data/
│       ├── system_a.csv          # 120 rows
│       ├── system_b.csv          # 121 rows
│       └── locations.csv         # 5 locations
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── DashboardHeader.jsx
│   │   │   ├── SummaryCards.jsx
│   │   │   ├── FilterBar.jsx
│   │   │   ├── DisagreementTable.jsx
│   │   │   ├── TableRow.jsx
│   │   │   ├── LoadingState.jsx
│   │   │   └── EmptyState.jsx
│   │   ├── services/
│   │   │   └── api.js
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── package.json
│   ├── vite.config.js
│   └── index.html
├── .gitignore
├── requirements.txt
├── DECISIONS.md
└── README.md
```

---

## 5. Database Schema

1. **`Location`**:
   - `location_id` (`CharField`, Unique, Indexed)
   - `org_id` (`CharField`, Indexed)
   - `name` (`CharField`, Nullable)
2. **`SystemARecord`**:
   - `record_id` (`CharField`, Unique, Indexed)
   - `location` (`ForeignKey(Location)`, Nullable, `on_delete=SET_NULL`)
   - `location_id_raw`, `event_date_raw`, `base_value_raw`, `adjustment_raw`, `total_value_raw`
   - `event_date` (`DateField`, Nullable)
   - `category_code`, `actor_id` (`CharField`, Nullable)
   - `base_value`, `adjustment`, `total_value` (`DecimalField(14, 2)`, Nullable)
   - `state` (`CharField`, Default `'CONFIRMED'`)
3. **`SystemBEntry`**:
   - `entry_id` (`CharField`, Unique, Indexed)
   - `record_ref_raw` (`CharField`, Nullable)
   - `record_ref` (`CharField`, Indexed, Nullable) &mdash; *Notice: NOT a Foreign Key to allow preserving orphans.*
   - `location` (`ForeignKey(Location)`, Nullable, `on_delete=SET_NULL`)
   - `location_id_raw`, `recorded_on_raw`, `value_raw`
   - `recorded_on` (`DateField`, Nullable)
   - `value` (`DecimalField(14, 2)`, Nullable)
   - `label` (`CharField`, Nullable)

---

## 6. Importer & Normalization Rules

### Normalization Logic (`reconcile/normalization.py`)
- **Monetary Amounts (`parse_amount`)**:
  - Removes commas, including Indian numbering formats (`"1,25,400.00"` &rarr; `Decimal("125400.00")`).
  - Blank strings or unparseable values return `None` (representing unknown values, **never converted to zero**).
  - Preserves exact cents using Python's `Decimal`.
- **References (`normalize_ref`)**:
  - Extracts numeric identifier via regex: `"rec1034"` &rarr; `"REC-1034"`, `" REC - 1070 "` &rarr; `"REC-1070"`, `"1112"` &rarr; `"REC-1112"`.
  - References without identifiable digits return `None` (classified as orphans).
- **Dates (`parse_date`)**:
  - Safely parses ISO and common date formats without throwing exceptions. Corrupt date strings return `None` while `*_raw` preserves original text.

### Idempotency & Fault Tolerance
- Ingests in order: `locations.csv` &rarr; `system_a.csv` &rarr; `system_b.csv`.
- Uses `update_or_create` based on natural primary keys (`location_id`, `record_id`, `entry_id`).
- Running the importer multiple times yields identical database counts without duplication.

---

## 7. Core Reconciliation Rules (`reconcile/comparison.py`)

The pure Python comparison engine classifies entries into deterministic disagreement categories:

| Disagreement Code | Trigger Condition | Example |
|---|---|---|
| `MISSING_IN_B` | System A record has no matching System B entry (and is not `VOIDED`). | `REC-1015`, `REC-1061` |
| `ORPHAN_IN_B` | System B entry points to a record not present in System A. | `ENT/2026/4901` (`REC-1999`) |
| `DUPLICATE_IN_B` | Multiple B entries reference the same A record and do not sum to `total_value`. | `REC-1042` (`ENT/2026/4042` & `ENT/2026/4902`) |
| `VALUE_MISMATCH` | System B `value` does not match System A `total_value`, or B value is blank/unknown. | `REC-1003` (B matched base_value), `REC-1050` (blank) |
| `LOCATION_MISMATCH` | System A and System B assign different locations to the same record. | `REC-1077` (A at `LOC-102`, B at `LOC-201`) |
| `DATE_MISMATCH` | System A `event_date` does not match System B `recorded_on`. | `REC-1009` (`2026-03-31` vs `2026-04-02`) |
| `VOIDED_RECORD_IN_B` | System A record is `VOIDED`, but System B contains an active entry. | `REC-1019` (`ENT/2026/4019`) |

### Valid Split Transaction Handling
If multiple System B entries exist for an A record, and all B values are present with a Decimal sum exactly matching System A's `total_value`, the transaction is accepted as a **`VALID SPLIT`** (a non-error).
- **Example in actual data**: `REC-1055` (A `total_value` = `179,877.32`) has two System B entries: `ENT/2026/4055` (`71,950.93`) + `ENT/2026/4903` (`107,926.39`) = `179,877.32`. It is accepted as a clean match.

---

## 8. Multi-Tenant Isolation & Cross-Tenant Redaction

- **Ownership Rules**:
  - Matched records belong to the organization owning System A's location.
  - Orphan entries belong to the organization owning System B's location.
- **Backend Query Scoping**:
  - Every API request requires a tenant parameter: `GET /api/disagreements/?org=ORG-A`.
  - Database queries filter records by `location__org_id` before running reconciliation.
  - No records belonging to foreign tenants are serialized or returned over the wire.
- **Cross-Tenant Redaction**:
  - When a location mismatch spans tenants (e.g. `REC-1077`: A is `LOC-102` [`ORG-A`], B is `LOC-201` [`ORG-B`]):
    - The record is owned by `ORG-A`.
    - `ORG-A` can see the disagreement.
    - System B's foreign location is redacted: `[REDACTED - FOREIGN TENANT]`.
    - `ORG-B` cannot see this record under any circumstance.

---

## 9. REST API Documentation

### `GET /api/disagreements/`
Parameters:
- `org` (Required): Tenant identifier (`ORG-A` or `ORG-B`).
- `reason` (Optional): Filter by discrepancy reason (`MISSING_IN_B`, `VALUE_MISMATCH`, etc.).
- `sort` (Optional): Sort by field (`value`, `-value`, `record_id`, `reason`).

Example response:
```json
[
  {
    "reason": "VALUE_MISMATCH",
    "record_id": "REC-1003",
    "entry_id": "ENT/2026/4003",
    "owning_org": "ORG-B",
    "location": "LOC-202",
    "a_location": "LOC-202",
    "b_location": "LOC-202",
    "a_value": "121388.01",
    "b_value": "94834.38",
    "difference": "26553.63",
    "a_date": "2026-03-04",
    "b_date": "2026-03-04",
    "description": "Value mismatch for record REC-1003: System A total is 121388.01, System B reported 94834.38.",
    "is_cross_tenant": false,
    "details": null
  }
]
```

### `GET /api/summary/`
Parameters:
- `org` (Required): Tenant identifier (`ORG-A` or `ORG-B`).

Example response:
```json
{
  "total_disagreements": 7,
  "missing_in_b": 1,
  "orphan_in_b": 1,
  "duplicate_in_b": 1,
  "value_mismatch": 3,
  "location_mismatch": 1,
  "date_mismatch": 0,
  "voided_record_in_b": 0
}
```

### `GET /api/organizations/`
Returns:
```json
{
  "organizations": ["ORG-A", "ORG-B"]
}
```

---

## 10. Setup & Execution Commands

### Clean Clone Setup

```bash
# 1. Create and activate virtual environment
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 2. Install backend dependencies
pip install -r requirements.txt

# 3. Run database migrations
cd backend
python manage.py migrate

# 4. Ingest CSV data into SQLite
python manage.py import_data

# 5. Run test suite
pytest -v

# 6. Start Django backend server (runs on http://127.0.0.1:8000)
python manage.py runserver 8000
```

### Frontend Setup

```bash
# In a separate terminal:
cd frontend
npm install
npm run dev
# Dashboard opens on http://localhost:5173
```

---

## 11. Automated Test Suite

Run all tests with Pytest:
```bash
cd backend
pytest -v
```

The test suite covers 34 automated unit and integration tests across:
- **Normalization**: Standard amount parsing, Indian numbering formatting (`1,25,400.00`), blank/invalid amounts returning `None`, reference cleanup (`rec1034`, ` REC - 1070 `, `1112`), safe date parsing.
- **Comparison Engine**: Missing detection, orphan detection, duplicate detection, valid split acceptance, value mismatch, blank value handling, cross-tenant location mismatch, date mismatch, VOIDED record policy.
- **Importer Resilience**: Preservation of all 120 A rows, 121 B rows, and 5 locations; idempotency; non-crashing dirty rows; unknown location handling.
- **Tenant Isolation**: ORG-A vs ORG-B data segregation, cross-tenant location redaction, orphan ownership resolution.
- **REST API**: Mandatory parameter validation, invalid reason/sort rejection, serializer accuracy.

---

## 12. Actual Data Reconciliation Summary

Reconciliation executed against the supplied CSV datasets:

| Metric | Total | ORG-A | ORG-B | Notes |
|---|---:|---:|---:|---|
| **Locations** | 5 | 3 | 2 | LOC-101, 102, 103 (ORG-A); LOC-201, 202 (ORG-B) |
| **System A Rows** | 120 | 72 | 48 | All rows preserved |
| **System B Entries** | 121 | 74 | 47 | All entries preserved |
| **Total Disagreements** | **12** | **7** | **5** | Zero foreign-tenant leakage |
| &bull; `MISSING_IN_B` | 2 | 1 | 1 | REC-1015 (ORG-A), REC-1061 (ORG-B) |
| &bull; `ORPHAN_IN_B` | 1 | 1 | 0 | REC-1999 (ENT/2026/4901 at LOC-102) |
| &bull; `DUPLICATE_IN_B` | 1 | 1 | 0 | REC-1042 (identical duplicate ENT/2026/4902) |
| &bull; `VALUE_MISMATCH` | 5 | 3 | 2 | REC-1027, 1064, 1088 (ORG-A); REC-1003, 1050 (ORG-B) |
| &bull; `LOCATION_MISMATCH` | 1 | 1 | 0 | REC-1077 (A: LOC-102, B: LOC-201; Redacted in ORG-A) |
| &bull; `DATE_MISMATCH` | 1 | 0 | 1 | REC-1009 (A: 2026-03-31, B: 2026-04-02) |
| &bull; `VOIDED_RECORD_IN_B` | 1 | 0 | 1 | REC-1019 (A: VOIDED, B: ENT/2026/4019 active) |
| **Valid Splits** | 1 | 1 | 0 | REC-1055 (Sum matches exactly; non-error) |
| **Clean Matching Records**| 108 | 66 | 42 | In full financial agreement |

---

## 13. Known Limitations & Deliberately Unimplemented Features

1. **Authentication & Session Login**: Deliberately omitted per assessment brief. Tenant scoping is passed via explicit `?org=` query parameter to maintain transparent testability.
2. **Containerization (Docker)**: Excluded in favor of direct local execution (`requirements.txt` + `npm install`), preventing container overhead on lightweight SQLite files.
3. **Heavy CSS Component Libraries**: Built using clean custom CSS to maintain focus on data integrity, state handling, and layout clarity.

---

## 14. How I Worked With the AI Agent

### Development Collaboration
I worked on this project step by step with the help of an AI agent. I didn't just ask it to generate the entire application at once. I first understood the data and then worked on each part separately.
1. Understanding the data: Before starting the implementation, I checked the CSV files using Python to understand what kind of data they contained and what problems needed to be handled. I found issues like different number formats, inconsistent references, blank values, duplicate entries and split transactions.
2. Building the logic separately: I worked on the comparison logic in reconcile/comparison.py separately from the Django API. This made it easier to understand the business rules and test them without depending on the frontend or API.
3. Testing along the way: After implementing each major part, I ran the tests and checked the results. I paid particular attention to financial calculations and used Decimal values to avoid floating-point accuracy issues.

### Assessment Questions

#### A. Name one thing the AI agent got wrong. How did you notice?
One thing I noticed was that the AI agent sometimes made assumptions about the data without checking the actual requirements. For example, while working on reference normalization, it suggested treating an invalid reference like "recdirty" as "REC-DIRTY". But when I ran the tests, I noticed that the result was None. I checked the logic and understood that a reference without identifiable digits should not be treated as a valid reference. So I corrected the test instead of changing the implementation just to make it pass.

#### B. Which part of your submission are you least confident about, and why?
I am not completely confident about sorting when a record has multiple entries in System B. For example, when split transactions have different dates or locations, sorting the combined record may not give users enough detail about the individual entries. The current implementation handles the overall disagreement, but I think there is room to improve how these cases are displayed.

#### C. If you had a second day, what would you fix first?
I would first add an option to export the disagreement records into CSV or Excel files. This would help users analyze the results outside the application. After that, I would work on a review feature where users can mark disagreements as reviewed or known exceptions and track which issues have been resolved.
