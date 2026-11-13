import React, { useState, useEffect } from 'react';
import {
  FileWarning,
  ShieldAlert,
  AlertTriangle,
  User,
  Users,
  Search,
  RefreshCw,
  TrendingDown,
  TrendingUp,
  FileText,
  DollarSign,
  Activity,
  Send,
  CheckCircle2,
  AlertCircle,
  Copy,
  ChevronRight,
  Layers,
  Clock,
  Zap
} from 'lucide-react';

interface AMLAlert {
  alert_id: string;
  rule_type: string;
  severity: string;
  description: string;
  trigger_amount: number;
  trigger_transaction_ids: string[];
  detected_at: string;
}

interface CustomerRiskProfile {
  customer_id: string;
  name: string;
  risk_tier: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  risk_score: number;
  account_type: string;
  country: string;
  pep_flag: boolean;
  risk_factors: string[];
  total_transaction_volume: number;
  lifetime_aml_alerts_count: number;
}

interface CaseNote {
  note_id: string;
  author: string;
  created_at: string;
  content: string;
}

interface CaseActivity {
  activity_id: string;
  timestamp: string;
  actor: string;
  action: string;
  details: Record<string, any>;
}

interface AMLCase {
  case_id: string;
  customer_id: string;
  status: 'NEW' | 'UNDER_INVESTIGATION' | 'ESCALATED' | 'CLOSED_NO_ACTION' | 'REPORT_PREPARED';
  alerts: AMLAlert[];
  risk_score: number;
  risk_tier: string;
  assigned_to?: string;
  notes: CaseNote[];
  created_at: string;
  updated_at: string;
  history: CaseActivity[];
}

interface AMLMetrics {
  total_monitored_transactions: number;
  total_alerts_detected: number;
  active_investigation_cases: number;
  customer_risk_distribution: Record<string, number>;
  alerts_by_rule_type: Record<string, number>;
  avg_case_resolution_time_hours: number;
}

interface SARDraft {
  draft_id: string;
  case_id: string;
  customer_id: string;
  prepared_by: string;
  suspicious_activity_summary: string;
  violating_patterns: string[];
  total_suspicious_amount: number;
  evidence_citations: string[];
  recommended_disposition: string;
  report_markdown: string;
}

