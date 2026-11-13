import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  Award,
  CheckCircle2,
  AlertTriangle,
  AlertOctagon,
  Clock,
  Layers,
  Search,
  Filter,
  RefreshCw,
  FileText,
  ExternalLink,
  ChevronRight,
  TrendingUp,
  UserCheck,
  PlusCircle,
  HelpCircle
} from 'lucide-react';

interface FrameworkMapping {
  framework: string;
  clause_or_requirement: string;
  description: string;
}

interface GovernanceControl {
  control_id: string;
  name: string;
  domain: string;
  description: string;
  framework_mappings: FrameworkMapping[];
  effectiveness: 'EFFECTIVE' | 'PARTIALLY_EFFECTIVE' | 'INEFFECTIVE' | 'NOT_APPLICABLE';
  evidence_references: string[];
  assessor_rationale?: string;
  last_assessed_at?: string;
  assessed_by?: string;
}

interface GovernanceFinding {
  finding_id: string;
  control_id: string;
  title: string;
  description: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  status: 'OPEN' | 'IN_PROGRESS' | 'REMEDIATED' | 'VERIFIED';
  owner: string;
  due_date: string;
  remediation_notes?: string;
}

interface ReadinessReport {
  overall_readiness_pct: number;
  effective_controls_count: number;
  partially_effective_count: number;
  ineffective_count: number;
  not_applicable_count: number;
  total_controls: number;
  framework_breakdown: Record<string, number>;
  open_findings_count: number;
  critical_findings_count: number;
  controls: GovernanceControl[];
  findings: GovernanceFinding[];
}

interface AuditEvent {
  event_id: string;
  timestamp: string;
  event_type: string;
  actor: string;
  entity_type: string;
  entity_id: string;
  details: Record<string, any>;
}

