import React, { useState, useEffect } from 'react';
import {
  CreditCard,
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  ArrowUpRight,
  TrendingUp,
  MapPin,
  Clock,
  Smartphone,
  Globe,
  UserCheck,
  Layers,
  Search,
  Filter,
  PlusCircle,
  RefreshCw,
  Info,
  CheckCircle2,
  DollarSign
} from 'lucide-react';

interface PaymentSignal {
  signal_name: string;
  points: number;
  category: string;
  description: string;
}

interface PaymentAssessment {
  assessment_id: string;
  transaction_id: string;
  customer_id: string;
  amount: number;
  currency: string;
  payment_rail: string;
  risk_score: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
  action: 'MONITOR' | 'REVIEW' | 'PRIORITY_REVIEW';
  signals: PaymentSignal[];
  summary: string;
  assessed_at: string;
  disclaimer: string;
}

interface PaymentMetrics {
  total_assessed: number;
  monitor_count: number;
  review_count: number;
  priority_review_count: number;
  avg_risk_score: number;
  high_value_count: number;
  new_beneficiary_count: number;
  city_mismatch_count: number;
  velocity_flagged_count: number;
  international_count: number;
}

const DEMO_ASSESSMENTS: PaymentAssessment[] = [
  {
    assessment_id: 'PA-DEMO-001',
    transaction_id: 'TXN-2026-UPI-285000',
    customer_id: 'CUST-BLR-40291',
    amount: 285000.0,
    currency: 'INR',
    payment_rail: 'UPI',
    risk_score: 45,
    risk_level: 'MEDIUM',
    action: 'REVIEW',
    signals: [
      {
        signal_name: 'High-value payment',
        points: 20,
        category: 'Amount',
        description: 'Transaction amount ₹285,000.00 exceeds high-value threshold of ₹200,000.00'
      },
      {
        signal_name: 'New beneficiary',
        points: 15,
        category: 'Payee',
        description: "First-time transfer to beneficiary 'Apex Digital Services'"
      },
      {
        signal_name: 'City mismatch',
        points: 10,
        category: 'Geography',
        description: "Home city 'Bengaluru' differs from transaction city 'Mumbai'"
      }
    ],
    summary: 'Payment of INR 285,000.00 via UPI scored 45/100 (MEDIUM) triggering action REVIEW across 3 risk signal(s).',
    assessed_at: new Date(Date.now() - 1000 * 60 * 5).toISOString(),
    disclaimer: 'Illustrative operational risk indicators for analyst prioritization. No automated payment rejection, reversal, or account freezing is implemented.'
  },
  {
    assessment_id: 'PA-DEMO-002',
    transaction_id: 'TXN-2026-NEFT-15000',
    customer_id: 'CUST-DEL-10294',
    amount: 15000.0,
    currency: 'INR',
    payment_rail: 'NEFT',
    risk_score: 0,
    risk_level: 'LOW',
    action: 'MONITOR',
    signals: [],
    summary: 'Payment of INR 15,000.00 via NEFT scored 0/100 (LOW) triggering action MONITOR across 0 risk signal(s).',
    assessed_at: new Date(Date.now() - 1000 * 60 * 25).toISOString(),
    disclaimer: 'Illustrative operational risk indicators for analyst prioritization. No automated payment rejection, reversal, or account freezing is implemented.'
  },
  {
    assessment_id: 'PA-DEMO-003',
    transaction_id: 'TXN-2026-RTGS-750000',
    customer_id: 'CUST-HYD-55102',
    amount: 750000.0,
    currency: 'USD',
    payment_rail: 'RTGS',
    risk_score: 80,
    risk_level: 'HIGH',
    action: 'PRIORITY_REVIEW',
    signals: [
      {
        signal_name: 'High-value payment',
        points: 20,
        category: 'Amount',
        description: 'Transaction amount ₹750,000.00 exceeds high-value threshold of ₹200,000.00'
      },
      {
        signal_name: 'New beneficiary',
        points: 15,
        category: 'Payee',
        description: "First-time transfer to beneficiary 'Global Offshore Holdings Ltd'"
      },
      {
        signal_name: 'City mismatch',
        points: 10,
        category: 'Geography',
        description: "Home city 'Hyderabad' differs from transaction city 'London'"
      },
      {
        signal_name: 'International payment',
        points: 20,
        category: 'CrossBorder',
        description: "Cross-border payment flag set or non-domestic currency 'USD'"
      },
      {
        signal_name: 'Missing device context',
        points: 15,
        category: 'Device',
        description: 'Transaction lacks authenticated device fingerprint or hardware context'
      }
    ],
    summary: 'Payment of USD 750,000.00 via RTGS scored 80/100 (HIGH) triggering action PRIORITY_REVIEW across 5 risk signal(s).',
    assessed_at: new Date(Date.now() - 1000 * 60 * 2).toISOString(),
    disclaimer: 'Illustrative operational risk indicators for analyst prioritization. No automated payment rejection, reversal, or account freezing is implemented.'
  }
];

