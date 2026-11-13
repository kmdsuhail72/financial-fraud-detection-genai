import React, { useState, useEffect, useCallback } from 'react';
import { Sidebar } from './components/Sidebar';
import { Navbar } from './components/Navbar';
import { DashboardPage } from './pages/DashboardPage';
import { QueuePage } from './pages/QueuePage';
import { CaseDetailPage } from './pages/CaseDetailPage';
import { SettingsPage } from './pages/SettingsPage';
import { ThreatIntelPage } from './pages/ThreatIntelPage';
import { UebaDashboardPage } from './pages/UebaDashboardPage';
import { GraphInvestigationPage } from './pages/GraphInvestigationPage';
import { NetworkAnalyticsPage } from './pages/NetworkAnalyticsPage';
import { GNNFraudDetectionPage } from './pages/GNNFraudDetectionPage';
import { TemporalFraudMonitorPage } from './pages/TemporalFraudMonitorPage';
import { FraudDecisionEnginePage } from './pages/FraudDecisionEnginePage';
import { OperationsQueuePage } from './pages/OperationsQueuePage';
import { EvidenceWorkspacePage } from './pages/EvidenceWorkspacePage';
import { ComplianceGovernancePage } from './pages/ComplianceGovernancePage';
import { AMLInvestigationPage } from './pages/AMLInvestigationPage';
import { KYCOnboardingPage } from './pages/KYCOnboardingPage';
import { DocumentVerificationPage } from './pages/DocumentVerificationPage';
import { InvestigationCase, DashboardMetrics, CaseStatus } from './types/case';
import { casesApi } from './services/api';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<string>('dashboard');
  const [sidebarCollapsed, setSidebarCollapsed] = useState<boolean>(false);
  const [isDemoMode, setIsDemoMode] = useState<boolean>(casesApi.isDemoMode());
  const [apiBaseUrl, setApiBaseUrl] = useState<string>(casesApi.getBaseUrl());
  const [backendHealthy, setBackendHealthy] = useState<boolean | null>(null);

  const [cases, setCases] = useState<InvestigationCase[]>([]);
  const [metrics, setMetrics] = useState<DashboardMetrics>({
    total_cases: 0,
    critical_cases: 0,
    high_risk_cases: 0,
    in_review_cases: 0,
    resolved_today: 0,
    avg_resolution_time_minutes: 0
  });

  const [activeCaseId, setActiveCaseId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Load cases
  const loadData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await casesApi.listCases();
      setCases(data);
      const computedMetrics = await casesApi.getMetrics(data);
      setMetrics(computedMetrics);

      // Check backend health quietly
      const healthy = await casesApi.healthCheck();
      setBackendHealthy(healthy);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch cases');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData, isDemoMode]);

  const handleToggleDemoMode = () => {
    const nextMode = !isDemoMode;
    casesApi.setDemoMode(nextMode);
    setIsDemoMode(nextMode);
    loadData();
  };

  const handleUpdateApiBaseUrl = (url: string) => {
    casesApi.setBaseUrl(url);
    setApiBaseUrl(url);
    loadData();
  };

  const handleSelectCase = (caseId: string) => {
    setActiveCaseId(caseId);
    setCurrentTab('detail');
  };

  const handleBackToQueue = () => {
    setCurrentTab('queue');
  };

  const handleUpdateStatus = async (caseId: string, newStatus: CaseStatus) => {
    const updated = await casesApi.updateCaseStatus(caseId, newStatus);
    setCases((prev) => prev.map((c) => (c.case_id === caseId ? updated : c)));
    const updatedMetrics = await casesApi.getMetrics(
      cases.map((c) => (c.case_id === caseId ? updated : c))
    );
    setMetrics(updatedMetrics);
  };

  const handleAddNote = async (caseId: string, noteText: string) => {
    const updated = await casesApi.addNote(caseId, noteText);
    setCases((prev) => prev.map((c) => (c.case_id === caseId ? updated : c)));
  };

  const activeCase = cases.find((c) => c.case_id === activeCaseId) || cases[0];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex">
      {/* Left Sidebar */}
      <Sidebar
        currentTab={currentTab}
        onSelectTab={(tab) => setCurrentTab(tab)}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        activeCaseId={activeCaseId}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <Navbar
          currentTab={currentTab}
          isDemoMode={isDemoMode}
          onToggleDemoMode={handleToggleDemoMode}
          onRefresh={loadData}
          isLoading={isLoading}
          backendHealthy={backendHealthy}
          onSearch={(query) => {
            setCurrentTab('queue');
          }}
        />

        {error && (
          <div className="bg-rose-950/50 border-b border-rose-900 px-6 py-2 text-xs text-rose-300 font-mono flex items-center justify-between">
            <span>API Communication Error: {error}</span>
            <button
              onClick={() => handleToggleDemoMode()}
              className="underline text-sky-400 hover:text-sky-300 font-sans"
            >
              Switch to Offline Demo Mode
            </button>
          </div>
        )}

        <main className="flex-1 p-6 overflow-y-auto">
          {currentTab === 'dashboard' && (
            <DashboardPage
              cases={cases}
              metrics={metrics}
              onSelectCase={handleSelectCase}
              onViewAllQueue={() => setCurrentTab('queue')}
            />
          )}

          {currentTab === 'queue' && (
            <QueuePage
              cases={cases}
              onSelectCase={handleSelectCase}
              isLoading={isLoading}
              onRefresh={loadData}
            />
          )}

          {currentTab === 'detail' && activeCase && (
            <CaseDetailPage
              caseData={activeCase}
              onBack={handleBackToQueue}
              onUpdateStatus={handleUpdateStatus}
              onAddNote={handleAddNote}
            />
          )}

          {currentTab === 'threat-intel' && (
            <ThreatIntelPage />
          )}

          {currentTab === 'ueba' && (
            <UebaDashboardPage />
          )}

          {currentTab === 'graph' && (
            <GraphInvestigationPage />
          )}

          {currentTab === 'network-analytics' && (
            <NetworkAnalyticsPage />
          )}

          {currentTab === 'gnn-fraud' && (
            <GNNFraudDetectionPage />
          )}

          {currentTab === 'temporal-monitor' && (
            <TemporalFraudMonitorPage />
          )}

          {currentTab === 'decision-engine' && (
            <FraudDecisionEnginePage />
          )}

          {currentTab === 'operations-queue' && (
            <OperationsQueuePage />
          )}

          {currentTab === 'evidence-forensics' && (
            <EvidenceWorkspacePage />
          )}

          {currentTab === 'compliance-governance' && (
            <ComplianceGovernancePage />
          )}

          {currentTab === 'aml-monitoring' && (
            <AMLInvestigationPage />
          )}

          {currentTab === 'kyc-onboarding' && (
            <KYCOnboardingPage />
          )}

          {currentTab === 'document-verification' && (
            <DocumentVerificationPage />
          )}

          {currentTab === 'settings' && (
            <SettingsPage
              isDemoMode={isDemoMode}
              onToggleDemoMode={handleToggleDemoMode}
              apiBaseUrl={apiBaseUrl}
              onUpdateApiBaseUrl={handleUpdateApiBaseUrl}
              onTestBackend={() => casesApi.healthCheck()}
            />
          )}
        </main>
      </div>
    </div>
  );
};

export default App;