export const ComplianceGovernancePage: React.FC = () => {
  const [readiness, setReadiness] = useState<ReadinessReport | null>(null);
  const [controls, setControls] = useState<GovernanceControl[]>([]);
  const [findings, setFindings] = useState<GovernanceFinding[]>([]);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  // Filters
  const [effectivenessFilter, setEffectivenessFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedControl, setSelectedControl] = useState<GovernanceControl | null>(null);

  // Assessment form state
  const [assessStatus, setAssessStatus] = useState<string>('EFFECTIVE');
  const [assessRationale, setAssessRationale] = useState<string>('');
  const [assessEvidence, setAssessEvidence] = useState<string>('');

  const fetchGovernanceData = async () => {
    setLoading(true);
    try {
      const [readRes, ctrlRes, findRes, audRes] = await Promise.all([
        fetch('http://127.0.0.1:8010/compliance/governance/readiness'),
        fetch('http://127.0.0.1:8010/compliance/governance/controls'),
        fetch('http://127.0.0.1:8010/compliance/governance/findings'),
        fetch('http://127.0.0.1:8010/compliance/governance/audit-trail')
      ]);

      if (readRes.ok) setReadiness(await readRes.json());
      if (ctrlRes.ok) {
        const cData = await ctrlRes.json();
        setControls(cData);
        if (cData.length > 0 && !selectedControl) setSelectedControl(cData[0]);
      }
      if (findRes.ok) setFindings(await findRes.json());
      if (audRes.ok) setAuditEvents(await audRes.json());
    } catch {
      console.warn('Backend unavailable, using initial state');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGovernanceData();
  }, []);

  const handleAssessControl = async (controlId: string) => {
    if (!assessRationale.trim()) return;
    try {
      const payload = {
        effectiveness: assessStatus,
        assessor_rationale: assessRationale,
        evidence_references: assessEvidence ? assessEvidence.split(',').map((s) => s.trim()) : [],
        assessor: 'lead.compliance.auditor@finguard.internal'
      };
      const res = await fetch(`http://127.0.0.1:8010/compliance/governance/controls/${controlId}/assess`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        setAssessRationale('');
        setAssessEvidence('');
        fetchGovernanceData();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const getEffectivenessBadge = (eff: string) => {
    switch (eff) {
      case 'EFFECTIVE':
        return 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40';
      case 'PARTIALLY_EFFECTIVE':
        return 'bg-amber-500/20 text-amber-400 border border-amber-500/40';
      case 'INEFFECTIVE':
        return 'bg-rose-500/20 text-rose-400 border border-rose-500/40';
      default:
        return 'bg-slate-500/20 text-slate-400 border border-slate-500/40';
    }
  };

  const getSeverityBadge = (sev: string) => {
    switch (sev) {
      case 'CRITICAL':
        return 'bg-rose-500/20 text-rose-400 border border-rose-500/40 font-bold';
      case 'HIGH':
        return 'bg-orange-500/20 text-orange-400 border border-orange-500/40';
      case 'MEDIUM':
        return 'bg-amber-500/20 text-amber-400 border border-amber-500/40';
      default:
        return 'bg-slate-500/20 text-slate-400 border border-slate-500/40';
    }
  };

  const filteredControls = controls.filter((c) => {
    if (effectivenessFilter !== 'ALL' && c.effectiveness !== effectivenessFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        c.control_id.toLowerCase().includes(q) ||
        c.name.toLowerCase().includes(q) ||
        c.domain.toLowerCase().includes(q)
      );
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
              Regulatory Compliance & Audit Governance
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-mono bg-indigo-500/10 text-indigo-400 border border-indigo-500/30">
              Phase 23
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Automated control catalogue, framework mappings (SOC 2, ISO 27001, PCI DSS), deficiency tracking, and audit-readiness KPIs.
          </p>
        </div>
        <button
          onClick={fetchGovernanceData}
          className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg border border-slate-700 transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh Status
        </button>
      </div>

      {/* Audit Readiness KPIs Bar */}
      {readiness && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl flex items-center justify-between">
            <div>
              <span className="text-xs text-slate-400 block">Audit Readiness</span>
              <p className="text-2xl font-extrabold text-indigo-400">{readiness.overall_readiness_pct}%</p>
            </div>
            <Award className="w-8 h-8 text-indigo-400/50" />
          </div>

          <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl">
            <span className="text-xs text-slate-400 block">SOC 2 Type II</span>
            <p className="text-xl font-bold text-slate-100">{readiness.framework_breakdown['SOC2'] || 0}%</p>
            <span className="text-[10px] text-emerald-400 font-mono">Mapped & Assessed</span>
          </div>

          <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl">
            <span className="text-xs text-slate-400 block">ISO 27001:2022</span>
            <p className="text-xl font-bold text-slate-100">{readiness.framework_breakdown['ISO27001'] || 0}%</p>
            <span className="text-[10px] text-emerald-400 font-mono">Annex A Controls</span>
          </div>

          <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl">
            <span className="text-xs text-slate-400 block">PCI DSS v4.0</span>
            <p className="text-xl font-bold text-slate-100">{readiness.framework_breakdown['PCI_DSS'] || 0}%</p>
            <span className="text-[10px] text-emerald-400 font-mono">Cardholder Data Scope</span>
          </div>

          <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl">
            <span className="text-xs text-rose-400 block">Open Deficiencies</span>
            <p className="text-xl font-bold text-rose-300">
              {readiness.open_findings_count} <span className="text-xs font-normal text-slate-400">({readiness.critical_findings_count} crit)</span>
            </p>
            <span className="text-[10px] text-rose-400 font-mono">Active Remediation</span>
          </div>
        </div>
      )}

      {/* Main Grid: Control Catalogue on Left, Assessment & Details on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: 10 Starter Controls */}
        <div className="lg:col-span-7 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-900/40 p-3 rounded-xl border border-slate-800">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="w-4 h-4 text-slate-400 absolute left-2.5 top-2.5" />
              <input
                type="text"
                placeholder="Search controls by ID, name, or domain..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200"
              />
            </div>
            <select
              value={effectivenessFilter}
              onChange={(e) => setEffectivenessFilter(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-300"
            >
              <option value="ALL">All Statuses</option>
              <option value="EFFECTIVE">Effective</option>
              <option value="PARTIALLY_EFFECTIVE">Partially Effective</option>
              <option value="INEFFECTIVE">Ineffective</option>
            </select>
          </div>

          <div className="space-y-2">
            {filteredControls.map((c) => {
              const isSelected = selectedControl?.control_id === c.control_id;
              return (
                <div
                  key={c.control_id}
                  onClick={() => setSelectedControl(c)}
                  className={`p-3.5 rounded-xl border transition cursor-pointer ${
                    isSelected
                      ? 'bg-slate-800/80 border-indigo-500 shadow-md'
                      : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-indigo-400">{c.control_id}</span>
                      <span className="text-xs text-slate-400">({c.domain})</span>
                    </div>
                    <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${getEffectivenessBadge(c.effectiveness)}`}>
                      {c.effectiveness.replace('_', ' ')}
                    </span>
                  </div>

                  <h3 className="text-sm font-semibold text-slate-100">{c.name}</h3>

                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {c.framework_mappings.map((m, i) => (
                      <span key={i} className="px-2 py-0.5 bg-slate-950 border border-slate-800 rounded text-[10px] font-mono text-slate-300">
                        {m.framework} {m.clause_or_requirement}
                      </span>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: Selected Control Assessment & Findings */}
        <div className="lg:col-span-5 space-y-4">
          {selectedControl ? (
            <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 space-y-4">
              <div className="border-b border-slate-800 pb-3">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs text-indigo-400 font-bold">{selectedControl.control_id}</span>
                  <span className={`px-2 py-0.5 rounded text-xs ${getEffectivenessBadge(selectedControl.effectiveness)}`}>
                    {selectedControl.effectiveness.replace('_', ' ')}
                  </span>
                </div>
                <h3 className="text-base font-bold text-slate-100 mt-1">{selectedControl.name}</h3>
                <p className="text-xs text-slate-400 mt-1 leading-relaxed">{selectedControl.description}</p>
              </div>

              {/* Framework Requirement Details */}
              <div className="space-y-2">
                <span className="text-xs font-semibold text-slate-300 block">Framework Clause Mappings</span>
                <div className="space-y-1.5 max-h-32 overflow-y-auto">
                  {selectedControl.framework_mappings.map((m, i) => (
                    <div key={i} className="bg-slate-950 p-2 rounded-lg border border-slate-850 text-xs">
                      <span className="font-mono text-indigo-300 font-bold">{m.framework} {m.clause_or_requirement}</span>
                      <p className="text-[11px] text-slate-400 mt-0.5">{m.description}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Assessment Rationale & Evidence References */}
              <div className="bg-slate-950 p-3 rounded-lg border border-slate-850 space-y-2 text-xs">
                <div>
                  <span className="text-slate-400 block font-semibold">Assessor Rationale:</span>
                  <p className="text-slate-200 mt-0.5 italic">{selectedControl.assessor_rationale || 'Not formally assessed yet.'}</p>
                </div>
                <div>
                  <span className="text-slate-400 block font-semibold">Attached Evidence References:</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {selectedControl.evidence_references.map((ref, i) => (
                      <span key={i} className="px-2 py-0.5 bg-slate-900 border border-slate-800 rounded font-mono text-[10px] text-purple-400">
                        {ref}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Formal Assessment Submission Form */}
              <div className="border-t border-slate-800 pt-3 space-y-2.5">
                <span className="text-xs font-semibold text-slate-200 block">Submit Auditor Assessment</span>
                <div className="grid grid-cols-2 gap-2">
                  <select
                    value={assessStatus}
                    onChange={(e) => setAssessStatus(e.target.value)}
                    className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1 text-xs text-slate-200"
                  >
                    <option value="EFFECTIVE">Effective</option>
                    <option value="PARTIALLY_EFFECTIVE">Partially Effective</option>
                    <option value="INEFFECTIVE">Ineffective</option>
                    <option value="NOT_APPLICABLE">Not Applicable</option>
                  </select>
                  <input
                    type="text"
                    placeholder="Evidence refs (comma-separated)"
                    value={assessEvidence}
                    onChange={(e) => setAssessEvidence(e.target.value)}
                    className="bg-slate-950 border border-slate-800 rounded-lg px-2 py-1 text-xs text-slate-200 font-mono"
                  />
                </div>
                <textarea
                  rows={2}
                  placeholder="Enter auditor evaluation and compliance verification rationale..."
                  value={assessRationale}
                  onChange={(e) => setAssessRationale(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-slate-200"
                />
                <button
                  onClick={() => handleAssessControl(selectedControl.control_id)}
                  className="w-full py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold transition"
                >
                  Record Formal Assessment
                </button>
              </div>

              {/* Linked Deficiencies / Findings */}
              <div className="border-t border-slate-800 pt-3 space-y-2">
                <span className="text-xs font-semibold text-slate-200 block">Linked Findings ({findings.filter(f => f.control_id === selectedControl.control_id).length})</span>
                <div className="space-y-1.5 max-h-28 overflow-y-auto">
                  {findings
                    .filter((f) => f.control_id === selectedControl.control_id)
                    .map((f) => (
                      <div key={f.finding_id} className="bg-slate-950 p-2 rounded-lg border border-slate-850 text-xs flex justify-between items-center">
                        <div>
                          <span className="font-semibold text-slate-200">{f.title}</span>
                          <span className="text-[10px] text-slate-400 block">Owner: {f.owner} | Due: {f.due_date}</span>
                        </div>
                        <span className={`px-2 py-0.5 rounded text-[10px] ${getSeverityBadge(f.severity)}`}>
                          {f.severity}
                        </span>
                      </div>
                    ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-8 text-center text-slate-500 text-xs">
              Select a control to review framework clause mappings and record assessments.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
export default ComplianceGovernancePage;

