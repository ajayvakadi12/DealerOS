import React from 'react';

export default function SummaryCards({ summary }) {
  const cards = [
    {
      title: 'Total Disagreements',
      value: summary?.total_disagreements ?? 0,
      className: 'card-total',
      description: 'Discrepancies flagged'
    },
    {
      title: 'Missing in B',
      value: summary?.missing_in_b ?? 0,
      className: 'card-missing',
      description: 'Records absent in System B'
    },
    {
      title: 'Orphan in B',
      value: summary?.orphan_in_b ?? 0,
      className: 'card-orphan',
      description: 'System B entries with no A record'
    },
    {
      title: 'Duplicate in B',
      value: summary?.duplicate_in_b ?? 0,
      className: 'card-duplicate',
      description: 'Non-split multiple entries'
    },
    {
      title: 'Value Mismatches',
      value: summary?.value_mismatch ?? 0,
      className: 'card-value',
      description: 'Amounts do not match total_value'
    },
  ];

  return (
    <div className="summary-cards-grid">
      {cards.map((card, idx) => (
        <div key={idx} className={`summary-card ${card.className}`}>
          <div className="card-label">{card.title}</div>
          <div className="card-value-display">{card.value}</div>
          <div className="card-desc">{card.description}</div>
        </div>
      ))}
    </div>
  );
}