export const AMLInvestigationPage: React.FC = () => {
  const [metrics, setMetrics] = useState<AMLMetrics | null>(null);
  const [cases, setCases] = useState<AMLCase[]>([]);
  const [selectedCase, setSelectedCase] = useState<AMLCase | null>(null);
  const [selectedProfile, setSelectedProfile] = useState<CustomerRiskProfile | null>(null);
  const [sarDraft, setSarDraft] = useState<SARDraft | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  // Filters & State
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Simulator State
  const [simCustomerId, setSimCustomerId] = useState<string>('CUST-AML-001');
  const [simAmount, setSimAmount] = useState<number>(9500.0);
  const [simDirection, setSimDirection] = useState<'INFLOW' | 'OUTFLOW'>('OUTFLOW');
  const [simMethod, setSimMethod] = useState<string>('CASH_DEPOSIT');
  const [simResult, setSimResult] = useState<string | null>(null);

  // Note State
  const [newNote, setNewNote] = useState<string>('');

  const fetchAMLData = async () => {
    setLoading(true);
    try {
      const [mRes, cRes] = await Promise.all([
        fetch('http://127.0.0.1:8010/aml/metrics'),
        fetch('http://127.0.0.1:8010/aml/cases')
      ]);

      if (mRes.ok) setMetrics(await mRes.json());
      if (cRes.ok) {
        const cData = await cRes.json();
        setCases(cData);
        if (cData.length > 0 && !selectedCase) {
          handleSelectCase(cData[0]);
        }
      }
    } catch {
      console.warn('Backend unavailable, using initial demo state');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAMLData();
  }, []);

  const handleSelectCase = async (caseObj: AMLCase) => {
    setSelectedCase(caseObj);
    setSarDraft(null);
    try {
      const profRes = await fetch(`http://127.0.0.1:8010/aml/customers/${caseObj.customer_id}`);
      if (profRes.ok) setSelectedProfile(await profRes.json());
    } catch (e) {
      console.error(e);
    }
  };

  const handleSimulateTransaction = async () => {
    try {
      const payload = {
        transaction_id: `TXN-${Date.now().toString().slice(-6)}`,
        customer_id: simCustomerId,
        amount: simAmount,
        direction: simDirection,
        payment_method: simMethod,
        currency: 'USD'
      };
      const res = await fetch('http://127.0.0.1:8010/aml/monitor/transaction', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        const data = await res.json();
        setSimResult(
          data.alerts_triggered.length > 0
            ? `⚠️ Flagged ${data.alerts_triggered.length} AML Alert(s)! Risk Tier: ${data.customer_risk_tier}`
            : `✅ Clean: No suspicious AML patterns detected.`
        );
        fetchAMLData();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleStatusChange = async (caseId: string, newStatus: string) => {
    try {
      const res = await fetch(`http://127.0.0.1:8010/aml/cases/${caseId}/status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus, notes: `Status updated to ${newStatus}` })
      });
      if (res.ok) {
        const updated = await res.json();
        setSelectedCase(updated);
        fetchAMLData();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleAddNote = async (caseId: string) => {
    if (!newNote.trim()) return;
    try {
      const res = await fetch(`http://127.0.0.1:8010/aml/cases/${caseId}/notes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ author: 'aml.investigator@finguard.internal', content: newNote })
      });
      if (res.ok) {
        const updated = await res.json();
        setSelectedCase(updated);
        setNewNote('');
        fetchAMLData();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleGenerateSAR = async (caseId: string) => {
    try {
      const res = await fetch(`http://127.0.0.1:8010/aml/cases/${caseId}/sar-draft`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prepared_by: 'senior.aml.officer@finguard.internal',
          recommended_disposition: 'RECOMMEND_SAR_FILING'
        })
      });
      if (res.ok) {
        const draft = await res.json();
        setSarDraft(draft);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const getRiskTierBadge = (tier: string) => {
    switch (tier) {
      case 'CRITICAL':
        return 'bg-rose-500/20 text-rose-400 border border-rose-500/40 font-bold';
      case 'HIGH':
        return 'bg-orange-500/20 text-orange-400 border border-orange-500/40';
      case 'MEDIUM':
        return 'bg-amber-500/20 text-amber-400 border border-amber-500/40';
      default:
        return 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40';
    }
  };

  const getStatusBadge = (st: string) => {
    switch (st) {
      case 'NEW':
        return 'bg-sky-500/20 text-sky-400 border border-sky-500/40';
      case 'UNDER_INVESTIGATION':
        return 'bg-amber-500/20 text-amber-400 border border-amber-500/40';
      case 'ESCALATED':
        return 'bg-rose-500/20 text-rose-400 border border-rose-500/40';
      case 'REPORT_PREPARED':
        return 'bg-purple-500/20 text-purple-400 border border-purple-500/40';
      default:
        return 'bg-slate-500/20 text-slate-400 border border-slate-500/40';
    }
  };

  const filteredCases = cases.filter((c) => {
    if (statusFilter !== 'ALL' && c.status !== statusFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return c.case_id.toLowerCase().includes(q) || c.customer_id.toLowerCase().includes(q);
    }
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-slate-100">
              AML Transaction Monitoring & Risk Profiling
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-mono bg-amber-500/10 text-amber-400 border border-amber-500/30">
              Phase 24
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Explainable AML rules monitoring, structuring / smurfing detection, customer risk scoring, and SAR investigation drafts.
          </p>
        </div>
        <button
          onClick={fetchAMLData}
          className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg border border-slate-700 transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Metrics Bar */}
      {metrics && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl">
            <span className="text-xs text-slate-400 block">Monitored Txns</span>
            <p className="text-xl font-bold text-slate-100">{metrics.total_monitored_transactions}</p>
          </div>
          <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl">
            <span className="text-xs text-amber-400 block">AML Alerts Flagged</span>
            <p className="text-xl font-bold text-amber-300">{metrics.total_alerts_detected}</p>
          </div>
          <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl">
            <span className="text-xs text-sky-400 block">Active Cases</span>
            <p className="text-xl font-bold text-sky-300">{metrics.active_investigation_cases}</p>
          </div>
          <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl">
            <span className="text-xs text-rose-400 block">High/Critical Risk Customers</span>
            <p className="text-xl font-bold text-rose-400">
              {(metrics.customer_risk_distribution['HIGH'] || 0) + (metrics.customer_risk_distribution['CRITICAL'] || 0)}
            </p>
          </div>
          <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl">
            <span className="text-xs text-purple-400 block">Structuring Alerts</span>
            <p className="text-xl font-bold text-purple-300">
              {metrics.alerts_by_rule_type['POSSIBLE_STRUCTURING'] || 0}
            </p>
          </div>
        </div>
      )}

      {/* AML Transaction Monitoring Simulator */}
      <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4 space-y-4">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-200">
          <Zap className="w-4 h-4 text-amber-400" />
          AML Monitoring Rules Simulator (Large Cash, Structuring & Velocity)
        </div>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
          <div>
            <label className="text-xs text-slate-400 block mb-1">Customer ID</label>
            <input
              type="text"
              value={simCustomerId}
              onChange={(e) => setSimCustomerId(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 font-mono"
            />
          </div>
          <div>
            <label className="text-xs text-slate-400 block mb-1">Amount ($ USD)</label>
            <input
              type="number"
              value={simAmount}
              onChange={(e) => setSimAmount(parseFloat(e.target.value))}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 font-mono"
            />
          </div>
          <div>
            <label className="text-xs text-slate-400 block mb-1">Direction</label>
            <select
              value={simDirection}
              onChange={(e) => setSimDirection(e.target.value as any)}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-300"
            >
              <option value="OUTFLOW">Outflow (Debit)</option>
              <option value="INFLOW">Inflow (Deposit)</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-slate-400 block mb-1">Payment Method</label>
            <select
              value={simMethod}
              onChange={(e) => setSimMethod(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-300"
            >
              <option value="CASH_DEPOSIT">Cash Deposit</option>
              <option value="WIRE">Domestic Wire</option>
              <option value="CROSS_BORDER_WIRE">Cross-Border Wire</option>
              <option value="CRYPTO_OFFRAMP">Crypto Off-Ramp</option>
            </select>
          </div>
          <div className="flex items-end">
            <button
              onClick={handleSimulateTransaction}
              className="w-full py-1.5 px-3 bg-amber-600 hover:bg-amber-500 text-white rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition"
            >
              <Send className="w-3.5 h-3.5" />
              Evaluate Rules
            </button>
          </div>
        </div>
        {simResult && (
          <div className="text-xs px-3 py-1.5 rounded-lg border font-mono bg-slate-950 border-slate-800 text-slate-200">
            {simResult}
          </div>
        )}
      </div>

      {/* Main Grid: Cases on Left, Case Details & SAR Draft on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: AML Investigation Cases */}
        <div className="lg:col-span-6 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-900/40 p-3 rounded-xl border border-slate-800">
            <div className="relative flex-1 min-w-[180px]">
              <Search className="w-4 h-4 text-slate-400 absolute left-2.5 top-2.5" />
              <input
                type="text"
                placeholder="Search case or customer..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200"
              />
            </div>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded-lg px-2 py-1.5 text-xs text-slate-300"
            >
              <option value="ALL">All Statuses</option>
              <option value="NEW">New</option>
              <option value="UNDER_INVESTIGATION">Under Investigation</option>
              <option value="ESCALATED">Escalated</option>
              <option value="REPORT_PREPARED">SAR Prepared</option>
            </select>
          </div>

          <div className="space-y-2">
            {filteredCases.map((c) => {
              const isSelected = selectedCase?.case_id === c.case_id;
              return (
                <div
                  key={c.case_id}
                  onClick={() => handleSelectCase(c)}
                  className={`p-3.5 rounded-xl border transition cursor-pointer ${
                    isSelected
                      ? 'bg-slate-800/80 border-amber-500 shadow-md'
                      : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-mono text-xs font-bold text-amber-400">{c.case_id}</span>
                    <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${getStatusBadge(c.status)}`}>
                      {c.status.replace('_', ' ')}
                    </span>
                  </div>

                  <div className="flex items-center justify-between mt-2">
                    <span className="text-xs text-slate-200 font-medium">Customer: {c.customer_id}</span>
                    <span className={`px-2 py-0.5 rounded text-[11px] ${getRiskTierBadge(c.risk_tier)}`}>
                      Tier: {c.risk_tier} ({c.risk_score}/100)
                    </span>
                  </div>

                  <div className="flex items-center gap-2 mt-2 pt-2 border-t border-slate-800/60 text-[11px] text-slate-400">
                    <span>Alerts: <strong className="text-rose-400">{c.alerts.length}</strong></span>
                    <span>•</span>
                    <span>Created: {new Date(c.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: Case Details, Risk Profile, and SAR Draft */}
        <div className="lg:col-span-6 space-y-4">
          {selectedCase ? (
            <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 space-y-4">
              <div className="border-b border-slate-800 pb-3 flex justify-between items-start">
                <div>
                  <span className="font-mono text-xs text-amber-400 font-bold">{selectedCase.case_id}</span>
                  <h3 className="text-base font-bold text-slate-100 mt-1">
                    Subject: {selectedProfile?.name || selectedCase.customer_id}
                  </h3>
                  <span className="text-xs text-slate-400 font-mono">
                    Jurisdiction: {selectedProfile?.country || 'US'} | PEP: {selectedProfile?.pep_flag ? 'YES' : 'NO'}
                  </span>
                </div>
                <span className={`px-2.5 py-0.5 rounded text-xs font-bold ${getRiskTierBadge(selectedCase.risk_tier)}`}>
                  {selectedCase.risk_tier} ({selectedCase.risk_score}/100)
                </span>
              </div>

              {/* Explainable Risk Factors */}
              {selectedProfile && selectedProfile.risk_factors.length > 0 && (
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-850 space-y-1 text-xs">
                  <span className="text-slate-400 font-semibold block">Explainable Risk Factors:</span>
                  <ul className="list-disc list-inside text-slate-300 space-y-0.5 text-[11px]">
                    {selectedProfile.risk_factors.map((f, i) => (
                      <li key={i}>{f}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Triggered AML Alerts */}
              <div className="space-y-2">
                <span className="text-xs font-semibold text-slate-300 block">Flagged Suspicious Activity ({selectedCase.alerts.length})</span>
                <div className="space-y-1.5 max-h-36 overflow-y-auto pr-1">
                  {selectedCase.alerts.map((a) => (
                    <div key={a.alert_id} className="bg-slate-950 p-2.5 rounded-lg border border-slate-850 text-xs space-y-1">
                      <div className="flex justify-between items-center font-mono">
                        <span className="text-rose-400 font-bold">{a.rule_type}</span>
                        <span className="text-amber-400 font-semibold">${a.trigger_amount.toLocaleString()} USD</span>
                      </div>
                      <p className="text-[11px] text-slate-300 leading-snug">{a.description}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Action Toolbar */}
              <div className="border-t border-slate-800 pt-3 space-y-2">
                <span className="text-xs font-semibold text-slate-300 block">Investigation Actions</span>
                <div className="grid grid-cols-3 gap-2">
                  <button
                    onClick={() => handleStatusChange(selectedCase.case_id, 'UNDER_INVESTIGATION')}
                    className="py-1 px-2 bg-amber-600/30 hover:bg-amber-600/50 text-amber-300 border border-amber-600/50 rounded-lg text-xs"
                  >
                    Under Review
                  </button>
                  <button
                    onClick={() => handleStatusChange(selectedCase.case_id, 'ESCALATED')}
                    className="py-1 px-2 bg-rose-600/30 hover:bg-rose-600/50 text-rose-300 border border-rose-600/50 rounded-lg text-xs"
                  >
                    Escalate
                  </button>
                  <button
                    onClick={() => handleGenerateSAR(selectedCase.case_id)}
                    className="py-1 px-2 bg-purple-600 hover:bg-purple-500 text-white rounded-lg text-xs font-semibold"
                  >
                    Generate SAR Draft
                  </button>
                </div>
              </div>

              {/* Investigation Notes */}
              <div className="border-t border-slate-800 pt-3 space-y-2">
                <span className="text-xs font-semibold text-slate-300 block">Analyst Notes</span>
                <div className="space-y-1 max-h-24 overflow-y-auto">
                  {selectedCase.notes.map((n) => (
                    <div key={n.note_id} className="bg-slate-950 p-2 rounded text-xs text-slate-200">
                      <span className="text-[10px] text-slate-500 font-mono block">{n.author}:</span>
                      {n.content}
                    </div>
                  ))}
                </div>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newNote}
                    onChange={(e) => setNewNote(e.target.value)}
                    placeholder="Add investigation observation..."
                    className="flex-1 bg-slate-950 border border-slate-800 rounded px-2.5 py-1 text-xs text-slate-200"
                    onKeyDown={(e) => e.key === 'Enter' && handleAddNote(selectedCase.case_id)}
                  />
                  <button
                    onClick={() => handleAddNote(selectedCase.case_id)}
                    className="px-3 py-1 bg-slate-800 text-slate-200 text-xs rounded hover:bg-slate-700"
                  >
                    Post
                  </button>
                </div>
              </div>

              {/* SAR Draft Preview */}
              {sarDraft && (
                <div className="border-t border-slate-800 pt-3 space-y-2">
                  <span className="text-xs font-semibold text-purple-400 block">Internal SAR/STR Investigation Report Draft</span>
                  <div className="bg-slate-950 p-3 rounded-lg border border-purple-900/50 text-xs text-slate-300 font-mono whitespace-pre-wrap max-h-48 overflow-y-auto leading-relaxed">
                    {sarDraft.report_markdown}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-8 text-center text-slate-500 text-xs">
              Select an AML case to review flagged patterns, customer risk profiles, and generate SAR drafts.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
export default AMLInvestigationPage;

