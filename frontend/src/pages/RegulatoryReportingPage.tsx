import React, { useState, useEffect } from 'react';
import {
  FileText,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  Clock,
  CheckCircle2,
  XCircle,
  RotateCcw,
  Send,
  Search,
  Filter,
  PlusCircle,
  RefreshCw,
  Info,
  ExternalLink,
  ChevronRight,
  DollarSign,
  User,
  Layers,
  History,
  FileCheck2,
  AlertOctagon
} from 'lucide-react';

interface ValidationError {
  field: string;
  message: string;
  severity: string;
}

interface ValidationResult {
  is_valid: boolean;
  errors: ValidationError[];
  checked_at: string;
}

interface AuditEvent {
  event_id: string;
  report_id: string;
  action: string;
  performed_by: string;
  details: Record<string, any>;
  timestamp: string;
}

interface RegulatoryReport {
  report_id: string;
  report_type: 'SAR' | 'STR';
  jurisdiction: string;
  status: 'DRAFT' | 'UNDER_REVIEW' | 'APPROVED' | 'REJECTED' | 'RETURNED_TO_DRAFT' | 'SUBMITTED';
  case_id?: string;
  customer_id: string;
  customer_name: string;
  customer_pan_or_id?: string;
  suspicion_narrative: string;
  primary_offense_category: string;
  transaction_ids: string[];
  evidence_ids: string[];
  total_suspicious_amount: number;
  currency: string;
  created_by: string;
  created_at: string;
  updated_at: string;
  filing_deadline: string;
  is_overdue: boolean;
  reviewed_by?: string;
  reviewed_at?: string;
  review_notes?: string;
  external_filing_reference?: string;
  submitted_at?: string;
  submitted_by?: string;
  validation_result?: ValidationResult;
}

interface ReportingMetrics {
  total_reports: number;
  draft_count: number;
  under_review_count: number;
  approved_count: number;
  submitted_count: number;
  rejected_count: number;
  returned_to_draft_count: number;
  overdue_count: number;
  total_suspicious_amount_reported: number;
}

const DEMO_REPORTS: RegulatoryReport[] = [
  {
    report_id: 'SAR-2026-IND-001',
    report_type: 'SAR',
    jurisdiction: 'FIU_IND',
    status: 'SUBMITTED',
    case_id: 'CASE-AML-9901',
    customer_id: 'CUST-IND-77102',
    customer_name: 'Vikram Malhotra',
    customer_pan_or_id: 'ABCDE1234F',
    suspicion_narrative:
      'Repeated cash deposits just below the ₹10,00,000 threshold followed by immediate NEFT transfers overseas, indicative of structuring and layering.',
    primary_offense_category: 'Structuring',
    transaction_ids: ['TXN-2026-001', 'TXN-2026-002', 'TXN-2026-003'],
    evidence_ids: ['EV-SHA256-BANK-01', 'EV-SHA256-KYC-02'],
    total_suspicious_amount: 3250000.0,
    currency: 'INR',
    created_by: 'compliance_analyst@finguard.internal',
    created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 12).toISOString(),
    updated_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 2).toISOString(),
    filing_deadline: new Date(Date.now() + 1000 * 60 * 60 * 24 * 18).toISOString(),
    is_overdue: false,
    reviewed_by: 'mlro_officer@finguard.internal',
    reviewed_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 4).toISOString(),
    review_notes: 'Approved for official filing. Clear structuring pattern confirmed.',
    external_filing_reference: 'FIU-IND-ACK-202604-9912',
    submitted_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 2).toISOString(),
    submitted_by: 'mlro_officer@finguard.internal',
    validation_result: { is_valid: true, errors: [], checked_at: new Date().toISOString() }
  },
  {
    report_id: 'STR-2026-IND-002',
    report_type: 'STR',
    jurisdiction: 'FIU_IND',
    status: 'UNDER_REVIEW',
    case_id: 'CASE-AML-4412',
    customer_id: 'CUST-BLR-40291',
    customer_name: 'Jordan Cross',
    customer_pan_or_id: 'BNMPL9021K',
    suspicion_narrative:
      'High-velocity payment funneling through newly added beneficiaries within 10-minute intervals without underlying economic rationale.',
    primary_offense_category: 'Payment Funneling / Layering',
    transaction_ids: ['TXN-UPI-285000', 'TXN-UPI-285001'],
    evidence_ids: ['EV-PAYMENT-GATEWAY-TRACE-01'],
    total_suspicious_amount: 1450000.0,
    currency: 'INR',
    created_by: 'analyst_rajesh@finguard.internal',
    created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 3).toISOString(),
    updated_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 1).toISOString(),
    filing_deadline: new Date(Date.now() + 1000 * 60 * 60 * 24 * 27).toISOString(),
    is_overdue: false,
    validation_result: { is_valid: true, errors: [], checked_at: new Date().toISOString() }
  }
];

