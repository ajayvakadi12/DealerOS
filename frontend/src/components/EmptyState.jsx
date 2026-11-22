import React from 'react';

export default function EmptyState({ message }) {
  return (
    <div className="state-container empty-container">
      <div className="empty-icon">✓</div>
      <h3>No Disagreements Found</h3>
      <p>{message || "All records for this filter criteria are in clean reconciliation agreement."}</p>
    </div>
  );
}
