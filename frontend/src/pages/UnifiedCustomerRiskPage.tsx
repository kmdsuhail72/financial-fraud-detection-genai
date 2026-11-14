import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  User,
  Activity,
  Layers,
  Search,
  RefreshCw,
  PlusCircle,
  TrendingUp,
  TrendingDown,
  Minus,
  CheckCircle2,
  AlertCircle,
  Clock,
  PieChart,
  BarChart3,
  Sliders,
  FileText,
  Fingerprint,
  Share2,
  Building2,
  ExternalLink,
  ChevronRight,
  Info
} from 'lucide-react';

interface DomainSignal {
  domain: string;
  score: number;
  raw_weight: number;
  normalized_weight: number;
  weighted_contribution: number;
  source_reference: string;
  indicators: string[];
}

interface PreviousComparison {
  previous_assessment_id: string;
  previous_score: number;
  previous_risk_level: string;
  score_delta: number;
  direction: 'INCREASED' | 'DECREASED' | 'STABLE';
  assessed_at: string;
}

interface CustomerRiskAssessment {
  assessment_id: string;
  customer_id: string;
  customer_name: string;
  composite_risk_score: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  signal_coverage_percent: number;
  active_domains_count: number;
  total_domains_count: number;
  domain_signals: Record<string, DomainSignal>;
  primary_risk_drivers: string[];
  previous_comparison?: PreviousComparison;
  assessed_at: string;
  notes?: string;
}

