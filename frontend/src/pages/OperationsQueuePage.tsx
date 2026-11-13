import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  AlertTriangle,
  Clock,
  UserCheck,
  CheckCircle,
  TrendingUp,
  RefreshCw,
  Search,
  Filter,
  ArrowUpRight,
  Send,
  PlusCircle,
  FileText,
  UserPlus,
  Zap,
  Info
} from 'lucide-react';

interface ActivityLogEntry {
  activity_id: string;
  timestamp: string;
  action: string;
  actor: string;
  details: Record<string, any>;
}

interface AnalystNote {
  note_id: string;
  author: string;
  created_at: string;
  content: string;
}

interface OperationalCase {
  case_id: string;
  alert_id: string;
  tenant_id: string;
  idempotency_key: string;
  transaction_id?: string;
  customer_id?: string;
  amount: number;
  currency: string;
  risk_score: number;
  priority: 'P0' | 'P1' | 'P2' | 'P3';
  status: 'OPEN' | 'IN_REVIEW' | 'ESCALATED' | 'RESOLVED' | 'CLOSED';
  assigned_to?: string;
  source: string;
  title: string;
  description: string;
  created_at: string;
  sla_deadline: string;
  sla_breached: boolean;
  resolved_at?: string;
  resolution?: string;
  notes: AnalystNote[];
  history: ActivityLogEntry[];
}

interface OperationsMetrics {
  total_cases: number;
  open_cases: number;
  in_review_cases: number;
  escalated_cases: number;
  resolved_cases: number;
  priority_breakdown: Record<string, number>;
  sla_breaches: number;
  sla_breach_rate_pct: number;
  sla_impending_breaches: number;
  analyst_workload: Record<string, number>;
  avg_resolution_time_minutes: number;
}

