import React, { useState, useEffect } from 'react';
import {
  FileCheck,
  ShieldCheck,
  ShieldAlert,
  Clock,
  Sparkles,
  FileText,
  Lock,
  Search,
  RefreshCw,
  PlusCircle,
  Hash,
  Database,
  ExternalLink,
  CheckCircle2,
  AlertOctagon,
  Copy,
  Layers,
  Fingerprint
} from 'lucide-react';

interface EvidenceItem {
  evidence_id: string;
  case_id: string;
  evidence_type: string;
  title: string;
  description: string;
  source_system: string;
  collected_at: string;
  collector: string;
  raw_payload: Record<string, any>;
  sha256_hash: string;
  size_bytes: number;
}

interface IntegrityResult {
  evidence_id: string;
  verified: boolean;
  stored_hash: string;
  computed_hash: string;
  status: string;
  details: string;
}

interface TimelineEvent {
  event_id: string;
  timestamp: string;
  event_type: string;
  entity_id: string;
  summary: string;
  evidence_id?: string;
}

interface CopilotDraft {
  draft_id: string;
  case_id: string;
  generated_at: string;
  model_provider: string;
  executive_summary: string;
  threat_hypotheses: string[];
  key_findings: string[];
  recommended_actions: string[];
  evidence_citations: Array<{
    evidence_id: string;
    evidence_type: string;
    title: string;
    relevance: string;
  }>;
  confidence_score: number;
  confidence_rationale: string;
}

interface AuditEntry {
  audit_id: string;
  timestamp: string;
  actor: string;
  action: string;
  evidence_id?: string;
  ip_address: string;
}