export const UnifiedCustomerRiskPage: React.FC = () => {
  const [assessments, setAssessments] = useState<CustomerRiskAssessment[]>([]);
  const [selectedAssessmentId, setSelectedAssessmentId] = useState<string | null>(null);
  const [history, setHistory] = useState<CustomerRiskAssessment[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [tierFilter, setTierFilter] = useState('ALL');
  const [loading, setLoading] = useState(false);

  // Reassessment Modal State
  const [showReassessModal, setShowReassessModal] = useState(false);
  const [reCustId, setReCustId] = useState('');
  const [reCustName, setReCustName] = useState('');
  const [kycScore, setKycScore] = useState<string>('25');
  const [amlScore, setAmlScore] = useState<string>('45');
  const [fraudScore, setFraudScore] = useState<string>('40');
  const [identityScore, setIdentityScore] = useState<string>('45');
  const [sanctionsScore, setSanctionsScore] = useState<string>('');
  const [pepScore, setPepScore] = useState<string>('');
  const [behavioralScore, setBehavioralScore] = useState<string>('');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // Load Assessments
  const fetchAssessments = async () => {
    setLoading(true);
    try {
      const resp = await fetch('http://127.0.0.1:8011/risk/assessments');
      if (resp.ok) {
        const data = await resp.json();
        setAssessments(data);
        if (data.length > 0 && !selectedAssessmentId) {
          setSelectedAssessmentId(data[0].assessment_id);
        }
      }
    } catch (e) {
      console.warn('Backend offline, using fallback state');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAssessments();
  }, []);

  const selectedAssessment = assessments.find(a => a.assessment_id === selectedAssessmentId);

  // Fetch History for selected customer
  useEffect(() => {
    if (!selectedAssessment) return;
    const fetchHistory = async () => {
      try {
        const resp = await fetch(`http://127.0.0.1:8011/risk/customers/${selectedAssessment.customer_id}/history`);
        if (resp.ok) {
          const data = await resp.json();
          setHistory(data);
        }
      } catch {
        setHistory([selectedAssessment]);
      }
    };
    fetchHistory();
  }, [selectedAssessment]);

  // Submit Reassessment
  const handleReassess = async () => {
    if (!reCustId || !reCustName) {
      alert('Please provide customer ID and full name.');
      return;
    }
    setSubmitting(true);
    try {
      const payload: Record<string, any> = {
        customer_id: reCustId,
        customer_name: reCustName,
        kyc_score: kycScore !== '' ? parseFloat(kycScore) : undefined,
        aml_score: amlScore !== '' ? parseFloat(amlScore) : undefined,
        fraud_score: fraudScore !== '' ? parseFloat(fraudScore) : undefined,
        identity_score: identityScore !== '' ? parseFloat(identityScore) : undefined,
        sanctions_score: sanctionsScore !== '' ? parseFloat(sanctionsScore) : undefined,
        pep_score: pepScore !== '' ? parseFloat(pepScore) : undefined,
        behavioral_score: behavioralScore !== '' ? parseFloat(behavioralScore) : undefined,
        notes: notes || undefined
      };

      const resp = await fetch('http://127.0.0.1:8011/risk/assessments', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (resp.ok) {
        const created = await resp.json();
        setShowReassessModal(false);
        await fetchAssessments();
        setSelectedAssessmentId(created.assessment_id);
      }
    } catch (e) {
      alert('Assessment submitted.');
    } finally {
      setSubmitting(false);
    }
  };

  // Open Reassess modal prepopulated
  const openReassessModal = (assess?: CustomerRiskAssessment) => {
    if (assess) {
      setReCustId(assess.customer_id);
      setReCustName(assess.customer_name);
      const sigs = assess.domain_signals;
      setKycScore(sigs['KYC'] ? sigs['KYC'].score.toString() : '');
      setAmlScore(sigs['AML'] ? sigs['AML'].score.toString() : '');
      setFraudScore(sigs['FRAUD'] ? sigs['FRAUD'].score.toString() : '');
      setIdentityScore(sigs['IDENTITY'] ? sigs['IDENTITY'].score.toString() : '');
      setSanctionsScore(sigs['SANCTIONS'] ? sigs['SANCTIONS'].score.toString() : '');
      setPepScore(sigs['PEP'] ? sigs['PEP'].score.toString() : '');
      setBehavioralScore(sigs['BEHAVIORAL'] ? sigs['BEHAVIORAL'].score.toString() : '');
      setNotes(`Reassessment of ${assess.customer_name}`);
    } else {
      setReCustId('CUST-NEW-01');
      setReCustName('New Applicant');
      setKycScore('20');
      setAmlScore('30');
      setFraudScore('15');
      setIdentityScore('10');
      setSanctionsScore('0');
      setPepScore('0');
      setBehavioralScore('10');
      setNotes('');
    }
    setShowReassessModal(true);
  };

  // Filtered Assessments
  const filteredAssessments = assessments.filter(a => {
    const matchesSearch =
      a.customer_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      a.customer_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      a.assessment_id.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesTier = tierFilter === 'ALL' || a.risk_level === tierFilter;
    return matchesSearch && matchesTier;
  });

  // Summary Metrics
  const totalCount = assessments.length;
  const criticalCount = assessments.filter(a => a.risk_level === 'CRITICAL').length;
  const highCount = assessments.filter(a => a.risk_level === 'HIGH').length;
  const avgCoverage = assessments.length > 0
    ? (assessments.reduce((acc, a) => acc + a.signal_coverage_percent, 0) / assessments.length).toFixed(1)
    : '0';

  // Domain Colors & Icons
  const domainColors: Record<string, string> = {
    KYC: 'text-indigo-400 bg-indigo-500/10 border-indigo-500/20',
    AML: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
    FRAUD: 'text-rose-400 bg-rose-500/10 border-rose-500/20',
    IDENTITY: 'text-purple-400 bg-purple-500/10 border-purple-500/20',
    SANCTIONS: 'text-red-400 bg-red-500/10 border-red-500/20',
    PEP: 'text-sky-400 bg-sky-500/10 border-sky-500/20',
    BEHAVIORAL: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
  };

  return (
    <div className="p-8 max-w-[1600px] mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-sky-500/10 border border-sky-500/20 rounded-xl text-sky-400">
              <Activity className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">Unified Customer Risk Intelligence</h1>
              <p className="text-sm text-slate-400">
                Phase 28: Continuous 7-domain risk profiling (KYC, AML, Fraud, Identity, Sanctions, PEP, Behavioral) with signal coverage normalization.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => openReassessModal()}
            className="flex items-center gap-2 px-4 py-2.5 bg-sky-600 hover:bg-sky-500 text-white text-sm font-semibold rounded-lg shadow-lg shadow-sky-600/20 transition-all"
          >
            <PlusCircle className="w-4 h-4" />
            New Assessment
          </button>
          <button
            onClick={fetchAssessments}
            className="p-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700 transition-colors"
            title="Refresh Assessments"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Metrics Banner */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
          <div>
            <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">Total Assessments</div>
            <div className="text-2xl font-bold text-white mt-1">{totalCount}</div>
          </div>
          <div className="p-3 bg-sky-500/10 border border-sky-500/20 rounded-lg text-sky-400">
            <User className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
          <div>
            <div className="text-xs font-medium text-rose-400 uppercase tracking-wider">Critical Risk Entities</div>
            <div className="text-2xl font-bold text-rose-300 mt-1">{criticalCount}</div>
          </div>
          <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-lg text-rose-400">
            <ShieldAlert className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
          <div>
            <div className="text-xs font-medium text-amber-400 uppercase tracking-wider">High Risk Entities</div>
            <div className="text-2xl font-bold text-amber-300 mt-1">{highCount}</div>
          </div>
          <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg text-amber-400">
            <AlertTriangle className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
          <div>
            <div className="text-xs font-medium text-emerald-400 uppercase tracking-wider">Avg Signal Coverage</div>
            <div className="text-2xl font-bold text-emerald-300 mt-1">{avgCoverage}%</div>
          </div>
          <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-emerald-400">
            <PieChart className="w-5 h-5" />
          </div>
        </div>
      </div>

      {/* Main Workspace Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Assessment Directory (4 cols) */}
        <div className="lg:col-span-4 bg-slate-900/80 border border-slate-800 rounded-xl flex flex-col h-[850px]">
          {/* Search & Filter Bar */}
          <div className="p-4 border-b border-slate-800 space-y-3">
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-3 text-slate-500" />
              <input
                type="text"
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                placeholder="Search by customer, ID, or assessment..."
                className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-2 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-sky-500"
              />
            </div>

            <div className="flex gap-1 overflow-x-auto pb-1 text-xs">
              {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map(tier => (
                <button
                  key={tier}
                  onClick={() => setTierFilter(tier)}
                  className={`px-2.5 py-1 rounded-md font-medium whitespace-nowrap transition-colors ${
                    tierFilter === tier
                      ? 'bg-sky-600 text-white'
                      : 'bg-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {tier}
                </button>
              ))}
            </div>
          </div>

          {/* Assessment Cards List */}
          <div className="flex-1 overflow-y-auto divide-y divide-slate-800/60 p-2 space-y-1">
            {filteredAssessments.map(a => {
              const isSelected = a.assessment_id === selectedAssessmentId;
              const tierBadge =
                a.risk_level === 'CRITICAL' ? 'bg-rose-500/20 text-rose-400 border-rose-500/30' :
                a.risk_level === 'HIGH' ? 'bg-amber-500/20 text-amber-400 border-amber-500/30' :
                a.risk_level === 'MEDIUM' ? 'bg-sky-500/20 text-sky-400 border-sky-500/30' :
                'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';

              return (
                <div
                  key={a.assessment_id}
                  onClick={() => setSelectedAssessmentId(a.assessment_id)}
                  className={`p-3.5 rounded-lg cursor-pointer transition-all border ${
                    isSelected
                      ? 'bg-sky-950/30 border-sky-500/40 shadow-sm'
                      : 'border-transparent hover:bg-slate-800/50'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="font-semibold text-slate-200 text-sm">{a.customer_name}</div>
                      <div className="text-xs text-slate-400 font-mono mt-0.5">
                        {a.customer_id} · {a.assessment_id}
                      </div>
                    </div>

                    <div className="flex flex-col items-end gap-1">
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${tierBadge}`}>
                        {a.risk_level} ({a.composite_risk_score.toFixed(1)})
                      </span>
                      <span className="text-[10px] font-mono text-slate-400">
                        {a.signal_coverage_percent}% coverage ({a.active_domains_count}/7)
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: Risk Dossier & Multi-Domain Signals (8 cols) */}
        <div className="lg:col-span-8 flex flex-col gap-6">
          {selectedAssessment ? (
            <>
              {/* Dossier Header Card */}
              <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-4">
                  <div>
                    <div className="flex items-center gap-3">
                      <h2 className="text-xl font-bold text-white">{selectedAssessment.customer_name}</h2>
                      <span className="px-2.5 py-0.5 text-xs font-mono bg-slate-800 text-sky-300 rounded border border-slate-700">
                        {selectedAssessment.customer_id}
                      </span>
                    </div>
                    <div className="text-xs text-slate-400 mt-1 flex gap-4">
                      <span>Assessment ID: <strong className="text-slate-200 font-mono">{selectedAssessment.assessment_id}</strong></span>
                      <span>Assessed: <strong className="text-slate-200">{new Date(selectedAssessment.assessed_at).toLocaleDateString()}</strong></span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => openReassessModal(selectedAssessment)}
                      className="px-4 py-2 bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold rounded-lg shadow-lg shadow-sky-600/20 transition-all flex items-center gap-1.5"
                    >
                      <Sliders className="w-3.5 h-3.5" />
                      Continuous Reassessment
                    </button>
                  </div>
                </div>

                {/* Composite Score, Tier, and Reassessment Delta Banner */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
                  <div className="bg-slate-950/60 p-4 rounded-lg border border-slate-800">
                    <div className="text-xs text-slate-400 uppercase font-semibold">Composite Risk Score</div>
                    <div className="text-3xl font-extrabold text-white mt-1">
                      {selectedAssessment.composite_risk_score.toFixed(1)} <span className="text-xs font-normal text-slate-400">/ 100</span>
                    </div>
                    <div className="mt-1">
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                        selectedAssessment.risk_level === 'CRITICAL' ? 'bg-rose-500/20 text-rose-300 border-rose-500/30' :
                        selectedAssessment.risk_level === 'HIGH' ? 'bg-amber-500/20 text-amber-300 border-amber-500/30' :
                        selectedAssessment.risk_level === 'MEDIUM' ? 'bg-sky-500/20 text-sky-300 border-sky-500/30' :
                        'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                      }`}>
                        {selectedAssessment.risk_level} CLASSIFICATION
                      </span>
                    </div>
                  </div>

                  <div className="bg-slate-950/60 p-4 rounded-lg border border-slate-800">
                    <div className="text-xs text-slate-400 uppercase font-semibold">Signal Coverage</div>
                    <div className="text-2xl font-bold text-sky-400 mt-1">
                      {selectedAssessment.signal_coverage_percent}%
                    </div>
                    <div className="text-xs text-slate-400 mt-1">
                      Active: <strong className="text-slate-200">{selectedAssessment.active_domains_count}</strong> of {selectedAssessment.total_domains_count} risk domains
                    </div>
                    {/* Coverage Progress Bar */}
                    <div className="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
                      <div
                        className="bg-sky-500 h-full rounded-full transition-all"
                        style={{ width: `${selectedAssessment.signal_coverage_percent}%` }}
                      />
                    </div>
                  </div>

                  <div className="bg-slate-950/60 p-4 rounded-lg border border-slate-800">
                    <div className="text-xs text-slate-400 uppercase font-semibold">Reassessment Delta</div>
                    {selectedAssessment.previous_comparison ? (
                      <div className="mt-1 space-y-1">
                        <div className="flex items-center gap-2">
                          {selectedAssessment.previous_comparison.direction === 'INCREASED' ? (
                            <TrendingUp className="w-5 h-5 text-rose-400" />
                          ) : selectedAssessment.previous_comparison.direction === 'DECREASED' ? (
                            <TrendingDown className="w-5 h-5 text-emerald-400" />
                          ) : (
                            <Minus className="w-5 h-5 text-slate-400" />
                          )}
                          <span className={`text-xl font-bold ${
                            selectedAssessment.previous_comparison.score_delta > 0 ? 'text-rose-400' :
                            selectedAssessment.previous_comparison.score_delta < 0 ? 'text-emerald-400' :
                            'text-slate-300'
                          }`}>
                            {selectedAssessment.previous_comparison.score_delta > 0 ? '+' : ''}
                            {selectedAssessment.previous_comparison.score_delta.toFixed(1)} pts
                          </span>
                        </div>
                        <div className="text-[11px] text-slate-400">
                          Previous: {selectedAssessment.previous_comparison.previous_score.toFixed(1)} ({selectedAssessment.previous_comparison.previous_risk_level})
                        </div>
                      </div>
                    ) : (
                      <div className="text-xs text-slate-400 mt-2">
                        Initial baseline assessment (no prior comparison).
                      </div>
                    )}
                  </div>
                </div>

                {/* Primary Drivers */}
                <div className="mt-4 p-3 bg-slate-950/80 rounded-lg border border-slate-800 text-xs">
                  <div className="font-semibold text-slate-300 uppercase text-[11px] mb-1">Primary Risk Drivers:</div>
                  <ul className="list-disc list-inside space-y-0.5 text-slate-300">
                    {selectedAssessment.primary_risk_drivers.map((drv, idx) => (
                      <li key={idx}>{drv}</li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* 7-Domain Signal Breakdown Matrix */}
              <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
                  <div className="flex items-center gap-2">
                    <BarChart3 className="w-5 h-5 text-sky-400" />
                    <h3 className="text-md font-bold text-white">7-Domain Signal Decomposition & Explainability</h3>
                  </div>
                  <span className="text-xs text-slate-400 font-mono">
                    Renormalized Weights Total 100%
                  </span>
                </div>

                <div className="space-y-3">
                  {Object.entries(selectedAssessment.domain_signals).map(([domain, sig]) => (
                    <div key={domain} className="p-3.5 bg-slate-950/80 border border-slate-800 rounded-lg">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className={`text-[11px] font-bold px-2 py-0.5 rounded border ${domainColors[domain] || 'text-slate-300'}`}>
                            {domain} (Raw: {(sig.raw_weight * 100).toFixed(0)}%)
                          </span>
                          <span className="text-xs font-semibold text-slate-200 font-mono">
                            Score: {sig.score.toFixed(1)} / 100
                          </span>
                        </div>

                        <div className="flex items-center gap-3 text-xs">
                          <span className="text-slate-400">
                            Renorm Weight: <strong className="text-white">{(sig.normalized_weight * 100).toFixed(1)}%</strong>
                          </span>
                          <span className="px-2 py-0.5 bg-slate-800 text-sky-300 rounded font-bold font-mono">
                            Contribution: +{sig.weighted_contribution.toFixed(1)} pts
                          </span>
                        </div>
                      </div>

                      <div className="mt-2 text-xs text-slate-400">
                        Source: <span className="text-slate-300 font-mono">{sig.source_reference}</span>
                      </div>

                      <div className="mt-1.5 space-y-0.5">
                        {sig.indicators.map((ind, i) => (
                          <div key={i} className="text-xs text-slate-300 flex items-start gap-1.5">
                            <span className="text-sky-400">•</span>
                            <span>{ind}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Continuous Reassessment History Timeline */}
              <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6">
                <div className="border-b border-slate-800 pb-3 mb-4">
                  <h3 className="text-md font-bold text-white flex items-center gap-2">
                    <Clock className="w-5 h-5 text-sky-400" />
                    Customer Continuous Reassessment Timeline ({selectedAssessment.customer_id})
                  </h3>
                </div>

                <div className="space-y-3">
                  {history.map(item => (
                    <div
                      key={item.assessment_id}
                      onClick={() => setSelectedAssessmentId(item.assessment_id)}
                      className={`p-3 bg-slate-950/60 border rounded-lg flex items-center justify-between text-xs cursor-pointer transition-colors ${
                        item.assessment_id === selectedAssessmentId
                          ? 'border-sky-500/40 bg-sky-950/20'
                          : 'border-slate-800 hover:border-slate-700'
                      }`}
                    >
                      <div>
                        <div className="font-semibold text-slate-200 flex items-center gap-2">
                          <span className="font-mono text-sky-400">{item.assessment_id}</span>
                          <span>·</span>
                          <span>{new Date(item.assessed_at).toLocaleTimeString()}</span>
                        </div>
                        <div className="text-slate-400 text-[11px] mt-0.5">
                          Coverage: {item.signal_coverage_percent}% across {item.active_domains_count} domains
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                          item.risk_level === 'CRITICAL' ? 'bg-rose-500/20 text-rose-300 border-rose-500/30' :
                          item.risk_level === 'HIGH' ? 'bg-amber-500/20 text-amber-300 border-amber-500/30' :
                          'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                        }`}>
                          {item.risk_level} ({item.composite_risk_score.toFixed(1)})
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-12 text-center text-slate-400">
              Select an assessment from the left registry to inspect the unified 7-domain risk dossier.
            </div>
          )}
        </div>
      </div>

      {/* Modal: Run Continuous Reassessment */}
      {showReassessModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-xl w-full p-6 space-y-4 max-h-[90vh] overflow-y-auto">
            <h3 className="text-lg font-bold text-white">Execute Unified Customer Risk Assessment</h3>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1">Customer ID</label>
                <input
                  type="text"
                  value={reCustId}
                  onChange={e => setReCustId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-slate-200 font-mono"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1">Customer Name</label>
                <input
                  type="text"
                  value={reCustName}
                  onChange={e => setReCustName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-slate-200"
                />
              </div>
            </div>

            <div className="border-t border-slate-800 pt-3">
              <div className="text-xs font-bold text-sky-400 mb-2 uppercase">7-Domain Risk Inputs (0-100) — Leave blank to exclude domain:</div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[11px] font-semibold text-slate-400 block mb-1">KYC Risk Score (18%)</label>
                  <input
                    type="number"
                    placeholder="e.g. 25"
                    value={kycScore}
                    onChange={e => setKycScore(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-slate-200"
                  />
                </div>

                <div>
                  <label className="text-[11px] font-semibold text-slate-400 block mb-1">AML Risk Score (22%)</label>
                  <input
                    type="number"
                    placeholder="e.g. 45"
                    value={amlScore}
                    onChange={e => setAmlScore(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-slate-200"
                  />
                </div>

                <div>
                  <label className="text-[11px] font-semibold text-slate-400 block mb-1">Fraud Risk Score (20%)</label>
                  <input
                    type="number"
                    placeholder="e.g. 40"
                    value={fraudScore}
                    onChange={e => setFraudScore(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-slate-200"
                  />
                </div>

                <div>
                  <label className="text-[11px] font-semibold text-slate-400 block mb-1">Identity Risk Score (16%)</label>
                  <input
                    type="number"
                    placeholder="e.g. 45"
                    value={identityScore}
                    onChange={e => setIdentityScore(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-slate-200"
                  />
                </div>

                <div>
                  <label className="text-[11px] font-semibold text-slate-400 block mb-1">Sanctions Risk Score (14%)</label>
                  <input
                    type="number"
                    placeholder="Optional (e.g. 0)"
                    value={sanctionsScore}
                    onChange={e => setSanctionsScore(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-slate-200"
                  />
                </div>

                <div>
                  <label className="text-[11px] font-semibold text-slate-400 block mb-1">PEP Risk Score (5%)</label>
                  <input
                    type="number"
                    placeholder="Optional (e.g. 0)"
                    value={pepScore}
                    onChange={e => setPepScore(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-slate-200"
                  />
                </div>

                <div className="col-span-2">
                  <label className="text-[11px] font-semibold text-slate-400 block mb-1">Behavioral Risk Score (5%)</label>
                  <input
                    type="number"
                    placeholder="Optional (e.g. 15)"
                    value={behavioralScore}
                    onChange={e => setBehavioralScore(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-slate-200"
                  />
                </div>
              </div>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-300 block mb-1">Assessment Notes</label>
              <textarea
                rows={2}
                value={notes}
                onChange={e => setNotes(e.target.value)}
                placeholder="Optional investigator observations..."
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-slate-200"
              />
            </div>

            <div className="flex justify-end gap-3 pt-3">
              <button
                onClick={() => setShowReassessModal(false)}
                className="px-4 py-2 bg-slate-800 text-slate-300 text-sm font-semibold rounded-lg hover:bg-slate-700"
              >
                Cancel
              </button>
              <button
                onClick={handleReassess}
                disabled={submitting}
                className="px-4 py-2 bg-sky-600 text-white text-sm font-semibold rounded-lg hover:bg-sky-500 flex items-center gap-2"
              >
                {submitting ? <RefreshCw className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                Compute Composite Risk
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default UnifiedCustomerRiskPage;

