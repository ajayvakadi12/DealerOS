import React from 'react';
import TableRow from './TableRow';

export default function DisagreementTable({ items }) {
  return (
    <div className="table-responsive">
      <table className="disagreement-table">
        <thead>
          <tr>
            <th>Reason</th>
            <th>Record / Entry ID</th>
            <th>Location</th>
            <th className="th-right">System A Value</th>
            <th className="th-right">System B Value</th>
            <th className="th-right">Difference</th>
            <th>Date Info</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, idx) => (
            <TableRow key={`${item.reason}-${item.record_id || item.entry_id}-${idx}`} item={item} />
          ))}
        </tbody>
      </table>
    </div>
  );
}