export const OperationsQueuePage: React.FC = () => {
  const [cases, setCases] = useState<OperationalCase[]>([]);
  const [metrics, setMetrics] = useState<OperationsMetrics | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedCase, setSelectedCase] = useState<OperationalCase | null>(null);

  // Filter state
  const [priorityFilter, setPriorityFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Simulator state
  const [simTenant, setSimTenant] = useState<string>('tenant-acme-bank');
  const [simTxnId, setSimTxnId] = useState<string>('TXN-8820-SIM');
  const [simAmount, setSimAmount] = useState<number>(4500.0);
  const [simRisk, setSimRisk] = useState<number>(0.92);
  const [simIdempKey, setSimIdempKey] = useState<string>('KEY-DEMO-01');
  const [ingestMsg, setIngestMsg] = useState<{ text: string; isDup: boolean } | null>(null);

  // Action modals / inputs
  const [actionAnalyst, setActionAnalyst] = useState<string>('sarah.connor@finguard.internal');
  const [newNoteText, setNewNoteText] = useState<string>('');
  const [resolutionType, setResolutionType] = useState<string>('CONFIRMED_FRAUD');

  const fetchOperationsData = async () => {
    setLoading(true);
    try {
      const [casesRes, metricsRes] = await Promise.all([
        fetch('http://127.0.0.1:8010/alerts'),
        fetch('http://127.0.0.1:8010/operations/metrics')
      ]);

      if (casesRes.ok) {
        const data = await casesRes.json();
        setCases(data);
        if (data.length > 0 && !selectedCase) {
          setSelectedCase(data[0]);
        }
      }
      if (metricsRes.ok) {
        const m = await metricsRes.json();
        setMetrics(m);
      }
    } catch (err) {
      console.warn('Backend unavailable, generating mock operations queue');
      generateMockData();
    } finally {
      setLoading(false);
    }
  };

  const generateMockData = () => {
    const mockCases: OperationalCase[] = [
      {
        case_id: 'CASE-P0-9901',
        alert_id: 'ALT-9901',
        tenant_id: 'tenant-acme-bank',
        idempotency_key: 'TXN-90812-BURST',
        transaction_id: 'TXN-90812-BURST',
        customer_id: 'CUST-4412',
        amount: 8500.0,
        currency: 'USD',
        risk_score: 0.96,
        priority: 'P0',
        status: 'OPEN',
        assigned_to: undefined,
        source: 'TEMPORAL_GRU_STREAM',
        title: 'P0: Rapid Micro-Burst Velocity & Ring Linkage',
        description: 'Cluster of 14 high-velocity transactions flagged by Temporal GRU and GNN ring detection.',
        created_at: new Date(Date.now() - 10 * 60000).toISOString(),
        sla_deadline: new Date(Date.now() + 20 * 60000).toISOString(),
        sla_breached: false,
        notes: [],
        history: [
          {
            activity_id: 'ACT-001',
            timestamp: new Date(Date.now() - 10 * 60000).toISOString(),
            action: 'ALERT_INGESTED',
            actor: 'TEMPORAL_GRU_STREAM',
            details: { priority: 'P0', sla_minutes: 30 }
          }
        ]
      },
      {
        case_id: 'CASE-P1-8842',
        alert_id: 'ALT-8842',
        tenant_id: 'tenant-acme-bank',
        idempotency_key: 'TXN-77210-UEBA',
        transaction_id: 'TXN-77210-UEBA',
        customer_id: 'CUST-1190',
        amount: 3200.0,
        currency: 'USD',
        risk_score: 0.78,
        priority: 'P1',
        status: 'IN_REVIEW',
        assigned_to: 'sarah.connor@finguard.internal',
        source: 'UEBA_ANOMALY_ENGINE',
        title: 'P1: Impossible Travel & Off-Hours Device Anomaly',
        description: 'Login location jump from London to Singapore within 22 minutes with new device fingerprint.',
        created_at: new Date(Date.now() - 45 * 60000).toISOString(),
        sla_deadline: new Date(Date.now() + 75 * 60000).toISOString(),
        sla_breached: false,
        notes: [
          {
            note_id: 'NOTE-1',
            author: 'sarah.connor@finguard.internal',
            created_at: new Date(Date.now() - 15 * 60000).toISOString(),
            content: 'Customer cardholder contacted via verified SMS OTP. Awaiting response.'
          }
        ],
        history: [
          {
            activity_id: 'ACT-101',
            timestamp: new Date(Date.now() - 45 * 60000).toISOString(),
            action: 'ALERT_INGESTED',
            actor: 'UEBA_ANOMALY_ENGINE',
            details: { priority: 'P1', sla_minutes: 120 }
          },
          {
            activity_id: 'ACT-102',
            timestamp: new Date(Date.now() - 30 * 60000).toISOString(),
            action: 'ANALYST_ASSIGNED',
            actor: 'supervisor.ops',
            details: { assigned_to: 'sarah.connor@finguard.internal' }
          }
        ]
      },
      {
        case_id: 'CASE-P2-7719',
        alert_id: 'ALT-7719',
        tenant_id: 'tenant-acme-bank',
        idempotency_key: 'TXN-55319-THREAT',
        transaction_id: 'TXN-55319-THREAT',
        customer_id: 'CUST-8831',
        amount: 1450.0,
        currency: 'USD',
        risk_score: 0.52,
        priority: 'P2',
        status: 'OPEN',
        assigned_to: undefined,
        source: 'THREAT_INTEL_IOC',
        title: 'P2: Tor Exit Node / Residential Proxy Transaction',
        description: 'Transaction originated from IP known for credential stuffing and residential proxy routing.',
        created_at: new Date(Date.now() - 120 * 60000).toISOString(),
        sla_deadline: new Date(Date.now() + 360 * 60000).toISOString(),
        sla_breached: false,
        notes: [],
        history: []
      }
    ];

    setCases(mockCases);
    setSelectedCase(mockCases[0]);
    setMetrics({
      total_cases: 3,
      open_cases: 2,
      in_review_cases: 1,
      escalated_cases: 0,
      resolved_cases: 0,
      priority_breakdown: { P0: 1, P1: 1, P2: 1, P3: 0 },
      sla_breaches: 0,
      sla_breach_rate_pct: 0.0,
      sla_impending_breaches: 1,
      analyst_workload: { 'sarah.connor@finguard.internal': 1 },
      avg_resolution_time_minutes: 0.0
    });
  };

  useEffect(() => {
    fetchOperationsData();
    const interval = setInterval(fetchOperationsData, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleIngestAlert = async () => {
    const payload = {
      tenant_id: simTenant,
      transaction_id: simTxnId,
      amount: simAmount,
      risk_score: simRisk,
      idempotency_key: simIdempKey,
      source: 'SIMULATOR_TEST'
    };

    try {
      const res = await fetch('http://127.0.0.1:8010/alerts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        const data = await res.json();
        setIngestMsg({
          text: data.is_duplicate
            ? `⚠️ Deduplicated: Re-used existing Case ${data.case_id}`
            : `✅ Case ${data.case_id} Created (${data.priority})`,
          isDup: data.is_duplicate
        });
        fetchOperationsData();
      }
    } catch {
      setIngestMsg({ text: 'Simulated ingest response received', isDup: false });
    }
  };

  const handleAssignAnalyst = async (caseId: string) => {
    try {
      await fetch(`http://127.0.0.1:8010/cases/${caseId}/assign`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ analyst_id: actionAnalyst, assigned_by: 'lead.supervisor' })
      });
      fetchOperationsData();
    } catch (e) {
      console.error(e);
    }
  };

  const handleUpdateStatus = async (caseId: string, status: string) => {
    try {
      await fetch(`http://127.0.0.1:8010/cases/${caseId}/status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status, updated_by: 'sarah.connor@finguard.internal' })
      });
      fetchOperationsData();
    } catch (e) {
      console.error(e);
    }
  };

  const handleAddNote = async (caseId: string) => {
    if (!newNoteText.trim()) return;
    try {
      await fetch(`http://127.0.0.1:8010/cases/${caseId}/notes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ author: 'sarah.connor@finguard.internal', content: newNoteText })
      });
      setNewNoteText('');
      fetchOperationsData();
    } catch (e) {
      console.error(e);
    }
  };

  const handleResolveCase = async (caseId: string) => {
    try {
      await fetch(`http://127.0.0.1:8010/cases/${caseId}/resolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          resolution: resolutionType,
          resolved_by: 'sarah.connor@finguard.internal',
          notes: 'Investigation concluded via operations workspace.'
        })
      });
      fetchOperationsData();
    } catch (e) {
      console.error(e);
    }
  };

  const filteredCases = cases.filter((c) => {
    if (priorityFilter !== 'ALL' && c.priority !== priorityFilter) return false;
    if (statusFilter !== 'ALL' && c.status !== statusFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        c.case_id.toLowerCase().includes(q) ||
        (c.transaction_id && c.transaction_id.toLowerCase().includes(q)) ||
        (c.customer_id && c.customer_id.toLowerCase().includes(q)) ||
        c.title.toLowerCase().includes(q)
      );
    }
    return true;
  });

  const getPriorityBadge = (prio: string) => {
    switch (prio) {
      case 'P0':
        return 'bg-rose-500/20 text-rose-400 border border-rose-500/40 animate-pulse';
      case 'P1':
        return 'bg-orange-500/20 text-orange-400 border border-orange-500/40';
      case 'P2':
        return 'bg-amber-500/20 text-amber-400 border border-amber-500/40';
      default:
        return 'bg-slate-500/20 text-slate-400 border border-slate-500/40';
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'OPEN':
        return 'bg-sky-500/20 text-sky-400 border border-sky-500/40';
      case 'IN_REVIEW':
        return 'bg-amber-500/20 text-amber-400 border border-amber-500/40';
      case 'ESCALATED':
        return 'bg-rose-500/20 text-rose-400 border border-rose-500/40';
      case 'RESOLVED':
        return 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40';
      default:
        return 'bg-slate-500/20 text-slate-400 border border-slate-500/40';
    }
  };

  const getRemainingTimeStr = (deadlineStr: string) => {
    const diff = new Date(deadlineStr).getTime() - Date.now();
    if (diff <= 0) return 'BREACHED';
    const mins = Math.floor(diff / 60000);
    if (mins < 60) return `${mins}m remaining`;
    const hours = Math.floor(mins / 60);
    return `${hours}h ${mins % 60}m remaining`;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-slate-100">
              Operations Queue & SLA Management
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-mono bg-purple-500/10 text-purple-400 border border-purple-500/30">
              Phase 21
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Real-time alert intake, tenant-scoped deduplication, priority queue dispatch, and strict SLA enforcement.
          </p>
        </div>
        <button
          onClick={fetchOperationsData}
          className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg border border-slate-700 transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh Queue
        </button>
      </div>

      {/* Metrics Bar */}
      {metrics && (
        <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
          <div className="bg-slate-900/60 border border-slate-800 p-3 rounded-xl">
            <span className="text-xs text-slate-400">Total Cases</span>
            <p className="text-xl font-bold text-slate-100">{metrics.total_cases}</p>
          </div>
          <div className="bg-slate-900/60 border border-slate-800 p-3 rounded-xl">
            <span className="text-xs text-sky-400">Open Queue</span>
            <p className="text-xl font-bold text-sky-300">{metrics.open_cases}</p>
          </div>
          <div className="bg-slate-900/60 border border-slate-800 p-3 rounded-xl">
            <span className="text-xs text-amber-400">In Review</span>
            <p className="text-xl font-bold text-amber-300">{metrics.in_review_cases}</p>
          </div>
          <div className="bg-slate-900/60 border border-slate-800 p-3 rounded-xl">
            <span className="text-xs text-rose-400">P0 / Critical</span>
            <p className="text-xl font-bold text-rose-300">{metrics.priority_breakdown['P0'] || 0}</p>
          </div>
          <div className="bg-slate-900/60 border border-slate-800 p-3 rounded-xl">
            <span className="text-xs text-rose-400">SLA Breaches</span>
            <p className="text-xl font-bold text-rose-400">
              {metrics.sla_breaches} ({metrics.sla_breach_rate_pct}%)
            </p>
          </div>
          <div className="bg-slate-900/60 border border-slate-800 p-3 rounded-xl">
            <span className="text-xs text-emerald-400">Resolved Cases</span>
            <p className="text-xl font-bold text-emerald-300">{metrics.resolved_cases}</p>
          </div>
        </div>
      )}

      {/* Alert Ingestion Simulator */}
      <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4 space-y-4">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-200">
          <Zap className="w-4 h-4 text-purple-400" />
          Real-Time Alert Ingestion & Idempotency Simulator
        </div>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
          <div>
            <label className="text-xs text-slate-400 block mb-1">Tenant ID</label>
            <input
              type="text"
              value={simTenant}
              onChange={(e) => setSimTenant(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 font-mono"
            />
          </div>
          <div>
            <label className="text-xs text-slate-400 block mb-1">Transaction ID</label>
            <input
              type="text"
              value={simTxnId}
              onChange={(e) => setSimTxnId(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 font-mono"
            />
          </div>
          <div>
            <label className="text-xs text-slate-400 block mb-1">Idempotency Key</label>
            <input
              type="text"
              value={simIdempKey}
              onChange={(e) => setSimIdempKey(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 font-mono"
            />
          </div>
          <div>
            <label className="text-xs text-slate-400 block mb-1">
              Risk Score: <span className="text-purple-400 font-bold">{simRisk.toFixed(2)}</span>
            </label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.01"
              value={simRisk}
              onChange={(e) => setSimRisk(parseFloat(e.target.value))}
              className="w-full accent-purple-500 mt-1"
            />
          </div>
          <div className="flex items-end">
            <button
              onClick={handleIngestAlert}
              className="w-full py-1.5 px-3 bg-purple-600 hover:bg-purple-500 text-white rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition"
            >
              <Send className="w-3.5 h-3.5" />
              Ingest Alert
            </button>
          </div>
        </div>
        {ingestMsg && (
          <div
            className={`text-xs px-3 py-1.5 rounded-lg border font-mono ${
              ingestMsg.isDup
                ? 'bg-amber-950/40 border-amber-800 text-amber-300'
                : 'bg-emerald-950/40 border-emerald-800 text-emerald-300'
            }`}
          >
            {ingestMsg.text}
          </div>
        )}
      </div>

      {/* Main Grid: Queue on Left, Case Detail & Timeline on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Operations Queue */}
        <div className="lg:col-span-7 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-900/40 p-3 rounded-xl border border-slate-800">
            <div className="relative flex-1 min-w-[180px]">
              <Search className="w-4 h-4 text-slate-400 absolute left-2.5 top-2.5" />
              <input
                type="text"
                placeholder="Search case, txn, customer..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200"
              />
            </div>
            <div className="flex items-center gap-2">
              <select
                value={priorityFilter}
                onChange={(e) => setPriorityFilter(e.target.value)}
                className="bg-slate-950 border border-slate-800 rounded-lg px-2 py-1.5 text-xs text-slate-300"
              >
                <option value="ALL">All Priorities</option>
                <option value="P0">P0 (Critical)</option>
                <option value="P1">P1 (High)</option>
                <option value="P2">P2 (Medium)</option>
                <option value="P3">P3 (Low)</option>
              </select>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="bg-slate-950 border border-slate-800 rounded-lg px-2 py-1.5 text-xs text-slate-300"
              >
                <option value="ALL">All Statuses</option>
                <option value="OPEN">Open</option>
                <option value="IN_REVIEW">In Review</option>
                <option value="ESCALATED">Escalated</option>
                <option value="RESOLVED">Resolved</option>
              </select>
            </div>
          </div>

          <div className="space-y-2">
            {filteredCases.map((c) => {
              const isSelected = selectedCase?.case_id === c.case_id;
              const remainingTime = getRemainingTimeStr(c.sla_deadline);
              const isBreached = remainingTime === 'BREACHED' || c.sla_breached;

              return (
                <div
                  key={c.case_id}
                  onClick={() => setSelectedCase(c)}
                  className={`p-3 rounded-xl border transition cursor-pointer ${
                    isSelected
                      ? 'bg-slate-800/80 border-purple-500 shadow-md'
                      : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 rounded text-xs font-bold ${getPriorityBadge(c.priority)}`}>
                        {c.priority}
                      </span>
                      <span className="font-mono text-xs font-semibold text-slate-100">{c.case_id}</span>
                      <span className="text-xs text-slate-400 font-mono">({c.tenant_id})</span>
                    </div>
                    <span className={`px-2 py-0.5 rounded text-[11px] font-medium ${getStatusBadge(c.status)}`}>
                      {c.status}
                    </span>
                  </div>

                  <p className="text-xs font-medium text-slate-200 truncate">{c.title}</p>

                  <div className="flex items-center justify-between mt-2 pt-2 border-t border-slate-800/60 text-[11px] text-slate-400">
                    <div className="flex items-center gap-1.5">
                      <Clock className="w-3 h-3 text-slate-400" />
                      <span className={isBreached ? 'text-rose-400 font-semibold' : 'text-slate-300'}>
                        {remainingTime}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span>Score: <strong className="text-purple-400">{c.risk_score.toFixed(2)}</strong></span>
                      {c.assigned_to ? (
                        <span className="text-sky-400 font-mono truncate max-w-[140px]">{c.assigned_to}</span>
                      ) : (
                        <span className="text-amber-400 italic">Unassigned</span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right: Selected Case Details, Actions & Audit Timeline */}
        <div className="lg:col-span-5 space-y-4">
          {selectedCase ? (
            <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4 space-y-5">
              <div className="border-b border-slate-800 pb-3">
                <div className="flex items-center justify-between">
                  <span className={`px-2.5 py-0.5 rounded text-xs font-bold ${getPriorityBadge(selectedCase.priority)}`}>
                    Priority {selectedCase.priority}
                  </span>
                  <span className={`px-2.5 py-0.5 rounded text-xs ${getStatusBadge(selectedCase.status)}`}>
                    {selectedCase.status}
                  </span>
                </div>
                <h3 className="text-base font-bold text-slate-100 mt-2">{selectedCase.title}</h3>
                <p className="text-xs text-slate-400 mt-1">{selectedCase.description}</p>
              </div>

              {/* Quick Case Attributes */}
              <div className="grid grid-cols-2 gap-2 text-xs bg-slate-950 p-3 rounded-lg border border-slate-800 font-mono">
                <div>
                  <span className="text-slate-500">Transaction:</span>
                  <p className="text-slate-200">{selectedCase.transaction_id || 'N/A'}</p>
                </div>
                <div>
                  <span className="text-slate-500">Customer:</span>
                  <p className="text-slate-200">{selectedCase.customer_id || 'N/A'}</p>
                </div>
                <div>
                  <span className="text-slate-500">Amount:</span>
                  <p className="text-slate-200">${selectedCase.amount.toLocaleString()} {selectedCase.currency}</p>
                </div>
                <div>
                  <span className="text-slate-500">SLA Deadline:</span>
                  <p className={selectedCase.sla_breached ? 'text-rose-400 font-bold' : 'text-slate-300'}>
                    {getRemainingTimeStr(selectedCase.sla_deadline)}
                  </p>
                </div>
              </div>

              {/* Action Toolbar */}
              <div className="space-y-2 border-t border-slate-800 pt-3">
                <span className="text-xs font-semibold text-slate-300 block">Analyst Workflow Actions</span>
                
                {/* Assign Analyst */}
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={actionAnalyst}
                    onChange={(e) => setActionAnalyst(e.target.value)}
                    className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1 text-xs text-slate-200 font-mono"
                    placeholder="analyst email..."
                  />
                  <button
                    onClick={() => handleAssignAnalyst(selectedCase.case_id)}
                    className="px-3 py-1 bg-sky-600 hover:bg-sky-500 text-white rounded-lg text-xs font-medium flex items-center gap-1"
                  >
                    <UserPlus className="w-3.5 h-3.5" />
                    Assign
                  </button>
                </div>

                {/* Status transitions */}
                <div className="grid grid-cols-3 gap-2 pt-1">
                  <button
                    onClick={() => handleUpdateStatus(selectedCase.case_id, 'IN_REVIEW')}
                    className="py-1 px-2 bg-amber-600/30 hover:bg-amber-600/50 text-amber-300 border border-amber-600/50 rounded-lg text-xs"
                  >
                    In Review
                  </button>
                  <button
                    onClick={() => handleUpdateStatus(selectedCase.case_id, 'ESCALATED')}
                    className="py-1 px-2 bg-rose-600/30 hover:bg-rose-600/50 text-rose-300 border border-rose-600/50 rounded-lg text-xs"
                  >
                    Escalate
                  </button>
                  <button
                    onClick={() => handleResolveCase(selectedCase.case_id)}
                    className="py-1 px-2 bg-emerald-600/30 hover:bg-emerald-600/50 text-emerald-300 border border-emerald-600/50 rounded-lg text-xs"
                  >
                    Resolve
                  </button>
                </div>
              </div>

              {/* Notes & Activity History */}
              <div className="space-y-3 border-t border-slate-800 pt-3">
                <span className="text-xs font-semibold text-slate-300 block">Investigation Notes</span>
                <div className="space-y-2 max-h-36 overflow-y-auto pr-1">
                  {selectedCase.notes.length === 0 ? (
                    <p className="text-xs text-slate-500 italic">No notes logged yet.</p>
                  ) : (
                    selectedCase.notes.map((n) => (
                      <div key={n.note_id} className="bg-slate-950 p-2 rounded-lg border border-slate-850 text-xs">
                        <div className="flex justify-between text-[10px] text-slate-400 mb-1">
                          <span className="font-semibold text-slate-300">{n.author}</span>
                          <span>{new Date(n.created_at).toLocaleTimeString()}</span>
                        </div>
                        <p className="text-slate-200">{n.content}</p>
                      </div>
                    ))
                  )}
                </div>

                {/* Add Note Input */}
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newNoteText}
                    onChange={(e) => setNewNoteText(e.target.value)}
                    placeholder="Add investigator note..."
                    className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1 text-xs text-slate-200"
                    onKeyDown={(e) => e.key === 'Enter' && handleAddNote(selectedCase.case_id)}
                  />
                  <button
                    onClick={() => handleAddNote(selectedCase.case_id)}
                    className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs"
                  >
                    Post
                  </button>
                </div>
              </div>

              {/* Activity Timeline */}
              <div className="space-y-2 border-t border-slate-800 pt-3">
                <span className="text-xs font-semibold text-slate-300 block">Activity Audit Timeline</span>
                <div className="space-y-1.5 max-h-32 overflow-y-auto pr-1">
                  {selectedCase.history.map((h) => (
                    <div key={h.activity_id} className="text-[11px] text-slate-400 flex items-start gap-2">
                      <span className="text-purple-400 font-mono">•</span>
                      <div>
                        <span className="text-slate-200 font-medium">{h.action}</span> by{' '}
                        <span className="text-slate-400">{h.actor}</span>
                        <span className="text-slate-600 ml-2">
                          {new Date(h.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-8 text-center text-slate-500 text-xs">
              Select an alert from the queue to view SLA details and workflow actions.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
export default OperationsQueuePage;

