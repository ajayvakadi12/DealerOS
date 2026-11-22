import React, { useState, useEffect, useCallback } from 'react';
import DashboardHeader from './components/DashboardHeader';
import SummaryCards from './components/SummaryCards';
import FilterBar from './components/FilterBar';
import DisagreementTable from './components/DisagreementTable';
import LoadingState from './components/LoadingState';
import EmptyState from './components/EmptyState';
import { fetchDisagreements, fetchSummary, fetchOrganizations } from './services/api';

export default function App() {
  const [organizations, setOrganizations] = useState(['ORG-A', 'ORG-B']);
  const [selectedOrg, setSelectedOrg] = useState('ORG-A');
  const [selectedReason, setSelectedReason] = useState('ALL');
  const [selectedSort, setSelectedSort] = useState('');
  
  const [disagreements, setDisagreements] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch initial organizations list
  useEffect(() => {
    fetchOrganizations()
      .then((orgs) => {
        if (orgs && orgs.length > 0) {
          setOrganizations(orgs);
          if (!orgs.includes(selectedOrg)) {
            setSelectedOrg(orgs[0]);
          }
        }
      })
      .catch((err) => {
        console.warn('Using default organizations:', err);
      });
  }, []);

  // Fetch summary metrics for current organization
  const loadSummary = useCallback(async (org) => {
    try {
      const data = await fetchSummary(org);
      setSummary(data);
    } catch (err) {
      console.error('Failed to load summary metrics:', err);
    }
  }, []);

  // Fetch disagreements from backend
  const loadDisagreements = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchDisagreements(selectedOrg, selectedReason, selectedSort);
      setDisagreements(data);
      await loadSummary(selectedOrg);
    } catch (err) {
      console.error('Failed to load disagreements:', err);
      setError(
        err.response?.data?.error || 'Unable to connect to DealerOS backend reconciliation API.'
      );
    } finally {
      setLoading(false);
    }
  }, [selectedOrg, selectedReason, selectedSort, loadSummary]);

  useEffect(() => {
    loadDisagreements();
  }, [loadDisagreements]);

  const handleOrgChange = (newOrg) => {
    setSelectedOrg(newOrg);
    setSelectedReason('ALL');
    setSelectedSort('');
  };

  return (
    <div className="app-container">
      <DashboardHeader currentOrg={selectedOrg} />
      
      <main className="main-content">
        <SummaryCards summary={summary} />

        <div className="content-card">
          <FilterBar
            organizations={organizations}
            selectedOrg={selectedOrg}
            onSelectOrg={handleOrgChange}
            selectedReason={selectedReason}
            onSelectReason={setSelectedReason}
            selectedSort={selectedSort}
            onSelectSort={setSelectedSort}
            itemCount={disagreements.length}
          />

          {loading ? (
            <LoadingState />
          ) : error ? (
            <div className="state-container error-container">
              <div className="error-icon">⚠</div>
              <h3>Backend API Error</h3>
              <p>{error}</p>
              <button className="btn-retry" onClick={loadDisagreements}>
                Retry Request
              </button>
            </div>
          ) : disagreements.length === 0 ? (
            <EmptyState
              message={
                selectedReason !== 'ALL'
                  ? `No records found for reason '${selectedReason}' in tenant ${selectedOrg}.`
                  : `No reconciliation discrepancies found for tenant ${selectedOrg}.`
              }
            />
          ) : (
            <DisagreementTable items={disagreements} />
          )}
        </div>
      </main>

      <footer className="dashboard-footer">
        DealerOS Reconciliation Engine &bull; Multi-Tenant Data Scoping Enabled &bull; SQLite Single Source of Truth
      </footer>
    </div>
  );
}