export const PaymentFraudPage: React.FC = () => {
  const [assessments, setAssessments] = useState<PaymentAssessment[]>(DEMO_ASSESSMENTS);
  const [selectedAssessment, setSelectedAssessment] = useState<PaymentAssessment>(DEMO_ASSESSMENTS[0]);
  const [metrics, setMetrics] = useState<PaymentMetrics>({
    total_assessed: 3,
    monitor_count: 1,
    review_count: 1,
    priority_review_count: 1,
    avg_risk_score: 41.7,
    high_value_count: 2,
    new_beneficiary_count: 2,
    city_mismatch_count: 2,
    velocity_flagged_count: 0,
    international_count: 1
  });
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedRail, setSelectedRail] = useState('ALL');
  const [selectedAction, setSelectedAction] = useState('ALL');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  // New payment form state
  const [formData, setFormData] = useState({
    transaction_id: `TXN-PAY-${Date.now().toString().slice(-6)}`,
    customer_id: 'CUST-MUM-89210',
    amount: 285000,
    currency: 'INR',
    payment_rail: 'UPI',
    beneficiary_account: 'ACC-HDFC-882194',
    beneficiary_name: 'Apex Digital Services',
    is_new_beneficiary: true,
    customer_home_city: 'Bengaluru',
    transaction_city: 'Mumbai',
    is_international: false,
    has_device: true
  });

  const fetchAssessments = async () => {
    try {
      setLoading(true);
      const res = await fetch('http://127.0.0.1:8011/payments/assessments');
      if (res.ok) {
        const data = await res.json();
        if (data && data.length > 0) {
          setAssessments(data);
          setSelectedAssessment(data[0]);
        }
      }
      const metRes = await fetch('http://127.0.0.1:8011/payments/metrics');
      if (metRes.ok) {
        const metData = await metRes.json();
        setMetrics(metData);
      }
    } catch {
      // Fallback to local demo assessments
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAssessments();
  }, []);

  const handleAssessSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const payload = {
      transaction_id: formData.transaction_id,
      customer_id: formData.customer_id,
      amount: Number(formData.amount),
      currency: formData.currency,
      payment_rail: formData.payment_rail,
      beneficiary_account: formData.beneficiary_account,
      beneficiary_name: formData.beneficiary_name,
      is_new_beneficiary: formData.is_new_beneficiary,
      customer_home_city: formData.customer_home_city,
      transaction_city: formData.transaction_city,
      is_international: formData.is_international,
      device_context: formData.has_device
        ? {
            device_id: 'DEV-MOBILE-ANDROID-01',
            ip_address: '49.36.120.45',
            location: `${formData.transaction_city}, IN`
          }
        : null
    };

    try {
      const res = await fetch('http://127.0.0.1:8011/payments/assess', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        const result: PaymentAssessment = await res.json();
        setAssessments((prev) => [result, ...prev]);
        setSelectedAssessment(result);
        setIsModalOpen(false);
        fetchAssessments();
      } else {
        simulateLocalAssessment(payload);
      }
    } catch {
      simulateLocalAssessment(payload);
    }
  };

  const simulateLocalAssessment = (payload: any) => {
    const signals: PaymentSignal[] = [];
    if (payload.amount >= 200000) {
      signals.push({
        signal_name: 'High-value payment',
        points: 20,
        category: 'Amount',
        description: `Transaction amount ₹${payload.amount.toLocaleString()} exceeds high-value threshold of ₹200,000`
      });
    }
    if (payload.is_new_beneficiary) {
      signals.push({
        signal_name: 'New beneficiary',
        points: 15,
        category: 'Payee',
        description: `First-time transfer to beneficiary '${payload.beneficiary_name || payload.beneficiary_account}'`
      });
    }
    if (
      payload.customer_home_city &&
      payload.transaction_city &&
      payload.customer_home_city.toLowerCase() !== payload.transaction_city.toLowerCase()
    ) {
      signals.push({
        signal_name: 'City mismatch',
        points: 10,
        category: 'Geography',
        description: `Home city '${payload.customer_home_city}' differs from transaction city '${payload.transaction_city}'`
      });
    }
    if (payload.is_international || payload.currency !== 'INR') {
      signals.push({
        signal_name: 'International payment',
        points: 20,
        category: 'CrossBorder',
        description: `Cross-border payment flag set or non-domestic currency '${payload.currency}'`
      });
    }
    if (!payload.device_context || !payload.device_context.device_id) {
      signals.push({
        signal_name: 'Missing device context',
        points: 15,
        category: 'Device',
        description: 'Transaction lacks authenticated device fingerprint or hardware context'
      });
    }

    const totalPoints = Math.min(100, signals.reduce((sum, s) => sum + s.points, 0));
    let level: 'LOW' | 'MEDIUM' | 'HIGH' = 'LOW';
    let action: 'MONITOR' | 'REVIEW' | 'PRIORITY_REVIEW' = 'MONITOR';

    if (totalPoints >= 70) {
      level = 'HIGH';
      action = 'PRIORITY_REVIEW';
    } else if (totalPoints >= 30) {
      level = 'MEDIUM';
      action = 'REVIEW';
    }

    const newAssessment: PaymentAssessment = {
      assessment_id: `PA-${Date.now().toString().slice(-6)}`,
      transaction_id: payload.transaction_id,
      customer_id: payload.customer_id,
      amount: payload.amount,
      currency: payload.currency,
      payment_rail: payload.payment_rail,
      risk_score: totalPoints,
      risk_level: level,
      action: action,
      signals: signals,
      summary: `Payment of ${payload.currency} ${payload.amount.toLocaleString()} via ${payload.payment_rail} scored ${totalPoints}/100 (${level}) triggering action ${action}.`,
      assessed_at: new Date().toISOString(),
      disclaimer: 'Illustrative operational risk indicators for analyst prioritization. No automated payment rejection, reversal, or account freezing is implemented.'
    };

    setAssessments((prev) => [newAssessment, ...prev]);
    setSelectedAssessment(newAssessment);
    setIsModalOpen(false);
  };

  const filteredAssessments = assessments.filter((a) => {
    const matchesSearch =
      a.transaction_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      a.customer_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      a.summary.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesRail = selectedRail === 'ALL' || a.payment_rail === selectedRail;
    const matchesAction = selectedAction === 'ALL' || a.action === selectedAction;
    return matchesSearch && matchesRail && matchesAction;
  });

  const getScoreColor = (score: number) => {
    if (score >= 70) return 'text-red-400 bg-red-950/40 border-red-800';
    if (score >= 30) return 'text-amber-400 bg-amber-950/40 border-amber-800';
    return 'text-emerald-400 bg-emerald-950/40 border-emerald-800';
  };

  const getActionBadge = (action: string) => {
    switch (action) {
      case 'PRIORITY_REVIEW':
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-red-500/20 text-red-300 border border-red-500/30 flex items-center gap-1">
            <ShieldAlert className="w-3 h-3" /> PRIORITY REVIEW
          </span>
        );
      case 'REVIEW':
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30 flex items-center gap-1">
            <AlertTriangle className="w-3 h-3" /> REVIEW
          </span>
        );
      default:
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
            <ShieldCheck className="w-3 h-3" /> MONITOR
          </span>
        );
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-indigo-600/20 border border-indigo-500/30 rounded-xl">
              <CreditCard className="w-6 h-6 text-indigo-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
                Payment Fraud Intelligence & Real-Time Monitoring
                <span className="text-xs font-medium px-2.5 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                  Phase 29
                </span>
              </h1>
              <p className="text-sm text-slate-400">
                Multi-rail transaction intelligence (UPI, IMPS, NEFT, RTGS, Cards) with rolling velocity & explainable scoring
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => fetchAssessments()}
            disabled={loading}
            className="px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-sm font-medium transition flex items-center gap-2 text-slate-300"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button
            onClick={() => setIsModalOpen(true)}
            className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold transition flex items-center gap-2 shadow-lg shadow-indigo-600/20"
          >
            <PlusCircle className="w-4 h-4" />
            Simulate Payment
          </button>
        </div>
      </div>

      {/* Advisory Notice Banner */}
      <div className="bg-slate-900/60 border border-indigo-900/40 rounded-xl p-4 flex items-start gap-3">
        <Info className="w-5 h-5 text-indigo-400 shrink-0 mt-0.5" />
        <div className="text-xs text-slate-300 leading-relaxed">
          <span className="font-semibold text-indigo-300">Human-in-the-Loop Operational Standard:</span> Risk scores (0–100) and alert actions (<span className="text-emerald-400">MONITOR</span>, <span className="text-amber-400">REVIEW</span>, <span className="text-red-400">PRIORITY_REVIEW</span>) are operational triage tools for compliance and fraud operations teams. No automated payment rejection, funds reversal, or account freezing is performed.
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
          <div className="text-xs font-medium text-slate-400">Total Payments Assessed</div>
          <div className="text-2xl font-bold text-white mt-1">{metrics.total_assessed}</div>
          <div className="text-xs text-slate-500 mt-1 flex items-center gap-1">
            <Layers className="w-3 h-3" /> Across all active rails
          </div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
          <div className="text-xs font-medium text-emerald-400">Monitor (Low Risk)</div>
          <div className="text-2xl font-bold text-emerald-400 mt-1">{metrics.monitor_count}</div>
          <div className="text-xs text-slate-500 mt-1">Score &lt; 30 (Passive audit)</div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
          <div className="text-xs font-medium text-amber-400">Review (Medium)</div>
          <div className="text-2xl font-bold text-amber-400 mt-1">{metrics.review_count}</div>
          <div className="text-xs text-slate-500 mt-1">Score 30–69 (Analyst queue)</div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
          <div className="text-xs font-medium text-red-400">Priority Review (High)</div>
          <div className="text-2xl font-bold text-red-400 mt-1">{metrics.priority_review_count}</div>
          <div className="text-xs text-slate-500 mt-1">Score &ge; 70 (Urgent P0 triage)</div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
          <div className="text-xs font-medium text-indigo-400">Avg Risk Score</div>
          <div className="text-2xl font-bold text-indigo-400 mt-1">{metrics.avg_risk_score}</div>
          <div className="text-xs text-slate-500 mt-1">Weighted rule aggregate</div>
        </div>
      </div>

      {/* Main Layout: Assessment Stream & Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Stream Table (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          {/* Filters Bar */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3 flex flex-wrap items-center justify-between gap-3">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-500" />
              <input
                type="text"
                placeholder="Search by Txn ID, Customer, or Payee..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-9 pr-3 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div className="flex items-center gap-2">
              <select
                value={selectedRail}
                onChange={(e) => setSelectedRail(e.target.value)}
                className="bg-slate-950 border border-slate-800 text-xs text-slate-300 rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-indigo-500"
              >
                <option value="ALL">All Rails</option>
                <option value="UPI">UPI</option>
                <option value="IMPS">IMPS</option>
                <option value="NEFT">NEFT</option>
                <option value="RTGS">RTGS</option>
                <option value="CARD">CARD</option>
              </select>

              <select
                value={selectedAction}
                onChange={(e) => setSelectedAction(e.target.value)}
                className="bg-slate-950 border border-slate-800 text-xs text-slate-300 rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-indigo-500"
              >
                <option value="ALL">All Actions</option>
                <option value="MONITOR">Monitor</option>
                <option value="REVIEW">Review</option>
                <option value="PRIORITY_REVIEW">Priority Review</option>
              </select>
            </div>
          </div>

          {/* Transactions List */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
            <div className="px-4 py-3 border-b border-slate-800 flex items-center justify-between">
              <div className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                Real-Time Payment Stream ({filteredAssessments.length})
              </div>
              <div className="text-xs text-slate-500">Auto-prioritizing live queue</div>
            </div>

            <div className="divide-y divide-slate-800/60 max-h-[580px] overflow-y-auto">
              {filteredAssessments.length === 0 ? (
                <div className="p-8 text-center text-slate-500 text-sm">
                  No payment assessments matched current filters.
                </div>
              ) : (
                filteredAssessments.map((a) => {
                  const isSelected = selectedAssessment?.transaction_id === a.transaction_id;
                  return (
                    <div
                      key={a.transaction_id}
                      onClick={() => setSelectedAssessment(a)}
                      className={`p-4 transition cursor-pointer flex items-center justify-between gap-4 hover:bg-slate-800/40 ${
                        isSelected ? 'bg-indigo-950/30 border-l-4 border-indigo-500' : ''
                      }`}
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-sm font-semibold text-white">
                            {a.transaction_id}
                          </span>
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-indigo-300 border border-slate-700">
                            {a.payment_rail}
                          </span>
                          {getActionBadge(a.action)}
                        </div>
                        <div className="text-xs text-slate-400 flex items-center gap-3">
                          <span>Cust: <span className="font-mono text-slate-300">{a.customer_id}</span></span>
                          <span>•</span>
                          <span>{new Date(a.assessed_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                        </div>
                      </div>

                      <div className="text-right space-y-1">
                        <div className="text-base font-bold text-white">
                          ₹{a.amount.toLocaleString()}
                        </div>
                        <div className="flex items-center justify-end gap-2">
                          <span className={`px-2 py-0.5 rounded-full text-xs font-bold border ${getScoreColor(a.risk_score)}`}>
                            {a.risk_score} / 100
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Assessment Inspector (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          {selectedAssessment ? (
            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-5">
              <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                <div>
                  <div className="text-xs uppercase tracking-wider text-slate-400 font-medium">
                    Payment Risk Evaluation
                  </div>
                  <div className="text-lg font-bold text-white font-mono mt-0.5">
                    {selectedAssessment.transaction_id}
                  </div>
                </div>
                {getActionBadge(selectedAssessment.action)}
              </div>

              {/* Gauge Score Display */}
              <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-4 flex items-center justify-between">
                <div>
                  <div className="text-xs text-slate-400">Composite Fraud Score</div>
                  <div className="text-3xl font-extrabold text-white mt-1 flex items-baseline gap-1">
                    <span>{selectedAssessment.risk_score}</span>
                    <span className="text-sm font-medium text-slate-500">/ 100</span>
                  </div>
                  <div className="text-xs text-slate-400 mt-1">
                    Risk Tier: <span className="font-bold text-slate-200">{selectedAssessment.risk_level}</span>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-xs text-slate-400">Payment Amount</div>
                  <div className="text-xl font-bold text-emerald-400 mt-1">
                    ₹{selectedAssessment.amount.toLocaleString()}
                  </div>
                  <div className="text-xs text-slate-500 mt-0.5">
                    via <span className="font-semibold text-slate-300">{selectedAssessment.payment_rail}</span>
                  </div>
                </div>
              </div>

              {/* Summary Sentence */}
              <div className="text-xs text-slate-300 bg-slate-800/40 border border-slate-800 rounded-lg p-3">
                {selectedAssessment.summary}
              </div>

              {/* Explainable Signals Breakdown */}
              <div className="space-y-3">
                <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center justify-between">
                  <span>Triggered Risk Signals ({selectedAssessment.signals.length})</span>
                  <span>Impact</span>
                </div>

                {selectedAssessment.signals.length === 0 ? (
                  <div className="p-4 rounded-lg bg-emerald-950/20 border border-emerald-900/40 text-xs text-emerald-300 flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>No anomaly signals flagged. Clean domestic transaction.</span>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {selectedAssessment.signals.map((sig, idx) => (
                      <div
                        key={idx}
                        className="p-3 rounded-lg bg-slate-950/70 border border-slate-800 flex items-start justify-between gap-3"
                      >
                        <div className="space-y-1">
                          <div className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
                            {sig.category === 'Amount' && <TrendingUp className="w-3.5 h-3.5 text-amber-400" />}
                            {sig.category === 'Payee' && <UserCheck className="w-3.5 h-3.5 text-blue-400" />}
                            {sig.category === 'Geography' && <MapPin className="w-3.5 h-3.5 text-purple-400" />}
                            {sig.category === 'Velocity' && <Clock className="w-3.5 h-3.5 text-red-400" />}
                            {sig.category === 'CrossBorder' && <Globe className="w-3.5 h-3.5 text-teal-400" />}
                            {sig.category === 'Device' && <Smartphone className="w-3.5 h-3.5 text-rose-400" />}
                            {sig.signal_name}
                          </div>
                          <div className="text-[11px] text-slate-400 leading-snug">
                            {sig.description}
                          </div>
                        </div>
                        <span className="text-xs font-extrabold px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                          +{sig.points} pts
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Assessment Metadata */}
              <div className="pt-2 border-t border-slate-800/80 grid grid-cols-2 gap-3 text-xs">
                <div>
                  <span className="text-slate-500">Customer ID:</span>{' '}
                  <span className="font-mono text-slate-300">{selectedAssessment.customer_id}</span>
                </div>
                <div>
                  <span className="text-slate-500">Assessed At:</span>{' '}
                  <span className="text-slate-300">{new Date(selectedAssessment.assessed_at).toLocaleTimeString()}</span>
                </div>
              </div>
            </div>
          ) : (
            <div className="p-8 text-center text-slate-500 bg-slate-900/40 rounded-xl border border-slate-800">
              Select a payment to inspect full signal breakdown.
            </div>
          )}
        </div>
      </div>

      {/* Payment Simulation Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 space-y-5 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <CreditCard className="w-5 h-5 text-indigo-400" />
                Simulate Payment Transaction
              </h2>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-slate-400 hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            {/* Benchmark Preset Button */}
            <div className="p-3 bg-indigo-950/40 border border-indigo-800/50 rounded-xl flex items-center justify-between">
              <div className="text-xs text-indigo-200">
                <span className="font-semibold text-white">Benchmark Scenario:</span> ₹2,85,000 UPI transfer from Bengaluru to Mumbai
              </div>
              <button
                type="button"
                onClick={() => {
                  setFormData({
                    transaction_id: `TXN-UPI-285K-${Date.now().toString().slice(-4)}`,
                    customer_id: 'CUST-BLR-40291',
                    amount: 285000,
                    currency: 'INR',
                    payment_rail: 'UPI',
                    beneficiary_account: 'ACC-HDFC-882194',
                    beneficiary_name: 'Apex Digital Services',
                    is_new_beneficiary: true,
                    customer_home_city: 'Bengaluru',
                    transaction_city: 'Mumbai',
                    is_international: false,
                    has_device: true
                  });
                }}
                className="px-2.5 py-1 text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition"
              >
                Load Preset (45 Pts)
              </button>
            </div>

            <form onSubmit={handleAssessSubmit} className="space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-slate-400 block mb-1">Transaction ID</label>
                  <input
                    type="text"
                    required
                    value={formData.transaction_id}
                    onChange={(e) => setFormData({ ...formData, transaction_id: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200"
                  />
                </div>
                <div>
                  <label className="text-slate-400 block mb-1">Customer ID</label>
                  <input
                    type="text"
                    required
                    value={formData.customer_id}
                    onChange={(e) => setFormData({ ...formData, customer_id: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div className="col-span-2">
                  <label className="text-slate-400 block mb-1">Amount (₹)</label>
                  <input
                    type="number"
                    min="1"
                    required
                    value={formData.amount}
                    onChange={(e) => setFormData({ ...formData, amount: Number(e.target.value) })}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 font-mono"
                  />
                </div>
                <div>
                  <label className="text-slate-400 block mb-1">Payment Rail</label>
                  <select
                    value={formData.payment_rail}
                    onChange={(e) => setFormData({ ...formData, payment_rail: e.target.value })}
                    className="w-full px-2 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200"
                  >
                    <option value="UPI">UPI</option>
                    <option value="IMPS">IMPS</option>
                    <option value="NEFT">NEFT</option>
                    <option value="RTGS">RTGS</option>
                    <option value="CARD">CARD</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-slate-400 block mb-1">Customer Home City</label>
                  <input
                    type="text"
                    value={formData.customer_home_city}
                    onChange={(e) => setFormData({ ...formData, customer_home_city: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200"
                  />
                </div>
                <div>
                  <label className="text-slate-400 block mb-1">Transaction City</label>
                  <input
                    type="text"
                    value={formData.transaction_city}
                    onChange={(e) => setFormData({ ...formData, transaction_city: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200"
                  />
                </div>
              </div>

              {/* Toggles */}
              <div className="space-y-2 pt-2 border-t border-slate-800">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.is_new_beneficiary}
                    onChange={(e) => setFormData({ ...formData, is_new_beneficiary: e.target.checked })}
                    className="rounded bg-slate-950 border-slate-800 text-indigo-600 focus:ring-0"
                  />
                  <span className="text-slate-300">New Beneficiary (+15 points)</span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.is_international}
                    onChange={(e) => setFormData({ ...formData, is_international: e.target.checked })}
                    className="rounded bg-slate-950 border-slate-800 text-indigo-600 focus:ring-0"
                  />
                  <span className="text-slate-300">International / Foreign Transfer (+20 points)</span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={!formData.has_device}
                    onChange={(e) => setFormData({ ...formData, has_device: !e.target.checked })}
                    className="rounded bg-slate-950 border-slate-800 text-indigo-600 focus:ring-0"
                  />
                  <span className="text-slate-300">Missing Device Context (+15 points)</span>
                </label>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 font-semibold text-white shadow-lg shadow-indigo-600/20"
                >
                  Assess Payment
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
export default PaymentFraudPage;

