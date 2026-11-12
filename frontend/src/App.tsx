import React, { useState, useEffect } from 'react';

interface MetricSummary {
  total_transactions_today: number;
  flagged_alerts: number;
  open_investigations: number;
  critical_cases: number;
  false_positive_rate: number;
}

export const App: React.FC = () => {
  const [metrics, setMetrics] = useState<MetricSummary>({
    total_transactions_today: 142580,
    flagged_alerts: 34,
    open_investigations: 12,
    critical_cases: 3,
    false_positive_rate: 0.38
  });

  return (
    <div style={{ fontFamily: 'system-ui, sans-serif', padding: '2rem', backgroundColor: '#0f172a', minHeight: '100vh', color: '#f8fafc' }}>
      <header style={{ borderBottom: '1px solid #334155', paddingBottom: '1rem', marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '1.875rem', fontWeight: 'bold', color: '#38bdf8', margin: 0 }}>
          FinGuard AI — Fraud Detection & GenAI Investigation Console
        </h1>
        <p style={{ color: '#94a3b8', marginTop: '0.25rem' }}>
          Real-Time Streaming Transaction Triage & Grounded Bedrock Copilot
        </p>
      </header>

      <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1.5rem', marginBottom: '2.5rem' }}>
        <div style={{ backgroundColor: '#1e293b', padding: '1.25rem', borderRadius: '0.5rem', border: '1px solid #334155' }}>
          <div style={{ fontSize: '0.875rem', color: '#94a3b8' }}>Processed Today</div>
          <div style={{ fontSize: '1.75rem', fontWeight: 'bold', color: '#f8fafc' }}>{metrics.total_transactions_today.toLocaleString()}</div>
        </div>
        <div style={{ backgroundColor: '#1e293b', padding: '1.25rem', borderRadius: '0.5rem', border: '1px solid #334155' }}>
          <div style={{ fontSize: '0.875rem', color: '#fbbf24' }}>Active Alerts</div>
          <div style={{ fontSize: '1.75rem', fontWeight: 'bold', color: '#fbbf24' }}>{metrics.flagged_alerts}</div>
        </div>
        <div style={{ backgroundColor: '#1e293b', padding: '1.25rem', borderRadius: '0.5rem', border: '1px solid #334155' }}>
          <div style={{ fontSize: '0.875rem', color: '#f87171' }}>Critical Cases</div>
          <div style={{ fontSize: '1.75rem', fontWeight: 'bold', color: '#f87171' }}>{metrics.critical_cases}</div>
        </div>
        <div style={{ backgroundColor: '#1e293b', padding: '1.25rem', borderRadius: '0.5rem', border: '1px solid #334155' }}>
          <div style={{ fontSize: '0.875rem', color: '#34d399' }}>False Positive Rate</div>
          <div style={{ fontSize: '1.75rem', fontWeight: 'bold', color: '#34d399' }}>{(metrics.false_positive_rate * 100).toFixed(1)}%</div>
        </div>
      </section>

      <main style={{ backgroundColor: '#1e293b', padding: '1.5rem', borderRadius: '0.5rem', border: '1px solid #334155' }}>
        <h2 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '1rem' }}>Investigation Workbench Status</h2>
        <p style={{ color: '#cbd5e1' }}>
          Phase 1 Architecture & Foundations configured. Backend API is ready to accept simulated transaction streams and SageMaker inference scoring.
        </p>
      </main>
    </div>
  );
};

export default App;
