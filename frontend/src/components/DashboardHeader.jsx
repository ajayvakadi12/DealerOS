import React from 'react';

export default function DashboardHeader({ currentOrg }) {
  return (
    <header className="dashboard-header">
      <div className="header-brand">
        <div className="brand-logo">DealerOS</div>
        <div className="tenant-badge">Tenant: {currentOrg}</div>
      </div>
      <div className="header-titles">
        <h1>Data Reconciliation</h1>
        <p className="subtitle">
          Multi-tenant disagreement detection engine reconciling transactional event records between System A and System B with strict boundary isolation.
        </p>
      </div>
    </header>
  );
}
