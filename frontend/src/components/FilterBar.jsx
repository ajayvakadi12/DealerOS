import React from 'react';

export default function FilterBar({
  organizations,
  selectedOrg,
  onSelectOrg,
  selectedReason,
  onSelectReason,
  selectedSort,
  onSelectSort,
  itemCount,
}) {
  const reasons = [
    { value: 'ALL', label: 'All Disagreement Types' },
    { value: 'MISSING_IN_B', label: 'MISSING_IN_B (Absent in B)' },
    { value: 'ORPHAN_IN_B', label: 'ORPHAN_IN_B (No A Record)' },
    { value: 'DUPLICATE_IN_B', label: 'DUPLICATE_IN_B (Duplicate Entries)' },
    { value: 'VALUE_MISMATCH', label: 'VALUE_MISMATCH (Amount Discrepancy)' },
    { value: 'LOCATION_MISMATCH', label: 'LOCATION_MISMATCH (Cross/Wrong Location)' },
    { value: 'DATE_MISMATCH', label: 'DATE_MISMATCH (Date Discrepancy)' },
  ];

  const sortOptions = [
    { value: '', label: 'Default Order' },
    { value: '-value', label: 'Difference: High to Low' },
    { value: 'value', label: 'Difference: Low to High' },
    { value: 'record_id', label: 'Record ID (Asc)' },
  ];

  return (
    <div className="filter-bar">
      <div className="filter-group">
        <label htmlFor="org-select">Organization (Tenant):</label>
        <select
          id="org-select"
          className="select-input select-org"
          value={selectedOrg}
          onChange={(e) => onSelectOrg(e.target.value)}
        >
          {organizations.map((org) => (
            <option key={org} value={org}>
              {org}
            </option>
          ))}
        </select>
      </div>

      <div className="filter-group">
        <label htmlFor="reason-select">Filter by Reason:</label>
        <select
          id="reason-select"
          className="select-input"
          value={selectedReason}
          onChange={(e) => onSelectReason(e.target.value)}
        >
          {reasons.map((r) => (
            <option key={r.value} value={r.value}>
              {r.label}
            </option>
          ))}
        </select>
      </div>

      <div className="filter-group">
        <label htmlFor="sort-select">Sort by:</label>
        <select
          id="sort-select"
          className="select-input"
          value={selectedSort}
          onChange={(e) => onSelectSort(e.target.value)}
        >
          {sortOptions.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
      </div>

      <div className="filter-count">
        Showing <strong>{itemCount}</strong> records
      </div>
    </div>
  );
}
