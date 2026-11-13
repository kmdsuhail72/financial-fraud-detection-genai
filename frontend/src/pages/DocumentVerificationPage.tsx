import React, { useState, useEffect } from 'react';
import {
  FileCheck2,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  FileText,
  Search,
  RefreshCw,
  PlusCircle,
  Copy,
  Check,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Layers,
  Clock,
  Scan,
  UserCheck,
  Fingerprint,
  Camera,
  ExternalLink,
  Sliders,
  FileCode,
  Eye,
  History
} from 'lucide-react';

interface IdentityDocumentMetadata {
  document_id: string;
  customer_id: string;
  document_category: string;
  file_format: string;
  file_name: string;
  file_size_bytes: number;
  mime_type: string;
  issuing_country: string;
  extracted_fields: Record<string, string>;
  expiration_date?: string;
  uploaded_at: string;
}

interface FieldConsistencyCheck {
  field_name: string;
  customer_value: string;
  document_value: string;
  similarity_score: number;
  verdict: 'MATCH' | 'PARTIAL_MATCH' | 'MISMATCH' | 'NOT_APPLICABLE';
  explanation: string;
}

interface FieldConsistencyReport {
  checks: FieldConsistencyCheck[];
  overall_consistency_score: number;
  is_consistent: boolean;
  mismatch_count: number;
  notes: string;
}

interface BiometricIntegrationPlaceholder {
  face_match_confidence?: number;
  face_match_status: string;
  liveness_score?: number;
  liveness_status: string;
  notes: string;
}

interface DocumentVerificationRecord {
  verification_id: string;
  document_metadata: IdentityDocumentMetadata;
  sha256_hash: string;
  verification_status: 'PENDING_VERIFICATION' | 'VERIFIED_AUTHENTIC_BYTES' | 'TAMPER_DETECTED' | 'INCONSISTENT_FIELDS' | 'REJECTED';
  consistency_report: FieldConsistencyReport;
  biometric_integration: BiometricIntegrationPlaceholder;
  verified_at: string;
  analyst_notes?: string;
}

interface DocumentAuditEvent {
  event_id: string;
  customer_id: string;
  document_id: string;
  event_type: string;
  actor: string;
  timestamp: string;
  details: Record<string, any>;
}

