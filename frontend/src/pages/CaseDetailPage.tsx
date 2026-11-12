import React, { useState } from 'react';
import {
  ArrowLeft,
  ShieldAlert,
  CreditCard,
  User,
  Clock,
  MapPin,
  Smartphone,
  Wifi,
  FileText,
  Send,
  CheckCircle,
  XCircle,
  AlertOctagon,
  History,
  Cpu,
  Layers,
  Lock
} from 'lucide-react';
import { InvestigationCase, CaseStatus } from '../types/case';
import { RiskBadge } from '../components/RiskBadge';
import { StatusBadge } from '../components/StatusBadge';
import { AiAssistantCard } from '../components/AiAssistantCard';

interface CaseDetailPageProps {
  caseData: InvestigationCase;
  onBack: () => void;
  onUpdateStatus: (caseId: string, newStatus: CaseStatus) => Promise<void>;
  onAddNote: (caseId: string, noteText: string) => Promise<void>;
}

export const CaseDetailPage: React.FC<CaseDetailPageProps> = ({
  caseData,
  onBack,
  onUpdateStatus,
  onAddNote
}) => {
  const [newNote, setNewNote] = useState('');
  const [isSubmittingNote, setIsSubmittingNote] = useState(false);
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const handleStatusChange = async (newStatus: CaseStatus) => {
    setIsUpdatingStatus(true);
    try {
      await onUpdateStatus(caseData.case_id, newStatus);
      setStatusMessage(`Status updated to ${newStatus}`);
      setTimeout(() => setStatusMessage(null), 3000);
    } finally {
      setIsUpdatingStatus(false);
    }
  };

  const handlePostNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newNote.trim()) return;

    setIsSubmittingNote(true);
    try {
      await onAddNote(caseData.case_id, newNote.trim());
      setNewNote('');
    } finally {
      setIsSubmittingNote(false);
    }
  };

  const formatCurrency = (amt: number, curr: string = 'INR') => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: curr || 'INR',
      maximumFractionDigits: 0
    }).format(amt);
  };

  const formatDate = (iso: string) => {
    try {
      const d = new Date(iso);
      return d.toLocaleString('en-US', {
        dateStyle: 'medium',
        timeStyle: 'short'
      });
    } catch {
      return iso;
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Navigation & Status Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900/80 border border-slate-800 rounded-xl p-4">
        <div className="flex items-center space-x-3">
          <button
            onClick={onBack}
            className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors"
            title="Back to Investigation Queue"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="flex items-center space-x-3">
              <span className="font-mono text-lg font-bold text-white tracking-tight">
                {caseData.case_id}
              </span>
              <RiskBadge level={caseData.risk_level} score={caseData.risk_score} />
              <StatusBadge status={caseData.status} />
              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                Priority: {caseData.priority}
              </span>
            </div>
            <div className="text-xs text-slate-400 mt-0.5 font-mono">
              Flagged at: {formatDate(caseData.created_at)} &bull; Assigned to:{' '}
              <span className="text-sky-300 font-semibold">{caseData.assigned_to || 'Unassigned'}</span>
            </div>
          </div>
        </div>

        {/* Status Dropdown & Feedback */}
        <div className="flex items-center space-x-3">
          {statusMessage && (
            <span className="text-xs text-emerald-400 font-medium font-mono animate-fade-in">
              {statusMessage}
            </span>
          )}
          <label className="text-xs text-slate-400 font-mono">Update State:</label>
          <select
            value={caseData.status}
            onChange={(e) => handleStatusChange(e.target.value as CaseStatus)}
            disabled={isUpdatingStatus}
            className="bg-slate-950 border border-slate-700 text-slate-200 text-xs font-mono rounded-lg px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-sky-500"
          >
            <option value="OPEN">OPEN</option>
            <option value="IN_REVIEW">IN_REVIEW</option>
            <option value="ESCALATED">ESCALATED</option>
            <option value="RESOLVED">RESOLVED</option>
            <option value="CLOSED">CLOSED</option>
          </select>
        </div>
      </div>

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Transaction Dossier & ML Telemetry (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          {/* Quantitative ML Risk Telemetry */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-4 shadow-lg">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 font-mono flex items-center gap-2">
              <Cpu className="w-4 h-4 text-sky-400" />
              Machine Learning Risk Decomposition
            </h3>

            {/* Score Bar */}
            <div className="p-4 bg-slate-950/70 rounded-xl border border-slate-800/80 space-y-2">
              <div className="flex justify-between items-baseline">
                <span className="text-xs font-mono text-slate-400">Composite Risk Score</span>
                <span className="text-2xl font-bold font-mono text-rose-400">
                  {caseData.risk_score.toFixed(3)}
                  <span className="text-xs text-slate-500 font-normal"> / 1.000</span>
                </span>
              </div>
              <div className="w-full bg-slate-800 rounded-full h-2.5 overflow-hidden">
                <div
                  className="h-2.5 rounded-full bg-gradient-to-r from-amber-500 to-rose-600 transition-all duration-500"
                  style={{ width: `${Math.min(100, caseData.risk_score * 100)}%` }}
                />
              </div>
              <div className="flex justify-between text-[10px] font-mono text-slate-500 pt-1">
                <span>0.00 (Safe)</span>
                <span>0.50 (Review Threshold)</span>
                <span>1.00 (Critical)</span>
              </div>
            </div>

            {/* Dual Model Breakdown */}
            <div className="grid grid-cols-2 gap-3 font-mono text-xs">
              <div className="p-3 bg-slate-950/50 rounded-lg border border-slate-800">
                <div className="text-[10px] text-slate-400">XGBoost Fraud Prob</div>
                <div className="text-base font-bold text-sky-400 mt-1">
                  {((caseData.fraud_probability ?? 0.5) * 100).toFixed(1)}%
                </div>
                <div className="text-[10px] text-slate-500 mt-0.5">Weight: 65%</div>
              </div>

              <div className="p-3 bg-slate-950/50 rounded-lg border border-slate-800">
                <div className="text-[10px] text-slate-400">Isolation Anomaly</div>
                <div className="text-base font-bold text-indigo-400 mt-1">
                  {((caseData.anomaly_score ?? 0.3) * 100).toFixed(1)}%
                </div>
                <div className="text-[10px] text-slate-500 mt-0.5">Weight: 35%</div>
              </div>
            </div>

            {/* Ingestion Feature Signals */}
            {caseData.features && (
              <div className="pt-2 border-t border-slate-800 space-y-2">
                <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">
                  Ingestion Behavioral Signals
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  {caseData.features.amount_ratio_to_avg !== undefined && (
                    <div className="p-2 rounded bg-slate-950/40 border border-slate-800/60 font-mono">
                      <span className="text-slate-500 text-[10px]">Amount / Avg:</span>
                      <div className="text-slate-200 font-semibold">{caseData.features.amount_ratio_to_avg.toFixed(1)}x</div>
                    </div>
                  )}
                  {caseData.features.velocity_1h !== undefined && (
                    <div className="p-2 rounded bg-slate-950/40 border border-slate-800/60 font-mono">
                      <span className="text-slate-500 text-[10px]">1h Velocity:</span>
                      <div className="text-slate-200 font-semibold">{caseData.features.velocity_1h} txns</div>
                    </div>
                  )}
                  {caseData.features.dist_from_home_km !== undefined && (
                    <div className="p-2 rounded bg-slate-950/40 border border-slate-800/60 font-mono">
                      <span className="text-slate-500 text-[10px]">Geo Distance:</span>
                      <div className="text-slate-200 font-semibold">{caseData.features.dist_from_home_km.toFixed(0)} km</div>
                    </div>
                  )}
                  {caseData.features.is_new_device !== undefined && (
                    <div className="p-2 rounded bg-slate-950/40 border border-slate-800/60 font-mono">
                      <span className="text-slate-500 text-[10px]">Device Known:</span>
                      <div className={caseData.features.is_new_device ? 'text-rose-400 font-semibold' : 'text-emerald-400 font-semibold'}>
                        {caseData.features.is_new_device ? 'NEW DEVICE' : 'Known'}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Transaction Metadata Dossier */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-4 shadow-lg">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 font-mono flex items-center gap-2">
              <CreditCard className="w-4 h-4 text-indigo-400" />
              Transaction Metadata
            </h3>

            <div className="space-y-3 text-xs">
              <div className="flex justify-between py-1.5 border-b border-slate-800/60">
                <span className="text-slate-400">Transaction ID:</span>
                <span className="font-mono text-slate-200">{caseData.transaction_id}</span>
              </div>

              <div className="flex justify-between py-1.5 border-b border-slate-800/60">
                <span className="text-slate-400">Amount & Currency:</span>
                <span className="font-mono font-bold text-white">
                  {formatCurrency(caseData.amount, caseData.currency)}
                </span>
              </div>

              <div className="flex justify-between py-1.5 border-b border-slate-800/60">
                <span className="text-slate-400">Banking Channel:</span>
                <span className="font-mono uppercase text-sky-400 font-semibold">{caseData.channel}</span>
              </div>

              <div className="flex justify-between py-1.5 border-b border-slate-800/60">
                <span className="text-slate-400">Customer ID:</span>
                <span className="font-mono text-slate-200">{caseData.customer_id}</span>
              </div>

              <div className="flex justify-between py-1.5 border-b border-slate-800/60">
                <span className="text-slate-400">Account ID:</span>
                <span className="font-mono text-slate-200">{caseData.account_id}</span>
              </div>

              {caseData.merchant_name && (
                <div className="flex justify-between py-1.5 border-b border-slate-800/60">
                  <span className="text-slate-400">Merchant:</span>
                  <span className="font-medium text-slate-200">{caseData.merchant_name}</span>
                </div>
              )}

              {caseData.merchant_category && (
                <div className="flex justify-between py-1.5 border-b border-slate-800/60">
                  <span className="text-slate-400">Merchant MCC / Category:</span>
                  <span className="font-mono text-slate-300">{caseData.merchant_category}</span>
                </div>
              )}

              {caseData.location && (
                <div className="flex justify-between py-1.5 border-b border-slate-800/60">
                  <span className="text-slate-400 flex items-center gap-1">
                    <MapPin className="w-3.5 h-3.5 text-slate-500" />
                    Transaction Geo:
                  </span>
                  <span className="font-mono text-slate-200">{caseData.location}</span>
                </div>
              )}

              {caseData.ip_address && (
                <div className="flex justify-between py-1.5 border-b border-slate-800/60">
                  <span className="text-slate-400 flex items-center gap-1">
                    <Wifi className="w-3.5 h-3.5 text-slate-500" />
                    Origin IP:
                  </span>
                  <span className="font-mono text-slate-300">{caseData.ip_address}</span>
                </div>
              )}

              {caseData.device_id && (
                <div className="flex justify-between py-1.5">
                  <span className="text-slate-400 flex items-center gap-1">
                    <Smartphone className="w-3.5 h-3.5 text-slate-500" />
                    Device Fingerprint:
                  </span>
                  <span className="font-mono text-slate-300 truncate max-w-[160px]" title={caseData.device_id}>
                    {caseData.device_id}
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Bedrock GenAI Synthesis & Analyst Workspace (7 cols) */}
        <div className="lg:col-span-7 space-y-6">
          {/* Bedrock GenAI Assistant Card */}
          <AiAssistantCard summary={caseData.bedrock_summary} />

          {/* Quick Decision Resolution Bar */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-3 shadow-lg">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300 font-mono flex items-center gap-2">
              <Lock className="w-4 h-4 text-sky-400" />
              Investigator Binding Verdict
            </h3>
            <p className="text-xs text-slate-400">
              Select one action to record investigator resolution in immutable DynamoDB audit log:
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
              <button
                onClick={() => handleStatusChange('RESOLVED')}
                disabled={isUpdatingStatus}
                className="p-3 rounded-lg bg-rose-950/40 hover:bg-rose-900/50 border border-rose-800/60 text-rose-200 text-xs font-medium flex items-center space-x-2 transition-all"
              >
                <XCircle className="w-4 h-4 text-rose-400 shrink-0" />
                <div className="text-left">
                  <div className="font-bold">Confirm Fraud & Freeze</div>
                  <div className="text-[10px] text-rose-300/70">Restrict account & void auth</div>
                </div>
              </button>

              <button
                onClick={() => handleStatusChange('CLOSED')}
                disabled={isUpdatingStatus}
                className="p-3 rounded-lg bg-emerald-950/40 hover:bg-emerald-900/50 border border-emerald-800/60 text-emerald-200 text-xs font-medium flex items-center space-x-2 transition-all"
              >
                <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
                <div className="text-left">
                  <div className="font-bold">Legitimate / False Positive</div>
                  <div className="text-[10px] text-emerald-300/70">Approve transaction & release</div>
                </div>
              </button>

              <button
                onClick={() => handleStatusChange('ESCALATED')}
                disabled={isUpdatingStatus}
                className="p-3 rounded-lg bg-amber-950/40 hover:bg-amber-900/50 border border-amber-800/60 text-amber-200 text-xs font-medium flex items-center space-x-2 transition-all"
              >
                <AlertOctagon className="w-4 h-4 text-amber-400 shrink-0" />
                <div className="text-left">
                  <div className="font-bold">Escalate to AML Tier-2</div>
                  <div className="text-[10px] text-amber-300/70">Submit for SAR filing review</div>
                </div>
              </button>

              <button
                onClick={() => handleStatusChange('IN_REVIEW')}
                disabled={isUpdatingStatus}
                className="p-3 rounded-lg bg-sky-950/40 hover:bg-sky-900/50 border border-sky-800/60 text-sky-200 text-xs font-medium flex items-center space-x-2 transition-all"
              >
                <Clock className="w-4 h-4 text-sky-400 shrink-0" />
                <div className="text-left">
                  <div className="font-bold">Hold for Customer Outbound</div>
                  <div className="text-[10px] text-sky-300/70">Trigger step-up 2FA callback</div>
                </div>
              </button>
            </div>
          </div>

          {/* Notes & Audit History */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-4 shadow-lg">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 font-mono flex items-center gap-2">
              <FileText className="w-4 h-4 text-sky-400" />
              Investigation Notes ({caseData.notes?.length || 0})
            </h3>

            {/* Note Input */}
            <form onSubmit={handlePostNote} className="space-y-2">
              <textarea
                value={newNote}
                onChange={(e) => setNewNote(e.target.value)}
                placeholder="Enter investigator observations, customer call logs, or verification details..."
                rows={3}
                className="w-full bg-slate-950/80 border border-slate-800 rounded-lg p-3 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-sky-500 font-sans"
              />
              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={isSubmittingNote || !newNote.trim()}
                  className="px-4 py-2 bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-colors shadow-sm"
                >
                  <Send className="w-3.5 h-3.5" />
                  <span>{isSubmittingNote ? 'Saving...' : 'Add Case Note'}</span>
                </button>
              </div>
            </form>

            {/* Notes List */}
            <div className="space-y-2.5 pt-2 border-t border-slate-800">
              {caseData.notes && caseData.notes.length > 0 ? (
                caseData.notes.map((n, idx) => (
                  <div key={idx} className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 text-xs space-y-1">
                    <div className="flex justify-between items-center text-[10px] font-mono text-slate-400">
                      <span className="text-sky-300 font-semibold">{n.author}</span>
                      <span>{formatDate(n.created_at || n.timestamp || '')}</span>
                    </div>
                    <p className="text-slate-200 font-sans leading-relaxed">{n.note || n.content || ''}</p>
                  </div>
                ))
              ) : (
                <div className="text-center py-4 text-xs text-slate-500 font-mono">
                  No analyst notes attached to this case yet.
                </div>
              )}
            </div>

            {/* Audit Trail Timeline */}
            {caseData.audit_trail && caseData.audit_trail.length > 0 && (
              <div className="pt-4 border-t border-slate-800 space-y-2">
                <h4 className="text-[11px] font-mono uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                  <History className="w-3.5 h-3.5 text-slate-400" />
                  Audit Trail
                </h4>
                <div className="space-y-1.5 font-mono text-[11px]">
                  {caseData.audit_trail.map((at, idx) => (
                    <div key={idx} className="flex items-center justify-between p-2 rounded bg-slate-950/40 text-slate-400">
                      <span>
                        <span className="text-slate-300 font-semibold">{at.action}</span> by {at.performed_by}
                      </span>
                      <span className="text-slate-500">{formatDate(at.timestamp)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