export const RegulatoryReportingPage: React.FC = () => {
  const [reports, setReports] = useState<RegulatoryReport[]>(DEMO_REPORTS);
  const [selectedReport, setSelectedReport] = useState<RegulatoryReport>(DEMO_REPORTS[0]);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [metrics, setMetrics] = useState<ReportingMetrics>({
    total_reports: 2,
    draft_count: 0,
    under_review_count: 1,
    approved_count: 0,
    submitted_count: 1,
    rejected_count: 0,
    returned_to_draft_count: 0,
    overdue_count: 0,
    total_suspicious_amount_reported: 4700000.0
  });

  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [typeFilter, setTypeFilter] = useState('ALL');
  const [loading, setLoading] = useState(false);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isSubmitModalOpen, setIsSubmitModalOpen] = useState(false);
  const [filingRefInput, setFilingRefInput] = useState('');

  // Create form state
  const [formData, setFormData] = useState({
    report_type: 'SAR',
    jurisdiction: 'FIU_IND',
    customer_id: 'CUST-BLR-40291',
    customer_name: 'Jordan Cross',
    customer_pan_or_id: 'BNMPL9021K',
    suspicion_narrative:
      'Multiple rapid payment bursts totaling INR 14,50,000 across newly added beneficiaries in disparate geographic locations within short time intervals without stated legitimate commercial basis.',
    primary_offense_category: 'Structuring and Layering',
    transaction_ids: 'TXN-2026-UPI-285000, TXN-2026-UPI-285001, TXN-2026-IMPS-880192',
    evidence_ids: 'EV-SHA256-PAYMENT-AUDIT-01, EV-SHA256-GEOLOCATION-LOG-02',
    total_suspicious_amount: 1450000,
    currency: 'INR'
  });

  const fetchReports = async () => {
    try {
      setLoading(true);
      const res = await fetch('http://127.0.0.1:8011/reports');
      if (res.ok) {
        const data = await res.json();
        if (data && data.length > 0) {
          setReports(data);
          setSelectedReport((prev) => data.find((r: any) => r.report_id === prev?.report_id) || data[0]);
        }
      }
      const metRes = await fetch('http://127.0.0.1:8011/reports/metrics');
      if (metRes.ok) {
        const metData = await metRes.json();
        setMetrics(metData);
      }
    } catch {
      // Fallback to in-memory demo data
    } finally {
      setLoading(false);
    }
  };

  const fetchAuditEvents = async (reportId: string) => {
    try {
      const res = await fetch(`http://127.0.0.1:8011/reports/${reportId}/audit`);
      if (res.ok) {
        const data = await res.json();
        setAuditEvents(data);
      }
    } catch {
      // Generate fallback local audit events
      setAuditEvents([
        {
          event_id: 'EVT-LOCAL-1',
          report_id: reportId,
          action: 'REPORT_CREATED',
          performed_by: 'compliance_analyst',
          details: { status: 'DRAFT' },
          timestamp: new Date().toISOString()
        }
      ]);
    }
  };

  useEffect(() => {
    fetchReports();
  }, []);

  useEffect(() => {
    if (selectedReport) {
      fetchAuditEvents(selectedReport.report_id);
    }
  }, [selectedReport?.report_id]);

  const handleSendForReview = async () => {
    if (!selectedReport) return;
    try {
      const res = await fetch(`http://127.0.0.1:8011/reports/${selectedReport.report_id}/send-for-review`, {
        method: 'POST'
      });
      if (res.ok) {
        const updated = await res.json();
        setSelectedReport(updated);
        fetchReports();
        fetchAuditEvents(updated.report_id);
      }
    } catch {
      // Local fallback state
      const updated: RegulatoryReport = { ...selectedReport, status: 'UNDER_REVIEW' };
      setSelectedReport(updated);
      setReports((prev) => prev.map((r) => (r.report_id === updated.report_id ? updated : r)));
    }
  };

  const handleReviewDecision = async (decision: 'APPROVE' | 'REJECT' | 'RETURN_TO_DRAFT') => {
    if (!selectedReport) return;
    const rationale = prompt(`Enter ${decision} review comments:`, 'Compliance standard met.');
    if (!rationale) return;

    try {
      const res = await fetch(`http://127.0.0.1:8011/reports/${selectedReport.report_id}/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          decision,
          reviewer: 'mlro_officer@finguard.internal',
          rationale
        })
      });
      if (res.ok) {
        const updated = await res.json();
        setSelectedReport(updated);
        fetchReports();
        fetchAuditEvents(updated.report_id);
      }
    } catch {
      let nextStatus: any = 'APPROVED';
      if (decision === 'REJECT') nextStatus = 'REJECTED';
      if (decision === 'RETURN_TO_DRAFT') nextStatus = 'RETURNED_TO_DRAFT';
      const updated: RegulatoryReport = {
        ...selectedReport,
        status: nextStatus,
        reviewed_by: 'mlro_officer@finguard.internal',
        review_notes: rationale,
        reviewed_at: new Date().toISOString()
      };
      setSelectedReport(updated);
      setReports((prev) => prev.map((r) => (r.report_id === updated.report_id ? updated : r)));
    }
  };

  const handleSubmitFiling = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedReport || !filingRefInput) return;

    try {
      const res = await fetch(`http://127.0.0.1:8011/reports/${selectedReport.report_id}/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          external_filing_reference: filingRefInput,
          submitted_by: 'mlro_officer@finguard.internal',
          submission_notes: 'Filed via regulatory secure portal.'
        })
      });
      if (res.ok) {
        const updated = await res.json();
        setSelectedReport(updated);
        setIsSubmitModalOpen(false);
        setFilingRefInput('');
        fetchReports();
        fetchAuditEvents(updated.report_id);
      }
    } catch {
      const updated: RegulatoryReport = {
        ...selectedReport,
        status: 'SUBMITTED',
        external_filing_reference: filingRefInput,
        submitted_at: new Date().toISOString(),
        submitted_by: 'mlro_officer@finguard.internal'
      };
      setSelectedReport(updated);
      setReports((prev) => prev.map((r) => (r.report_id === updated.report_id ? updated : r)));
      setIsSubmitModalOpen(false);
      setFilingRefInput('');
    }
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const payload = {
      report_type: formData.report_type,
      jurisdiction: formData.jurisdiction,
      customer_id: formData.customer_id,
      customer_name: formData.customer_name,
      customer_pan_or_id: formData.customer_pan_or_id,
      suspicion_narrative: formData.suspicion_narrative,
      primary_offense_category: formData.primary_offense_category,
      transaction_ids: formData.transaction_ids.split(',').map((s) => s.trim()).filter(Boolean),
      evidence_ids: formData.evidence_ids.split(',').map((s) => s.trim()).filter(Boolean),
      total_suspicious_amount: Number(formData.total_suspicious_amount),
      currency: formData.currency,
      created_by: 'compliance_analyst@finguard.internal'
    };

    try {
      const res = await fetch('http://127.0.0.1:8011/reports', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        const created: RegulatoryReport = await res.json();
        setReports((prev) => [created, ...prev]);
        setSelectedReport(created);
        setIsCreateModalOpen(false);
        fetchReports();
      }
    } catch {
      const mockCreated: RegulatoryReport = {
        report_id: `SAR-2026-${Date.now().toString().slice(-4)}`,
        report_type: formData.report_type as any,
        jurisdiction: formData.jurisdiction,
        status: 'DRAFT',
        customer_id: payload.customer_id,
        customer_name: payload.customer_name,
        customer_pan_or_id: payload.customer_pan_or_id,
        suspicion_narrative: payload.suspicion_narrative,
        primary_offense_category: payload.primary_offense_category,
        transaction_ids: payload.transaction_ids,
        evidence_ids: payload.evidence_ids,
        total_suspicious_amount: payload.total_suspicious_amount,
        currency: payload.currency,
        created_by: 'compliance_analyst@finguard.internal',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        filing_deadline: new Date(Date.now() + 1000 * 60 * 60 * 24 * 30).toISOString(),
        is_overdue: false,
        validation_result: { is_valid: true, errors: [], checked_at: new Date().toISOString() }
      };
      setReports((prev) => [mockCreated, ...prev]);
      setSelectedReport(mockCreated);
      setIsCreateModalOpen(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'SUBMITTED':
        return (
          <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" /> SUBMITTED
          </span>
        );
      case 'APPROVED':
        return (
          <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-blue-500/20 text-blue-300 border border-blue-500/30 flex items-center gap-1">
            <ShieldCheck className="w-3 h-3" /> APPROVED
          </span>
        );
      case 'UNDER_REVIEW':
        return (
          <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30 flex items-center gap-1">
            <Clock className="w-3 h-3" /> UNDER REVIEW
          </span>
        );
      case 'REJECTED':
        return (
          <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-red-500/20 text-red-300 border border-red-500/30 flex items-center gap-1">
            <XCircle className="w-3 h-3" /> REJECTED
          </span>
        );
      case 'RETURNED_TO_DRAFT':
        return (
          <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30 flex items-center gap-1">
            <RotateCcw className="w-3 h-3" /> RETURNED
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-slate-800 text-slate-300 border border-slate-700 flex items-center gap-1">
            <FileText className="w-3 h-3" /> DRAFT
          </span>
        );
    }
  };

  const filteredReports = reports.filter((r) => {
    const matchesSearch =
      r.report_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.customer_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.customer_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.primary_offense_category.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'ALL' || r.status === statusFilter;
    const matchesType = typeFilter === 'ALL' || r.report_type === typeFilter;
    return matchesSearch && matchesStatus && matchesType;
  });

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-blue-600/20 border border-blue-500/30 rounded-xl">
              <FileCheck2 className="w-6 h-6 text-blue-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
                Enterprise AML Regulatory Reporting (SAR/STR)
                <span className="text-xs font-medium px-2.5 py-0.5 rounded-full bg-blue-500/20 text-blue-300 border border-blue-500/30">
                  Phase 30
                </span>
              </h1>
              <p className="text-sm text-slate-400">
                Suspicious Activity & Transaction Reports with evidence traceability, validation, approval, and submission tracking
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => fetchReports()}
            disabled={loading}
            className="px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-sm font-medium transition flex items-center gap-2 text-slate-300"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold transition flex items-center gap-2 shadow-lg shadow-blue-600/20"
          >
            <PlusCircle className="w-4 h-4" />
            Prepare Report
          </button>
        </div>
      </div>

      {/* Advisory Banner */}
      <div className="bg-slate-900/60 border border-blue-900/40 rounded-xl p-4 flex items-start gap-3">
        <Info className="w-5 h-5 text-blue-400 shrink-0 mt-0.5" />
        <div className="text-xs text-slate-300 leading-relaxed">
          <span className="font-semibold text-blue-300">Regulatory Advisory & Segregation of Duties:</span> SAR/STR filings represent internal regulatory workflows and audit records. External submission references are captured for enterprise compliance defensibility. Filing templates do not constitute official statutory legal advice.
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3.5">
          <div className="text-xs font-medium text-slate-400">Total Filings</div>
          <div className="text-2xl font-bold text-white mt-1">{metrics.total_reports}</div>
          <div className="text-[11px] text-slate-500 mt-1">SAR / STR ledger</div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3.5">
          <div className="text-xs font-medium text-slate-400">Drafts</div>
          <div className="text-2xl font-bold text-slate-300 mt-1">{metrics.draft_count}</div>
          <div className="text-[11px] text-slate-500 mt-1">In preparation</div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3.5">
          <div className="text-xs font-medium text-amber-400">Under Review</div>
          <div className="text-2xl font-bold text-amber-400 mt-1">{metrics.under_review_count}</div>
          <div className="text-[11px] text-slate-500 mt-1">MLRO triage</div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3.5">
          <div className="text-xs font-medium text-blue-400">Approved</div>
          <div className="text-2xl font-bold text-blue-400 mt-1">{metrics.approved_count}</div>
          <div className="text-[11px] text-slate-500 mt-1">Ready to file</div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3.5">
          <div className="text-xs font-medium text-emerald-400">Submitted</div>
          <div className="text-2xl font-bold text-emerald-400 mt-1">{metrics.submitted_count}</div>
          <div className="text-[11px] text-slate-500 mt-1">Acknowledgment recvd</div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3.5">
          <div className="text-xs font-medium text-red-400">Overdue SLA</div>
          <div className="text-2xl font-bold text-red-400 mt-1">{metrics.overdue_count}</div>
          <div className="text-[11px] text-slate-500 mt-1">&gt; 30 day deadline</div>
        </div>
      </div>

      {/* Main Grid: Reports List (7 cols) + Detail View (5 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Filings Queue */}
        <div className="lg:col-span-7 space-y-4">
          {/* Filter Bar */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3 flex flex-wrap items-center justify-between gap-3">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-500" />
              <input
                type="text"
                placeholder="Search Report ID, Customer, PAN, Category..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-9 pr-3 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500"
              />
            </div>
            <div className="flex items-center gap-2">
              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className="bg-slate-950 border border-slate-800 text-xs text-slate-300 rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-blue-500"
              >
                <option value="ALL">All Types</option>
                <option value="SAR">SAR</option>
                <option value="STR">STR</option>
              </select>

              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="bg-slate-950 border border-slate-800 text-xs text-slate-300 rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-blue-500"
              >
                <option value="ALL">All Statuses</option>
                <option value="DRAFT">Draft</option>
                <option value="UNDER_REVIEW">Under Review</option>
                <option value="APPROVED">Approved</option>
                <option value="SUBMITTED">Submitted</option>
                <option value="REJECTED">Rejected</option>
                <option value="RETURNED_TO_DRAFT">Returned</option>
              </select>
            </div>
          </div>

          {/* List Table */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
            <div className="px-4 py-3 border-b border-slate-800 flex items-center justify-between">
              <div className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                Regulatory Filings Register ({filteredReports.length})
              </div>
              <div className="text-xs text-slate-500">Statutory reporting track</div>
            </div>

            <div className="divide-y divide-slate-800/60 max-h-[600px] overflow-y-auto">
              {filteredReports.length === 0 ? (
                <div className="p-8 text-center text-slate-500 text-sm">
                  No regulatory reports match the filter criteria.
                </div>
              ) : (
                filteredReports.map((r) => {
                  const isSelected = selectedReport?.report_id === r.report_id;
                  return (
                    <div
                      key={r.report_id}
                      onClick={() => setSelectedReport(r)}
                      className={`p-4 transition cursor-pointer flex items-center justify-between gap-4 hover:bg-slate-800/40 ${
                        isSelected ? 'bg-blue-950/30 border-l-4 border-blue-500' : ''
                      }`}
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-sm font-bold text-white">
                            {r.report_id}
                          </span>
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-blue-300 border border-slate-700">
                            {r.report_type} • {r.jurisdiction}
                          </span>
                          {getStatusBadge(r.status)}
                        </div>
                        <div className="text-xs text-slate-300 font-medium">
                          {r.customer_name} <span className="text-slate-500 font-mono">({r.customer_id})</span>
                        </div>
                        <div className="text-[11px] text-slate-400">
                          Offense: <span className="text-slate-200">{r.primary_offense_category}</span>
                        </div>
                      </div>

                      <div className="text-right space-y-1">
                        <div className="text-sm font-bold text-white">
                          ₹{r.total_suspicious_amount.toLocaleString()}
                        </div>
                        <div className="text-[11px] text-slate-400 flex items-center justify-end gap-1">
                          <Clock className="w-3 h-3 text-slate-500" />
                          <span>Deadline: {new Date(r.filing_deadline).toLocaleDateString()}</span>
                        </div>
                        {r.external_filing_reference && (
                          <div className="text-[10px] font-mono text-emerald-400">
                            Ack: {r.external_filing_reference}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Report Dossier & Workflow Actions */}
        <div className="lg:col-span-5 space-y-4">
          {selectedReport ? (
            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-5">
              {/* Header */}
              <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                <div>
                  <div className="text-xs uppercase tracking-wider text-slate-400 font-medium">
                    Regulatory Filing Dossier
                  </div>
                  <div className="text-lg font-bold text-white font-mono mt-0.5">
                    {selectedReport.report_id}
                  </div>
                </div>
                {getStatusBadge(selectedReport.status)}
              </div>

              {/* Subject & Summary Info */}
              <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-4 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400">Customer Subject:</span>
                  <span className="font-bold text-white">{selectedReport.customer_name}</span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400">Customer ID:</span>
                  <span className="font-mono text-slate-300">{selectedReport.customer_id}</span>
                </div>
                {selectedReport.customer_pan_or_id && (
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-400">PAN / Tax Reference:</span>
                    <span className="font-mono text-slate-300">{selectedReport.customer_pan_or_id}</span>
                  </div>
                )}
                <div className="flex items-center justify-between text-xs pt-1 border-t border-slate-800/80">
                  <span className="text-slate-400">Suspicious Amount:</span>
                  <span className="font-extrabold text-emerald-400 text-sm">
                    ₹{selectedReport.total_suspicious_amount.toLocaleString()}
                  </span>
                </div>
              </div>

              {/* Suspicion Narrative */}
              <div className="space-y-1.5">
                <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Factual Suspicion Narrative
                </div>
                <div className="p-3 bg-slate-950/80 border border-slate-800 rounded-lg text-xs text-slate-300 leading-relaxed max-h-32 overflow-y-auto">
                  {selectedReport.suspicion_narrative}
                </div>
              </div>

              {/* Linked Evidence & Transactions */}
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-lg space-y-1">
                  <div className="text-[11px] font-semibold text-slate-400 flex items-center gap-1">
                    <FileText className="w-3 h-3 text-blue-400" />
                    Transactions ({selectedReport.transaction_ids.length})
                  </div>
                  <div className="text-xs font-mono text-slate-300 truncate">
                    {selectedReport.transaction_ids.join(', ')}
                  </div>
                </div>

                <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-lg space-y-1">
                  <div className="text-[11px] font-semibold text-slate-400 flex items-center gap-1">
                    <ShieldCheck className="w-3 h-3 text-teal-400" />
                    Evidence IDs ({selectedReport.evidence_ids.length})
                  </div>
                  <div className="text-xs font-mono text-slate-300 truncate">
                    {selectedReport.evidence_ids.length > 0
                      ? selectedReport.evidence_ids.join(', ')
                      : 'None'}
                  </div>
                </div>
              </div>

              {/* External Submission Info if Submitted */}
              {selectedReport.status === 'SUBMITTED' && (
                <div className="p-3 bg-emerald-950/30 border border-emerald-800/50 rounded-xl space-y-1">
                  <div className="text-xs font-bold text-emerald-300 flex items-center gap-1.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    Regulator Submission Recorded
                  </div>
                  <div className="text-xs text-slate-300">
                    Acknowledgment Reference:{' '}
                    <span className="font-mono font-semibold text-white">
                      {selectedReport.external_filing_reference}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-400">
                    Submitted on: {new Date(selectedReport.submitted_at || '').toLocaleString()} by{' '}
                    {selectedReport.submitted_by}
                  </div>
                </div>
              )}

              {/* Workflow Actions */}
              <div className="pt-2 border-t border-slate-800 space-y-3">
                <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Compliance Workflow Actions
                </div>

                {(selectedReport.status === 'DRAFT' || selectedReport.status === 'RETURNED_TO_DRAFT') && (
                  <button
                    onClick={handleSendForReview}
                    className="w-full py-2 px-4 rounded-lg bg-blue-600 hover:bg-blue-500 font-semibold text-xs text-white transition flex items-center justify-center gap-2 shadow-lg shadow-blue-600/20"
                  >
                    <Send className="w-3.5 h-3.5" />
                    Send for Compliance Review
                  </button>
                )}

                {selectedReport.status === 'UNDER_REVIEW' && (
                  <div className="grid grid-cols-3 gap-2">
                    <button
                      onClick={() => handleReviewDecision('APPROVE')}
                      className="py-2 px-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 font-semibold text-xs text-white transition flex items-center justify-center gap-1"
                    >
                      <CheckCircle2 className="w-3 h-3" /> Approve
                    </button>
                    <button
                      onClick={() => handleReviewDecision('RETURN_TO_DRAFT')}
                      className="py-2 px-2 rounded-lg bg-purple-600 hover:bg-purple-500 font-semibold text-xs text-white transition flex items-center justify-center gap-1"
                    >
                      <RotateCcw className="w-3 h-3" /> Return
                    </button>
                    <button
                      onClick={() => handleReviewDecision('REJECT')}
                      className="py-2 px-2 rounded-lg bg-red-600 hover:bg-red-500 font-semibold text-xs text-white transition flex items-center justify-center gap-1"
                    >
                      <XCircle className="w-3 h-3" /> Reject
                    </button>
                  </div>
                )}

                {selectedReport.status === 'APPROVED' && (
                  <button
                    onClick={() => setIsSubmitModalOpen(true)}
                    className="w-full py-2 px-4 rounded-lg bg-emerald-600 hover:bg-emerald-500 font-semibold text-xs text-white transition flex items-center justify-center gap-2 shadow-lg shadow-emerald-600/20"
                  >
                    <Send className="w-3.5 h-3.5" />
                    Record External Submission
                  </button>
                )}
              </div>

              {/* Audit Trail List */}
              <div className="pt-2 border-t border-slate-800 space-y-2">
                <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1">
                  <History className="w-3.5 h-3.5 text-slate-400" />
                  Audit Trail History ({auditEvents.length})
                </div>
                <div className="divide-y divide-slate-800/60 max-h-40 overflow-y-auto text-xs">
                  {auditEvents.map((ev) => (
                    <div key={ev.event_id} className="py-2 flex items-start justify-between gap-2">
                      <div>
                        <div className="font-semibold text-slate-200">{ev.action}</div>
                        <div className="text-[11px] text-slate-500">By: {ev.performed_by}</div>
                      </div>
                      <div className="text-[10px] text-slate-400 whitespace-nowrap">
                        {new Date(ev.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="p-8 text-center text-slate-500 bg-slate-900/40 rounded-xl border border-slate-800">
              Select a regulatory filing to inspect dossier.
            </div>
          )}
        </div>
      </div>

      {/* Create Report Modal */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-xl w-full p-6 space-y-4 shadow-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <FileCheck2 className="w-5 h-5 text-blue-400" />
                Prepare SAR / STR Regulatory Filing
              </h2>
              <button
                onClick={() => setIsCreateModalOpen(false)}
                className="text-slate-400 hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateSubmit} className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-slate-400 block mb-1">Report Type</label>
                  <select
                    value={formData.report_type}
                    onChange={(e) => setFormData({ ...formData, report_type: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200"
                  >
                    <option value="SAR">SAR (Suspicious Activity Report)</option>
                    <option value="STR">STR (Suspicious Transaction Report)</option>
                  </select>
                </div>

                <div>
                  <label className="text-slate-400 block mb-1">Target Jurisdiction</label>
                  <select
                    value={formData.jurisdiction}
                    onChange={(e) => setFormData({ ...formData, jurisdiction: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200"
                  >
                    <option value="FIU_IND">FIU-IND (India)</option>
                    <option value="FINCEN">FinCEN (United States)</option>
                    <option value="FCA">FCA (United Kingdom)</option>
                    <option value="GLOBAL">Global Framework</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
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
                <div>
                  <label className="text-slate-400 block mb-1">Customer Legal Name</label>
                  <input
                    type="text"
                    required
                    value={formData.customer_name}
                    onChange={(e) => setFormData({ ...formData, customer_name: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-slate-400 block mb-1">Customer PAN / Tax ID</label>
                  <input
                    type="text"
                    value={formData.customer_pan_or_id}
                    onChange={(e) => setFormData({ ...formData, customer_pan_or_id: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 font-mono"
                  />
                </div>
                <div>
                  <label className="text-slate-400 block mb-1">Primary Offense Category</label>
                  <input
                    type="text"
                    required
                    value={formData.primary_offense_category}
                    onChange={(e) => setFormData({ ...formData, primary_offense_category: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200"
                  />
                </div>
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Suspicion Factual Narrative (min 20 chars)</label>
                <textarea
                  rows={3}
                  required
                  value={formData.suspicion_narrative}
                  onChange={(e) => setFormData({ ...formData, suspicion_narrative: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 leading-relaxed"
                />
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Linked Transactions (comma-separated)</label>
                <input
                  type="text"
                  required
                  value={formData.transaction_ids}
                  onChange={(e) => setFormData({ ...formData, transaction_ids: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 font-mono"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-slate-400 block mb-1">Total Suspicious Amount (₹)</label>
                  <input
                    type="number"
                    min="1"
                    required
                    value={formData.total_suspicious_amount}
                    onChange={(e) => setFormData({ ...formData, total_suspicious_amount: Number(e.target.value) })}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 font-mono"
                  />
                </div>
                <div>
                  <label className="text-slate-400 block mb-1">Linked Evidence IDs (optional)</label>
                  <input
                    type="text"
                    value={formData.evidence_ids}
                    onChange={(e) => setFormData({ ...formData, evidence_ids: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 font-mono"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsCreateModalOpen(false)}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 font-semibold text-white shadow-lg shadow-blue-600/20"
                >
                  Create Regulatory Draft
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Record External Submission Modal */}
      {isSubmitModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <Send className="w-4 h-4 text-emerald-400" />
                Record External Regulatory Submission
              </h2>
              <button
                onClick={() => setIsSubmitModalOpen(false)}
                className="text-slate-400 hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSubmitFiling} className="space-y-4 text-xs">
              <div>
                <label className="text-slate-400 block mb-1">
                  Regulator Acknowledgment / Filing Number
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. FIU-IND-ACK-2026-99014"
                  value={filingRefInput}
                  onChange={(e) => setFilingRefInput(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 font-mono"
                />
              </div>

              <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-lg text-[11px] text-slate-400">
                Filing for <span className="font-semibold text-white">{selectedReport?.report_id}</span> ({selectedReport?.customer_name}). Submitter: mlro_officer@finguard.internal
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsSubmitModalOpen(false)}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 font-semibold text-white shadow-lg shadow-emerald-600/20"
                >
                  Record Submission
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default RegulatoryReportingPage;