export const EvidenceWorkspacePage: React.FC = () => {
  const [selectedCaseId, setSelectedCaseId] = useState<string>('CASE-P0-9901');
  const [evidenceList, setEvidenceList] = useState<EvidenceItem[]>([]);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [copilotDraft, setCopilotDraft] = useState<CopilotDraft | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [verificationResults, setVerificationResults] = useState<Record<string, IntegrityResult>>({});
  const [activeTab, setActiveTab] = useState<'locker' | 'timeline' | 'copilot' | 'report' | 'audit'>('locker');
  const [reportMarkdown, setReportMarkdown] = useState<string>('');
  const [copiedHash, setCopiedHash] = useState<string | null>(null);

  const fetchCaseEvidenceData = async (caseId: string) => {
    setLoading(true);
    try {
      const [evRes, timeRes, auditRes] = await Promise.all([
        fetch(`http://127.0.0.1:8010/cases/${caseId}/evidence`),
        fetch(`http://127.0.0.1:8010/cases/${caseId}/timeline`),
        fetch(`http://127.0.0.1:8010/evidence/audit?case_id=${caseId}`)
      ]);

      if (evRes.ok) {
        const evData = await evRes.json();
        setEvidenceList(evData);
      }
      if (timeRes.ok) {
        const timeData = await timeRes.json();
        setTimeline(timeData.events || []);
      }
      if (auditRes.ok) {
        const auditData = await auditRes.json();
        setAuditLogs(auditData);
      }
    } catch {
      console.warn('Backend unavailable, using initial demo evidence view');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCaseEvidenceData(selectedCaseId);
  }, [selectedCaseId]);

  const handleVerifyIntegrity = async (evidenceId: string) => {
    try {
      const res = await fetch(`http://127.0.0.1:8010/evidence/${evidenceId}/verify`, { method: 'POST' });
      if (res.ok) {
        const data: IntegrityResult = await res.json();
        setVerificationResults((prev) => ({ ...prev, [evidenceId]: data }));
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleGenerateCopilotDraft = async () => {
    try {
      const res = await fetch(`http://127.0.0.1:8010/cases/${selectedCaseId}/copilot/draft`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      if (res.ok) {
        const draft = await res.json();
        setCopilotDraft(draft);
        setActiveTab('copilot');
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleGenerateReport = async () => {
    try {
      const res = await fetch(`http://127.0.0.1:8010/cases/${selectedCaseId}/reports`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          author: 'sarah.connor@finguard.internal',
          disposition: 'CONFIRMED_FRAUD',
          analyst_notes: 'All cryptographic SHA-256 evidence digests verified authentic in vault.'
        })
      });
      if (res.ok) {
        const report = await res.json();
        setReportMarkdown(report.report_markdown);
        setActiveTab('report');
      }
    } catch (err) {
      console.error(err);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedHash(text);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  const getEvidenceTypeBadge = (type: string) => {
    switch (type) {
      case 'TRANSACTION_RECORD':
        return 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40';
      case 'DEVICE_FINGERPRINT':
        return 'bg-sky-500/20 text-sky-400 border border-sky-500/40';
      case 'NETWORK_FLOW_IP':
        return 'bg-amber-500/20 text-amber-400 border border-amber-500/40';
      case 'GRAPH_COMMUNITY_SNAPSHOT':
        return 'bg-purple-500/20 text-purple-400 border border-purple-500/40';
      default:
        return 'bg-slate-500/20 text-slate-400 border border-slate-500/40';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-slate-100">
              Evidence Management, Digital Forensics & AI Copilot
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
              Phase 22
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Immutable SHA-256 evidence indexing, multi-source digital timeline, source-cited AI Copilot drafts, and forensic reports.
          </p>
        </div>

        {/* Case Selector */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs">
            <span className="text-slate-400">Case ID:</span>
            <input
              type="text"
              value={selectedCaseId}
              onChange={(e) => setSelectedCaseId(e.target.value)}
              className="bg-transparent font-mono text-purple-400 font-bold outline-none w-32"
            />
          </div>
          <button
            onClick={() => fetchCaseEvidenceData(selectedCaseId)}
            className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg border border-slate-700 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Action Navigation Tabs */}
      <div className="flex flex-wrap items-center gap-2 border-b border-slate-800 pb-2">
        <button
          onClick={() => setActiveTab('locker')}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium transition ${
            activeTab === 'locker'
              ? 'bg-purple-600/20 text-purple-300 border border-purple-500/40'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Database className="w-3.5 h-3.5" />
          Evidence Locker ({evidenceList.length})
        </button>
        <button
          onClick={() => setActiveTab('timeline')}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium transition ${
            activeTab === 'timeline'
              ? 'bg-purple-600/20 text-purple-300 border border-purple-500/40'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Clock className="w-3.5 h-3.5" />
          Digital Timeline ({timeline.length})
        </button>
        <button
          onClick={() => setActiveTab('copilot')}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium transition ${
            activeTab === 'copilot'
              ? 'bg-purple-600/20 text-purple-300 border border-purple-500/40'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Sparkles className="w-3.5 h-3.5 text-purple-400" />
          AI Copilot Draft
        </button>
        <button
          onClick={() => setActiveTab('report')}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium transition ${
            activeTab === 'report'
              ? 'bg-purple-600/20 text-purple-300 border border-purple-500/40'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <FileText className="w-3.5 h-3.5" />
          Analyst Report
        </button>
        <button
          onClick={() => setActiveTab('audit')}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium transition ${
            activeTab === 'audit'
              ? 'bg-purple-600/20 text-purple-300 border border-purple-500/40'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <ShieldCheck className="w-3.5 h-3.5" />
          Access Audit ({auditLogs.length})
        </button>

        <div className="ml-auto flex items-center gap-2">
          <button
            onClick={handleGenerateCopilotDraft}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white rounded-lg text-xs font-semibold shadow transition"
          >
            <Sparkles className="w-3.5 h-3.5" />
            Synthesize with Copilot
          </button>
          <button
            onClick={handleGenerateReport}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold border border-slate-700 transition"
          >
            <FileCheck className="w-3.5 h-3.5" />
            Export Formal Report
          </button>
        </div>
      </div>

      {/* Tab Content: Evidence Locker */}
      {activeTab === 'locker' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {evidenceList.map((item) => {
              const vResult = verificationResults[item.evidence_id];
              return (
                <div
                  key={item.evidence_id}
                  className="bg-slate-900/60 border border-slate-800 hover:border-slate-700 p-4 rounded-xl space-y-3 transition"
                >
                  <div className="flex items-center justify-between">
                    <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${getEvidenceTypeBadge(item.evidence_type)}`}>
                      {item.evidence_type}
                    </span>
                    <span className="font-mono text-xs text-slate-400">{item.evidence_id}</span>
                  </div>

                  <div>
                    <h3 className="text-sm font-bold text-slate-100">{item.title}</h3>
                    <p className="text-xs text-slate-400 mt-1">{item.description}</p>
                  </div>

                  {/* Payload Summary */}
                  <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-850 font-mono text-xs text-slate-300 max-h-28 overflow-y-auto">
                    <pre className="text-[11px]">{JSON.stringify(item.raw_payload, null, 2)}</pre>
                  </div>

                  {/* SHA-256 Hash Digest */}
                  <div className="bg-slate-950/80 p-2 rounded-lg border border-slate-800 text-[11px] font-mono flex items-center justify-between gap-2">
                    <div className="flex items-center gap-1.5 truncate text-slate-400">
                      <Hash className="w-3.5 h-3.5 text-purple-400 flex-shrink-0" />
                      <span className="truncate">{item.sha256_hash}</span>
                    </div>
                    <button
                      onClick={() => copyToClipboard(item.sha256_hash)}
                      className="text-slate-400 hover:text-slate-200 text-xs flex-shrink-0"
                    >
                      {copiedHash === item.sha256_hash ? 'Copied' : <Copy className="w-3.5 h-3.5" />}
                    </button>
                  </div>

                  {/* Verification Banner */}
                  <div className="flex items-center justify-between pt-2 border-t border-slate-800/80">
                    <div className="text-[11px] text-slate-400">
                      Source: <span className="text-slate-300 font-mono">{item.source_system}</span>
                    </div>

                    {vResult ? (
                      <span
                        className={`flex items-center gap-1 px-2.5 py-0.5 rounded text-xs font-semibold ${
                          vResult.verified
                            ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                            : 'bg-rose-500/20 text-rose-400 border border-rose-500/40'
                        }`}
                      >
                        {vResult.verified ? (
                          <>
                            <CheckCircle2 className="w-3.5 h-3.5" /> Authentic (SHA-256)
                          </>
                        ) : (
                          <>
                            <AlertOctagon className="w-3.5 h-3.5" /> Tamper Detected!
                          </>
                        )}
                      </span>
                    ) : (
                      <button
                        onClick={() => handleVerifyIntegrity(item.evidence_id)}
                        className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-xs flex items-center gap-1 transition"
                      >
                        <Lock className="w-3 h-3 text-purple-400" /> Verify Integrity
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Tab Content: Digital Timeline */}
      {activeTab === 'timeline' && (
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
          <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
            <Clock className="w-4 h-4 text-purple-400" />
            Chronological Forensic Timeline ({timeline.length} Recorded Milestones)
          </h3>
          <div className="relative pl-6 space-y-4 border-l-2 border-slate-800 ml-3">
            {timeline.map((evt) => (
              <div key={evt.event_id} className="relative">
                <div className="absolute -left-[31px] top-1.5 w-3 h-3 bg-purple-500 rounded-full border-2 border-slate-900" />
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-850 space-y-1">
                  <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                    <span className="font-bold text-slate-200">{evt.event_type}</span>
                    <span>{new Date(evt.timestamp).toLocaleString()}</span>
                  </div>
                  <p className="text-xs text-slate-300">{evt.summary}</p>
                  <div className="text-[11px] text-slate-500 font-mono">
                    Entity: <span className="text-slate-400">{evt.entity_id}</span>
                    {evt.evidence_id && (
                      <span className="ml-3 text-purple-400">Ref: {evt.evidence_id}</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab Content: AI Copilot Draft */}
      {activeTab === 'copilot' && (
        <div className="space-y-4">
          {copilotDraft ? (
            <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-6 space-y-5">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div>
                  <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-purple-400" />
                    AI Investigation Copilot Synthesis
                  </h3>
                  <span className="text-xs text-slate-400 font-mono">{copilotDraft.model_provider}</span>
                </div>
                <div className="text-right">
                  <span className="text-xs text-slate-400 block">Copilot Confidence</span>
                  <span className="text-lg font-bold text-purple-400">
                    {(copilotDraft.confidence_score * 100).toFixed(0)}%
                  </span>
                </div>
              </div>

              {/* Executive Summary */}
              <div className="space-y-1">
                <span className="text-xs font-semibold text-slate-400 block uppercase">Executive Summary</span>
                <p className="text-sm text-slate-200 leading-relaxed bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                  {copilotDraft.executive_summary}
                </p>
              </div>

              {/* Threat Hypotheses */}
              <div className="space-y-2">
                <span className="text-xs font-semibold text-slate-400 block uppercase">Threat Hypotheses</span>
                <div className="space-y-2">
                  {copilotDraft.threat_hypotheses.map((hyp, i) => (
                    <div key={i} className="text-xs text-slate-200 bg-slate-950 p-2.5 rounded-lg border border-slate-850">
                      {hyp}
                    </div>
                  ))}
                </div>
              </div>

              {/* Key Findings with Source Citations */}
              <div className="space-y-2">
                <span className="text-xs font-semibold text-slate-400 block uppercase">Evidence-Grounded Findings</span>
                <div className="space-y-2">
                  {copilotDraft.key_findings.map((f, i) => (
                    <div key={i} className="text-xs text-slate-200 bg-slate-950 p-2.5 rounded-lg border border-slate-850 font-mono">
                      {f}
                    </div>
                  ))}
                </div>
              </div>

              {/* Cited Evidence Sources */}
              <div className="space-y-2">
                <span className="text-xs font-semibold text-slate-400 block uppercase">Evidence Citations</span>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {copilotDraft.evidence_citations.map((cite) => (
                    <div key={cite.evidence_id} className="text-xs bg-slate-950 p-2 rounded-lg border border-slate-800">
                      <div className="flex justify-between items-center font-mono">
                        <span className="text-purple-400 font-bold">{cite.evidence_id}</span>
                        <span className="text-[10px] text-slate-500">{cite.evidence_type}</span>
                      </div>
                      <p className="text-slate-300 text-[11px] mt-0.5">{cite.title}</p>
                      <span className="text-[10px] text-slate-400 italic block mt-1">{cite.relevance}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Recommended Actions */}
              <div className="space-y-2 border-t border-slate-800 pt-3">
                <span className="text-xs font-semibold text-slate-400 block uppercase">Recommended SOC Actions</span>
                <ul className="list-disc list-inside text-xs text-slate-300 space-y-1">
                  {copilotDraft.recommended_actions.map((act, i) => (
                    <li key={i}>{act}</li>
                  ))}
                </ul>
              </div>
            </div>
          ) : (
            <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-8 text-center text-slate-500 text-xs">
              Click &quot;Synthesize with Copilot&quot; to generate an evidence-grounded investigation summary with explicit citations.
            </div>
          )}
        </div>
      )}

      {/* Tab Content: Formal Report Preview */}
      {activeTab === 'report' && (
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 space-y-4">
          <div className="flex justify-between items-center border-b border-slate-800 pb-3">
            <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
              <FileText className="w-4 h-4 text-purple-400" />
              Formal Analyst Investigation Report (Markdown Preview)
            </h3>
            <button
              onClick={() => copyToClipboard(reportMarkdown)}
              className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs rounded-lg border border-slate-700 flex items-center gap-1.5"
            >
              <Copy className="w-3.5 h-3.5" />
              Copy Report Markdown
            </button>
          </div>
          <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 font-mono text-xs text-slate-300 max-h-[500px] overflow-y-auto whitespace-pre-wrap leading-relaxed">
            {reportMarkdown || 'Click "Export Formal Report" to compile the investigation report with cryptographic sign-off.'}
          </div>
        </div>
      )}

      {/* Tab Content: Access Audit Log */}
      {activeTab === 'audit' && (
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
          <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            Tamper-Evident Evidence Access & Verification Audit Trail
          </h3>
          <div className="space-y-2">
            {auditLogs.map((log) => (
              <div key={log.audit_id} className="bg-slate-950 p-2.5 rounded-lg border border-slate-850 flex items-center justify-between text-xs font-mono">
                <div className="flex items-center gap-2">
                  <span className="text-purple-400 font-bold">{log.action}</span>
                  <span className="text-slate-400">by {log.actor}</span>
                  {log.evidence_id && <span className="text-slate-500">({log.evidence_id})</span>}
                </div>
                <div className="text-slate-500 text-[11px]">
                  <span>{new Date(log.timestamp).toLocaleTimeString()}</span>
                  <span className="ml-2 text-slate-600">{log.ip_address}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
export default EvidenceWorkspacePage;