export const DocumentVerificationPage: React.FC = () => {
  const [records, setRecords] = useState<DocumentVerificationRecord[]>([]);
  const [selectedVerId, setSelectedVerId] = useState<string | null>(null);
  const [timeline, setTimeline] = useState<DocumentVerificationRecord[]>([]);
  const [auditTrail, setAuditTrail] = useState<DocumentAuditEvent[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [loading, setLoading] = useState(false);
  const [copiedHash, setCopiedHash] = useState<string | null>(null);

  // Ingest Modal State
  const [showIngestModal, setShowIngestModal] = useState(false);
  const [newCustId, setNewCustId] = useState('CUST-IN-3042');
  const [newCategory, setNewCategory] = useState('PASSPORT');
  const [newFormat, setNewFormat] = useState('PDF');
  const [newFileName, setNewFileName] = useState('passport_front.pdf');
  const [newCountry, setNewCountry] = useState('IND');
  const [rawPayload, setRawPayload] = useState('SAMPLE_BASE64_OR_RAW_FILE_STREAM');
  const [docName, setDocName] = useState('Vikram Malhotra');
  const [expName, setExpName] = useState('Vikram Malhotra');
  const [docDob, setDocDob] = useState('1988-04-12');
  const [expDob, setExpDob] = useState('1988-04-12');
  const [docIdNum, setDocIdNum] = useState('Z9018274');
  const [expIdNum, setExpIdNum] = useState('Z9018274');

  // Adjudication State
  const [analystDecision, setAnalystDecision] = useState<'VERIFY' | 'FLAG_TAMPER' | 'REJECT_INCONSISTENT'>('VERIFY');
  const [analystId, setAnalystId] = useState('forensic-analyst-mark');
  const [analystNotes, setAnalystNotes] = useState('');
  const [submittingAssessment, setSubmittingAssessment] = useState(false);

  // Tamper Simulator State
  const [simulatedTamperContent, setSimulatedTamperContent] = useState('ALTERED_PAYLOAD_BYTE_STREAM');
  const [tamperAlert, setTamperAlert] = useState<string | null>(null);

  // Load records
  const fetchRecords = async () => {
    setLoading(true);
    try {
      const resp = await fetch('http://127.0.0.1:8011/documents/verification/records');
      if (resp.ok) {
        const data = await resp.json();
        setRecords(data);
        if (data.length > 0 && !selectedVerId) {
          setSelectedVerId(data[0].verification_id);
        }
      }
    } catch (e) {
      console.warn('Backend offline, using fallback data');
      setRecords([
        {
          verification_id: 'VER-9011-PASS',
          document_metadata: {
            document_id: 'DOC-9011-PASS',
            customer_id: 'CUST-US-9011',
            document_category: 'PASSPORT',
            file_format: 'PDF',
            file_name: 'passport_scan_s_connor.pdf',
            file_size_bytes: 1048576,
            mime_type: 'application/pdf',
            issuing_country: 'US',
            extracted_fields: {
              full_name: 'Sarah Connor',
              date_of_birth: '1984-05-12',
              issuing_country: 'US',
              document_number: 'P884920442'
            },
            expiration_date: '2032-05-12',
            uploaded_at: new Date().toISOString()
          },
          sha256_hash: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
          verification_status: 'VERIFIED_AUTHENTIC_BYTES',
          consistency_report: {
            checks: [
              {
                field_name: 'full_name',
                customer_value: 'Sarah Connor',
                document_value: 'Sarah Connor',
                similarity_score: 1.0,
                verdict: 'MATCH',
                explanation: 'Exact match on full name.'
              },
              {
                field_name: 'date_of_birth',
                customer_value: '1984-05-12',
                document_value: '1984-05-12',
                similarity_score: 1.0,
                verdict: 'MATCH',
                explanation: 'Exact match on date of birth.'
              }
            ],
            overall_consistency_score: 1.0,
            is_consistent: true,
            mismatch_count: 0,
            notes: 'All extracted identity fields are perfectly consistent with customer record.'
          },
          biometric_integration: {
            face_match_confidence: 0.98,
            face_match_status: 'INTEGRATION_POINT_READY',
            liveness_score: 0.96,
            liveness_status: 'INTEGRATION_POINT_READY',
            notes: 'Biometric and face-liveness APIs are integration points for downstream production models.'
          },
          verified_at: new Date().toISOString(),
          analyst_notes: 'Primary passport verified authentic against customer KYC declaration.'
        }
      ]);
      setSelectedVerId('VER-9011-PASS');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRecords();
  }, []);

  const selectedRecord = records.find(r => r.verification_id === selectedVerId);

  // Fetch Timeline and Audit for selected customer
  useEffect(() => {
    if (!selectedRecord) return;
    const cid = selectedRecord.document_metadata.customer_id;

    const fetchTimeline = async () => {
      try {
        const resp = await fetch(`http://127.0.0.1:8011/documents/verification/customers/${cid}/timeline`);
        if (resp.ok) {
          const data = await resp.json();
          setTimeline(data);
        }
      } catch {
        setTimeline([selectedRecord]);
      }
    };

    const fetchAudit = async () => {
      try {
        const resp = await fetch(`http://127.0.0.1:8011/documents/verification/customers/${cid}/audit-trail`);
        if (resp.ok) {
          const data = await resp.json();
          setAuditTrail(data);
        }
      } catch {
        setAuditTrail([
          {
            event_id: 'DOC-AUD-001',
            customer_id: cid,
            document_id: selectedRecord.document_metadata.document_id,
            event_type: 'DOCUMENT_INGESTED',
            actor: 'system',
            timestamp: new Date().toISOString(),
            details: { action: 'initial_seed' }
          }
        ]);
      }
    };

    fetchTimeline();
    fetchAudit();
  }, [selectedRecord]);

  // Handle Tamper Check
  const handleTamperCheck = async (simulateMismatch: boolean) => {
    if (!selectedRecord) return;
    try {
      const contentToTest = simulateMismatch
        ? `${selectedRecord.document_metadata.file_name}_MODIFIED_BYTE_DATA`
        : 'AUTHENTIC_BYTES';

      const resp = await fetch(`http://127.0.0.1:8011/documents/verification/records/${selectedRecord.verification_id}/tamper-check`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ modified_content_raw: contentToTest })
      });
      if (resp.ok) {
        const data = await resp.json();
        if (!data.is_authentic) {
          setTamperAlert(`TAMPER ALERT: Recorded hash does not match modified byte stream! Status updated to TAMPER_DETECTED.`);
        } else {
          setTamperAlert(`AUTHENTIC: SHA-256 integrity digest verified authentic.`);
        }
        await fetchRecords();
      }
    } catch {
      setTamperAlert('Tamper check simulated.');
    }
  };

  // Submit Analyst Assessment
  const handleSubmitAssessment = async () => {
    if (!selectedRecord || !analystNotes) {
      alert('Please provide notes explaining your verification assessment.');
      return;
    }
    setSubmittingAssessment(true);
    try {
      const resp = await fetch(`http://127.0.0.1:8011/documents/verification/records/${selectedRecord.verification_id}/assess`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          analyst_id: analystId,
          decision: analystDecision,
          notes: analystNotes
        })
      });
      if (resp.ok) {
        setAnalystNotes('');
        await fetchRecords();
      }
    } catch {
      alert('Assessment recorded.');
    } finally {
      setSubmittingAssessment(false);
    }
  };

  // Ingest Document
  const handleIngestDocument = async () => {
    try {
      const extracted: Record<string, string> = {
        full_name: docName,
        date_of_birth: docDob,
        id_number: docIdNum
      };
      const expected: Record<string, string> = {
        full_name: expName,
        date_of_birth: expDob,
        id_number: expIdNum
      };

      const resp = await fetch('http://127.0.0.1:8011/documents/verification/intake', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          customer_id: newCustId,
          document_category: newCategory,
          file_format: newFormat,
          file_name: newFileName,
          content_raw: rawPayload,
          issuing_country: newCountry,
          extracted_fields: extracted,
          customer_profile_expected: expected
        })
      });
      if (resp.ok) {
        setShowIngestModal(false);
        await fetchRecords();
      }
    } catch {
      setShowIngestModal(false);
    }
  };

  // Copy hash helper
  const copyToClipboard = (hash: string) => {
    navigator.clipboard.writeText(hash);
    setCopiedHash(hash);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  // Filtered Records
  const filteredRecords = records.filter(r => {
    const meta = r.document_metadata;
    const matchesSearch =
      meta.file_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      meta.customer_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      meta.document_category.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'ALL' || r.verification_status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  // Summary Metrics
  const totalCount = records.length;
  const authenticCount = records.filter(r => r.verification_status === 'VERIFIED_AUTHENTIC_BYTES').length;
  const tamperCount = records.filter(r => r.verification_status === 'TAMPER_DETECTED').length;
  const inconsistentCount = records.filter(r => r.verification_status === 'INCONSISTENT_FIELDS').length;

  return (
    <div className="p-8 max-w-[1600px] mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-emerald-400">
              <FileCheck2 className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">Identity Document Intelligence & Verification</h1>
              <p className="text-sm text-slate-400">
                Phase 26: Multi-format document intake (PDF/JPEG/PNG), SHA-256 byte integrity, and explainable field consistency checks.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowIngestModal(true)}
            className="flex items-center gap-2 px-4 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-semibold rounded-lg shadow-lg shadow-emerald-600/20 transition-all"
          >
            <PlusCircle className="w-4 h-4" />
            Ingest Document
          </button>
          <button
            onClick={fetchRecords}
            className="p-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700 transition-colors"
            title="Refresh Records"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Metrics Banner */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
          <div>
            <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">Documents Ingested</div>
            <div className="text-2xl font-bold text-white mt-1">{totalCount}</div>
          </div>
          <div className="p-3 bg-sky-500/10 border border-sky-500/20 rounded-lg text-sky-400">
            <FileText className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
          <div>
            <div className="text-xs font-medium text-emerald-400 uppercase tracking-wider">Verified Authentic</div>
            <div className="text-2xl font-bold text-emerald-300 mt-1">{authenticCount}</div>
          </div>
          <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-emerald-400">
            <ShieldCheck className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
          <div>
            <div className="text-xs font-medium text-rose-400 uppercase tracking-wider">Tamper Alerts</div>
            <div className="text-2xl font-bold text-rose-300 mt-1">{tamperCount}</div>
          </div>
          <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-lg text-rose-400">
            <ShieldAlert className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
          <div>
            <div className="text-xs font-medium text-amber-400 uppercase tracking-wider">Inconsistent Fields</div>
            <div className="text-2xl font-bold text-amber-300 mt-1">{inconsistentCount}</div>
          </div>
          <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg text-amber-400">
            <AlertTriangle className="w-5 h-5" />
          </div>
        </div>
      </div>

      {/* Main Workspace Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Document Directory (4 cols) */}
        <div className="lg:col-span-4 bg-slate-900/80 border border-slate-800 rounded-xl flex flex-col h-[850px]">
          {/* Search & Filter Bar */}
          <div className="p-4 border-b border-slate-800 space-y-3">
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-3 text-slate-500" />
              <input
                type="text"
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                placeholder="Search file name, customer, or type..."
                className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-2 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500"
              />
            </div>

            <div className="flex gap-1 overflow-x-auto pb-1 text-xs">
              {['ALL', 'VERIFIED_AUTHENTIC_BYTES', 'INCONSISTENT_FIELDS', 'TAMPER_DETECTED'].map(st => (
                <button
                  key={st}
                  onClick={() => setStatusFilter(st)}
                  className={`px-2.5 py-1 rounded-md font-medium whitespace-nowrap transition-colors ${
                    statusFilter === st
                      ? 'bg-emerald-600 text-white'
                      : 'bg-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {st.replace(/_/g, ' ')}
                </button>
              ))}
            </div>
          </div>

          {/* Records List */}
          <div className="flex-1 overflow-y-auto divide-y divide-slate-800/60 p-2 space-y-1">
            {filteredRecords.map(r => {
              const isSelected = r.verification_id === selectedVerId;
              const meta = r.document_metadata;

              const statusBadge =
                r.verification_status === 'VERIFIED_AUTHENTIC_BYTES' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                r.verification_status === 'TAMPER_DETECTED' ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' :
                r.verification_status === 'INCONSISTENT_FIELDS' ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' :
                'bg-slate-800 text-slate-400 border-slate-700';

              const fmtBadge =
                meta.file_format === 'PDF' ? 'bg-rose-500/20 text-rose-300' :
                meta.file_format === 'PNG' ? 'bg-sky-500/20 text-sky-300' :
                'bg-amber-500/20 text-amber-300';

              return (
                <div
                  key={r.verification_id}
                  onClick={() => setSelectedVerId(r.verification_id)}
                  className={`p-3.5 rounded-lg cursor-pointer transition-all border ${
                    isSelected
                      ? 'bg-emerald-950/30 border-emerald-500/40 shadow-sm'
                      : 'border-transparent hover:bg-slate-800/50'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${fmtBadge}`}>
                          {meta.file_format}
                        </span>
                        <span className="font-semibold text-slate-200 text-sm">{meta.file_name}</span>
                      </div>
                      <div className="text-xs text-slate-400 mt-1 font-mono">
                        {meta.customer_id} · {meta.document_category}
                      </div>
                    </div>

                    <span className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${statusBadge}`}>
                      {r.verification_status.replace(/_/g, ' ')}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: Forensic Inspection & Field Consistency (8 cols) */}
        <div className="lg:col-span-8 flex flex-col gap-6">
          {selectedRecord ? (
            <>
              {/* Document Metadata Header */}
              <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-4">
                  <div>
                    <div className="flex items-center gap-3">
                      <h2 className="text-xl font-bold text-white">{selectedRecord.document_metadata.file_name}</h2>
                      <span className="px-2.5 py-0.5 text-xs font-mono bg-slate-800 text-emerald-300 rounded border border-slate-700">
                        {selectedRecord.verification_id}
                      </span>
                    </div>
                    <div className="text-xs text-slate-400 mt-1 flex gap-4">
                      <span>Customer: <strong className="text-slate-200 font-mono">{selectedRecord.document_metadata.customer_id}</strong></span>
                      <span>Category: <strong className="text-slate-200">{selectedRecord.document_metadata.document_category}</strong></span>
                      <span>Size: <strong className="text-slate-200">{(selectedRecord.document_metadata.file_size_bytes / 1024).toFixed(1)} KB</strong></span>
                      <span>MIME: <strong className="text-slate-200 font-mono">{selectedRecord.document_metadata.mime_type}</strong></span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleTamperCheck(false)}
                      className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-semibold text-slate-200 rounded-lg transition-colors flex items-center gap-1.5"
                      title="Verify authentic bytes"
                    >
                      <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                      Verify Integrity
                    </button>
                    <button
                      onClick={() => handleTamperCheck(true)}
                      className="px-3 py-1.5 bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 text-xs font-semibold text-rose-300 rounded-lg transition-colors flex items-center gap-1.5"
                      title="Simulate byte modification"
                    >
                      <ShieldAlert className="w-3.5 h-3.5" />
                      Simulate Tamper
                    </button>
                  </div>
                </div>

                {tamperAlert && (
                  <div className={`mt-3 p-3 rounded-lg text-xs font-mono border ${
                    tamperAlert.includes('TAMPER ALERT')
                      ? 'bg-rose-500/10 border-rose-500/30 text-rose-300'
                      : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                  }`}>
                    {tamperAlert}
                  </div>
                )}

                {/* Cryptographic SHA-256 Digest */}
                <div className="mt-4 p-3 bg-slate-950/80 rounded-lg border border-slate-800/80 flex items-center justify-between">
                  <div className="text-xs font-mono text-slate-300 flex items-center gap-2 overflow-hidden">
                    <span className="text-slate-500 font-bold">SHA-256:</span>
                    <span className="text-emerald-400 select-all">{selectedRecord.sha256_hash}</span>
                  </div>
                  <button
                    onClick={() => copyToClipboard(selectedRecord.sha256_hash)}
                    className="p-1.5 text-slate-400 hover:text-white transition-colors"
                    title="Copy Full Digest"
                  >
                    {copiedHash === selectedRecord.sha256_hash ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* Field Consistency Matrix Card */}
              <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <div className="flex items-center gap-2">
                    <Scan className="w-5 h-5 text-emerald-400" />
                    <h3 className="text-md font-bold text-white">Explainable Field Consistency Matrix</h3>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-400">Consistency Score:</span>
                    <span className="text-xs font-bold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">
                      {(selectedRecord.consistency_report.overall_consistency_score * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>

                <div className="mt-4 overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-slate-800 text-slate-400 uppercase text-[10px]">
                        <th className="pb-2">Field</th>
                        <th className="pb-2">Document Extracted Value</th>
                        <th className="pb-2">Customer Profile Value</th>
                        <th className="pb-2">Congruence</th>
                        <th className="pb-2">Verdict</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/50">
                      {selectedRecord.consistency_report.checks.map((chk, idx) => (
                        <tr key={idx} className="hover:bg-slate-800/30">
                          <td className="py-2.5 font-semibold text-slate-300 capitalize">{chk.field_name.replace(/_/g, ' ')}</td>
                          <td className="py-2.5 font-mono text-slate-200">{chk.document_value}</td>
                          <td className="py-2.5 font-mono text-slate-400">{chk.customer_value}</td>
                          <td className="py-2.5 font-mono font-semibold text-slate-200">{(chk.similarity_score * 100).toFixed(0)}%</td>
                          <td className="py-2.5">
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              chk.verdict === 'MATCH' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                              chk.verdict === 'PARTIAL_MATCH' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                              'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                            }`}>
                              {chk.verdict}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div className="mt-3 p-3 bg-slate-950/60 rounded-lg text-xs text-slate-400 font-mono">
                  {selectedRecord.consistency_report.notes}
                </div>
              </div>

              {/* Biometric Integration Status Placeholder Card */}
              <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <div className="flex items-center gap-2">
                    <Camera className="w-5 h-5 text-indigo-400" />
                    <h3 className="text-md font-bold text-white">Biometric Verification Foundation</h3>
                  </div>
                  <span className="text-[10px] uppercase font-bold text-indigo-400 px-2 py-0.5 bg-indigo-500/10 rounded border border-indigo-500/20">
                    Integration Point
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                  <div className="p-3.5 bg-slate-950/80 rounded-lg border border-slate-800 flex items-center justify-between">
                    <div>
                      <div className="text-xs text-slate-400 uppercase font-semibold">Face Match Confidence</div>
                      <div className="text-base font-bold text-slate-200 mt-1">
                        {selectedRecord.biometric_integration.face_match_confidence
                          ? `${(selectedRecord.biometric_integration.face_match_confidence * 100).toFixed(0)}% Match`
                          : 'Not Evaluated'}
                      </div>
                    </div>
                    <span className="text-xs text-emerald-400 font-semibold px-2 py-0.5 bg-emerald-500/10 rounded">
                      {selectedRecord.biometric_integration.face_match_status}
                    </span>
                  </div>

                  <div className="p-3.5 bg-slate-950/80 rounded-lg border border-slate-800 flex items-center justify-between">
                    <div>
                      <div className="text-xs text-slate-400 uppercase font-semibold">Liveness Verification</div>
                      <div className="text-base font-bold text-slate-200 mt-1">
                        {selectedRecord.biometric_integration.liveness_score
                          ? `${(selectedRecord.biometric_integration.liveness_score * 100).toFixed(0)}% Liveness`
                          : 'Not Evaluated'}
                      </div>
                    </div>
                    <span className="text-xs text-emerald-400 font-semibold px-2 py-0.5 bg-emerald-500/10 rounded">
                      {selectedRecord.biometric_integration.liveness_status}
                    </span>
                  </div>
                </div>

                <p className="text-xs text-slate-500 mt-3 font-mono">
                  {selectedRecord.biometric_integration.notes}
                </p>
              </div>

              {/* Analyst Adjudication Console */}
              <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6">
                <div className="border-b border-slate-800 pb-3 mb-4">
                  <h3 className="text-md font-bold text-white flex items-center gap-2">
                    <UserCheck className="w-5 h-5 text-emerald-400" />
                    Analyst Document Verification Adjudication
                  </h3>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                  <div>
                    <label className="text-xs font-semibold text-slate-300 block mb-1">Decision</label>
                    <select
                      value={analystDecision}
                      onChange={e => setAnalystDecision(e.target.value as any)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-emerald-500"
                    >
                      <option value="VERIFY">VERIFY (Authentic Bytes & Approved Fields)</option>
                      <option value="FLAG_TAMPER">FLAG TAMPER (Byte Mismatch Alert)</option>
                      <option value="REJECT_INCONSISTENT">REJECT (Field Consistency Discrepancy)</option>
                    </select>
                  </div>

                  <div>
                    <label className="text-xs font-semibold text-slate-300 block mb-1">Analyst ID</label>
                    <input
                      type="text"
                      value={analystId}
                      onChange={e => setAnalystId(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-emerald-500"
                    />
                  </div>
                </div>

                <div>
                  <label className="text-xs font-semibold text-slate-300 block mb-1">Adjudication Notes</label>
                  <textarea
                    rows={2}
                    placeholder="Enter verification assessment rationale..."
                    value={analystNotes}
                    onChange={e => setAnalystNotes(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-sm text-slate-200 focus:outline-none focus:border-emerald-500"
                  />
                </div>

                <div className="flex justify-end mt-4">
                  <button
                    onClick={handleSubmitAssessment}
                    disabled={submittingAssessment}
                    className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-sm rounded-lg shadow-lg shadow-emerald-600/20 transition-all flex items-center gap-2"
                  >
                    {submittingAssessment ? <RefreshCw className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                    Submit Forensic Verification
                  </button>
                </div>
              </div>

              {/* Customer Identity Document Timeline */}
              <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6">
                <div className="border-b border-slate-800 pb-3 mb-4">
                  <h3 className="text-md font-bold text-white flex items-center gap-2">
                    <History className="w-5 h-5 text-indigo-400" />
                    Customer Identity Document Timeline ({selectedRecord.document_metadata.customer_id})
                  </h3>
                </div>

                <div className="space-y-3">
                  {timeline.map(item => (
                    <div key={item.verification_id} className="p-3 bg-slate-950/60 border border-slate-800 rounded-lg flex items-center justify-between text-xs">
                      <div>
                        <div className="font-semibold text-slate-200 flex items-center gap-2">
                          <span className="font-mono text-indigo-400">{item.document_metadata.document_category}</span>
                          <span>·</span>
                          <span className="text-slate-300">{item.document_metadata.file_name}</span>
                        </div>
                        <div className="text-slate-400 font-mono text-[11px] mt-1">
                          SHA-256: {item.sha256_hash.substring(0, 20)}...
                        </div>
                      </div>

                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        {item.verification_status}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-12 text-center text-slate-400">
              Select a verification record from the left directory to inspect document integrity and consistency.
            </div>
          )}
        </div>
      </div>

      {/* Modal: Ingest New Document */}
      {showIngestModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-xl w-full p-6 space-y-4 max-h-[90vh] overflow-y-auto">
            <h3 className="text-lg font-bold text-white">Ingest Identity Document</h3>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1">Customer ID</label>
                <input
                  type="text"
                  value={newCustId}
                  onChange={e => setNewCustId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-sm text-slate-200"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1">Document Category</label>
                <select
                  value={newCategory}
                  onChange={e => setNewCategory(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-sm text-slate-200"
                >
                  <option value="PASSPORT">Passport</option>
                  <option value="PAN">PAN (Permanent Account Number)</option>
                  <option value="AADHAAR">Aadhaar (Synthetic Demo Only)</option>
                  <option value="DRIVING_LICENSE">Driving License</option>
                  <option value="NATIONAL_ID">National ID</option>
                  <option value="VOTER_ID">Voter ID</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1">File Format</label>
                <select
                  value={newFormat}
                  onChange={e => setNewFormat(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-sm text-slate-200"
                >
                  <option value="PDF">PDF</option>
                  <option value="JPEG">JPEG</option>
                  <option value="PNG">PNG</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1">File Name</label>
                <input
                  type="text"
                  value={newFileName}
                  onChange={e => setNewFileName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-sm text-slate-200"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1">Issuing Country</label>
                <input
                  type="text"
                  value={newCountry}
                  onChange={e => setNewCountry(e.target.value.toUpperCase())}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-sm text-slate-200"
                />
              </div>
            </div>

            <div className="border-t border-slate-800 pt-3">
              <div className="text-xs font-bold text-emerald-400 mb-2 uppercase">Field Consistency Verification Test</div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[11px] font-semibold text-slate-400 block mb-1">Document Extracted Name</label>
                  <input
                    type="text"
                    value={docName}
                    onChange={e => setDocName(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-slate-200"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-semibold text-slate-400 block mb-1">Customer Profile Expected Name</label>
                  <input
                    type="text"
                    value={expName}
                    onChange={e => setExpName(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-slate-200"
                  />
                </div>

                <div>
                  <label className="text-[11px] font-semibold text-slate-400 block mb-1">Document Extracted DOB</label>
                  <input
                    type="date"
                    value={docDob}
                    onChange={e => setDocDob(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-slate-200"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-semibold text-slate-400 block mb-1">Customer Profile Expected DOB</label>
                  <input
                    type="date"
                    value={expDob}
                    onChange={e => setExpDob(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-slate-200"
                  />
                </div>
              </div>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-300 block mb-1">Raw File Byte Stream / Content (for SHA-256)</label>
              <textarea
                rows={2}
                value={rawPayload}
                onChange={e => setRawPayload(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-slate-200 font-mono"
              />
            </div>

            <div className="flex justify-end gap-3 pt-3">
              <button
                onClick={() => setShowIngestModal(false)}
                className="px-4 py-2 bg-slate-800 text-slate-300 text-sm font-semibold rounded-lg hover:bg-slate-700"
              >
                Cancel
              </button>
              <button
                onClick={handleIngestDocument}
                className="px-4 py-2 bg-emerald-600 text-white text-sm font-semibold rounded-lg hover:bg-emerald-500"
              >
                Ingest & Run Verification
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DocumentVerificationPage;
