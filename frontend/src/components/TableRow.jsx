import React from 'react';

const formatCurrency = (val) => {
  if (val === null || val === undefined || val === '') return '—';
  const num = Number(val);
  if (isNaN(num)) return val;
  return '$' + num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

const formatDifference = (item) => {
  // Non-monetary disagreements (Location, Date, Voided with equal values) display a dash instead of $0.00
  const isNonMonetary = ['LOCATION_MISMATCH', 'DATE_MISMATCH', 'VOIDED_RECORD_IN_B'].includes(item.reason);
  if (isNonMonetary && (!item.difference || Number(item.difference) === 0)) {
    return '—';
  }
  if (item.difference === null || item.difference === undefined || item.difference === '') {
    return '—';
  }
  if (Number(item.difference) === 0 && item.reason !== 'VALUE_MISMATCH' && item.reason !== 'DUPLICATE_IN_B') {
    return '—';
  }
  return formatCurrency(item.difference);
};

const getReasonBadgeClass = (reason) => {
  switch (reason) {
    case 'MISSING_IN_B':
      return 'badge-missing';
    case 'ORPHAN_IN_B':
      return 'badge-orphan';
    case 'DUPLICATE_IN_B':
      return 'badge-duplicate';
    case 'VALUE_MISMATCH':
      return 'badge-value';
    case 'LOCATION_MISMATCH':
      return 'badge-location';
    case 'DATE_MISMATCH':
      return 'badge-date';
    case 'VOIDED_RECORD_IN_B':
      return 'badge-voided';
    default:
      return 'badge-default';
  }
};

export default function TableRow({ item }) {
  const isRedacted = item.b_location && item.b_location.includes('REDACTED');
  const hasSplitDetails = item.details && item.details.entries;

  return (
    <tr className="table-row">
      <td className="cell-reason">
        <span className={`reason-badge ${getReasonBadgeClass(item.reason)}`}>
          {item.reason}
        </span>
      </td>
      <td className="cell-record-id">
        <strong>{item.record_id || '—'}</strong>
        {item.entry_id && (
          <div className="entry-subtext">Entry: {item.entry_id}</div>
        )}
      </td>
      <td className="cell-location">
        {isRedacted ? (
          <div>
            <span>{item.a_location}</span>
            <span className="redacted-tag">System B: [REDACTED]</span>
          </div>
        ) : (
          item.location || '—'
        )}
      </td>
      <td className="cell-amount cell-amount-a">
        {formatCurrency(item.a_value)}
      </td>
      <td className="cell-amount cell-amount-b">
        {formatCurrency(item.b_value)}
        {hasSplitDetails && (
          <div className="split-entries-container">
            {item.details.entries.map((e, idx) => (
              <div key={idx} className="split-pill">
                {e.entry_id}: {formatCurrency(e.value)}
              </div>
            ))}
          </div>
        )}
      </td>
      <td className="cell-amount cell-diff">
        {formatDifference(item)}
      </td>
      <td className="cell-date">
        {item.a_date || item.b_date ? (
          <div className="date-display">
            {item.a_date && <div>A: {item.a_date}</div>}
            {item.b_date && <div>B: {item.b_date}</div>}
          </div>
        ) : (
          '—'
        )}
      </td>
    </tr>
  );
}
