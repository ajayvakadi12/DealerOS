import React from 'react';

export default function LoadingState() {
  return (
    <div className="state-container loading-container">
      <div className="spinner"></div>
      <p>Reconciling tenant records from database...</p>
    </div>
  );
}
