# Source Data Anomalies & Inspection Report

## Overview
Inspection of `locations.csv`, `system_a.csv`, and `system_b.csv` reveals the exact composition of the source datasets and deliberate real-world anomalies.

## Baseline Row Counts
- `locations.csv`: 5 rows (Headers: `location_id`, `org_id`, `location_name`)
  - LOC-101, LOC-102, LOC-103 -> ORG-A
  - LOC-201, LOC-202 -> ORG-B
- `system_a.csv`: 120 rows (Headers: `record_id`, `location_id`, `event_date`, `category_code`, `actor_id`, `base_value`, `adjustment`, `total_value`, `state`)
- `system_b.csv`: 121 rows (Headers: `entry_id`, `record_ref`, `location_id`, `recorded_on`, `value`, `label`)

## Identified Anomalies

### 1. Missing Records in System B
- `REC-1015`: Exists in System A (LOC-103, CONFIRMED, 41095.33), completely absent in System B.
- `REC-1061`: Exists in System A (LOC-202, CONFIRMED, 87615.49), completely absent in System B.

### 2. Orphan Records in System B
- `ENT/2026/4901`: Has `record_ref` = `REC-1999`, location `LOC-102` (ORG-A). Does not exist in System A.

### 3. Inconsistent Reference Formatting in System B
- `ENT/2026/4034`: `rec1034` (lowercase without hyphen).
- `ENT/2026/4070`: ` REC - 1070 ` (irregular whitespace).
- `ENT/2026/4112`: `1112` (pure numeric digits without prefix).

### 4. Monetary Value Formatting Anomalies
- `ENT/2026/4050`: `value` is blank (`""`). Must be treated as unknown (`None`), never zero.
- `ENT/2026/4064`: `value` is `"1,25,400.00"` (Indian numbering format with non-standard commas).

### 5. Multi-Entry References in System B
- **Duplicates**:
  - `REC-1042`: Referenced by `ENT/2026/4042` ($112,837.06) and `ENT/2026/4902` ($112,837.06). System A total is $112,837.06. Classified as `DUPLICATE_IN_B`.
- **Valid Splits**:
  - `REC-1055`: Referenced by `ENT/2026/4055` ($71,950.93) and `ENT/2026/4903` ($107,926.39). Sum = $179,877.32. System A total is $179,877.32. Classified as a valid split (non-error).

### 6. State / Lifecycle Anomalies
- `REC-1019`: Marked as `state` = `VOIDED` in System A, but System B contains an active entry `ENT/2026/4019`. Classified as `VOIDED_RECORD_IN_B`.

### 7. Cross-Tenant Location Mismatches
- `REC-1077`: System A assigns to `LOC-102` (ORG-A), but System B assigns to `LOC-201` (ORG-B). Belongs to ORG-A; foreign location details must be redacted.

### 8. Nullable Fields in System A
- `REC-1050`: `actor_id` is empty string.
