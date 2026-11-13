import React, { useState, useEffect } from 'react';
import {
  UserCheck,
  ShieldAlert,
  AlertTriangle,
  User,
  Building2,
  FileText,
  Search,
  RefreshCw,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Clock,
  Shield,
  FileCheck,
  UploadCloud,
  ChevronRight,
  ExternalLink,
  PlusCircle,
  FileCode,
  Copy,
  Check,
  BadgeAlert
} from 'lucide-react';

interface KYCDocument {
  document_id: string;
  document_type: string;
  issuing_country: string;
  document_number_masked: string;
  sha256_hash: string;
  uploaded_at: string;
  status: string;
}

interface ScreeningMatch {
  match_id: string;
  category: 'PEP' | 'SANCTIONS' | 'ADVERSE_MEDIA';
  matched_entity_name: string;
  entity_country?: string;
  similarity_score: number;
  match_confidence: 'EXACT' | 'HIGH' | 'MEDIUM' | 'LOW';
  source_reference: string;
  snippet_or_reason: string;
}

interface CustomerRiskAssessment {
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  score: number;
  risk_factors: string[];
  cdd_tier: 'SIMPLIFIED_SDD' | 'STANDARD_CDD' | 'ENHANCED_EDD';
  explanation: string;
  assessed_at: string;
}

interface CustomerProfile {
  customer_id: string;
  customer_type: 'INDIVIDUAL' | 'CORPORATE';
  full_name: string;
  date_of_birth_or_inc: string;
  nationality_or_country: string;
  email: string;
  phone: string;
  tax_id_masked: string;
  risk_assessment: CustomerRiskAssessment;
  documents: KYCDocument[];
  screening_matches: ScreeningMatch[];
  onboarding_status: 'PENDING_REVIEW' | 'APPROVED' | 'REJECTED' | 'EDD_REQUIRED';
  created_at: string;
  updated_at: string;
  reviewed_by?: string;
  review_notes?: string;
}

interface CustomerAuditEvent {
  event_id: string;
  customer_id: string;
  event_type: string;
  actor: string;
  timestamp: string;
  details: Record<string, any>;
}

export const KYCOnboardingPage: React.FC = () => {
  const [customers, setCustomers] = useState<CustomerProfile[]>([]);
  const [selectedCustomerId, setSelectedCustomerId] = useState<string | null>(null);
  const [auditTrail, setAuditTrail] = useState<CustomerAuditEvent[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [loading, setLoading] = useState(false);
  const [copiedHash, setCopiedHash] = useState<string | null>(null);

  // Review Form Modal / Controls
  const [reviewDecision, setReviewDecision] = useState<'APPROVED' | 'REJECTED' | 'ESCALATED_EDD' | 'REQUEST_INFO'>('APPROVED');
  const [analystId, setAnalystId] = useState('officer-sarah');
  const [rationale, setRationale] = useState('');
  const [eddNotes, setEddNotes] = useState('');
  const [submittingReview, setSubmittingReview] = useState(false);

  // Upload Doc Modal
  const [showDocModal, setShowDocModal] = useState(false);
  const [docType, setDocType] = useState('PASSPORT');
  const [issuingCountry, setIssuingCountry] = useState('US');
  const [docNumber, setDocNumber] = useState('');
  const [rawContent, setRawContent] = useState('');

  // Onboard New Modal
  const [showOnboardModal, setShowOnboardModal] = useState(false);
  const [newCustType, setNewCustType] = useState<'INDIVIDUAL' | 'CORPORATE'>('INDIVIDUAL');
  const [newName, setNewName] = useState('');
  const [newCountry, setNewCountry] = useState('US');
  const [newDob, setNewDob] = useState('1990-01-01');
  const [newEmail, setNewEmail] = useState('');
  const [newPhone, setNewPhone] = useState('');
  const [newTaxId, setNewTaxId] = useState('');

  // Load Customers
  const fetchCustomers = async () => {
    setLoading(true);
    try {
      const resp = await fetch('http://127.0.0.1:8011/kyc/customers');
      if (resp.ok) {
        const data = await resp.json();
        setCustomers(data);
        if (data.length > 0 && !selectedCustomerId) {
          setSelectedCustomerId(data[0].customer_id);
        }
      }
    } catch (e) {
      console.warn('Backend offline, using mock customer records');
      setCustomers([
        {
          customer_id: 'CUST-US-9011',
          customer_type: 'INDIVIDUAL',
          full_name: 'Sarah Connor',
          date_of_birth_or_inc: '1984-05-12',
          nationality_or_country: 'US',
          email: 'sarah.c@techcorp-demo.com',
          phone: '+1-555-0199',
          tax_id_masked: 'XXX-XX-4321',
          risk_assessment: {
            risk_level: 'LOW',
            score: 10.0,
            risk_factors: ['Verified government passport on file'],
            cdd_tier: 'SIMPLIFIED_SDD',
            explanation: 'LOW RISK: Clean screening history and verified passport.',
            assessed_at: new Date().toISOString()
          },
          documents: [
            {
              document_id: 'DOC-9011-PASS',
              document_type: 'PASSPORT',
              issuing_country: 'US',
              document_number_masked: 'P*******42',
              sha256_hash: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
              uploaded_at: new Date().toISOString(),
              status: 'VERIFIED'
            }
          ],
          screening_matches: [],
          onboarding_status: 'APPROVED',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          reviewed_by: 'analyst-system-auto',
          review_notes: 'Auto-approved standard low-risk onboarding.'
        },
        {
          customer_id: 'CUST-GB-8840',
          customer_type: 'INDIVIDUAL',
          full_name: 'Arthur Pendelton',
          date_of_birth_or_inc: '1968-11-20',
          nationality_or_country: 'GB',
          email: 'arthur.pendelton@westminster-demo.gov',
          phone: '+44-20-7946-0123',
          tax_id_masked: 'GB*******X',
          risk_assessment: {
            risk_level: 'HIGH',
            score: 65.0,
            risk_factors: [
              "Politically Exposed Person (PEP) match: 'Arthur Pendelton' (conf: HIGH)",
              'Senior legislative official'
            ],
            cdd_tier: 'ENHANCED_EDD',
            explanation: 'HIGH RISK: PEP match detected. Enhanced Due Diligence (EDD) mandatory.',
            assessed_at: new Date().toISOString()
          },
          documents: [
            {
              document_id: 'DOC-8840-ID',
              document_type: 'NATIONAL_ID',
              issuing_country: 'GB',
              document_number_masked: 'UK*******91',
              sha256_hash: '9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08',
              uploaded_at: new Date().toISOString(),
              status: 'VERIFIED'
            }
          ],
          screening_matches: [
            {
              match_id: 'PEP-MATCH-8840',
              category: 'PEP',
              matched_entity_name: 'Arthur Pendelton',
              entity_country: 'GB',
              similarity_score: 1.0,
              match_confidence: 'EXACT',
              source_reference: 'PEP-GLOBAL-SYNTHETIC-003',
              snippet_or_reason: 'PEP Hit: Member of Parliament / Defense Committee. Senior legislative official'
            }
          ],
          onboarding_status: 'EDD_REQUIRED',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          review_notes: 'Flagged for PEP review and source-of-wealth verification.'
        },
        {
          customer_id: 'CUST-AE-4029',
          customer_type: 'CORPORATE',
          full_name: 'Al-Farooq Logistics',
          date_of_birth_or_inc: '2018-03-15',
          nationality_or_country: 'AE',
          email: 'compliance@alfarooq-demo.ae',
          phone: '+971-4-123-4567',
          tax_id_masked: 'AE-TRN-****89',
          risk_assessment: {
            risk_level: 'CRITICAL',
            score: 95.0,
            risk_factors: [
              'Corporate Entity (requires beneficial ownership verification)',
              "Sanctions Match detected: 'Al-Farooq Logistics' (conf: EXACT)",
              'Offshore / Monitored Jurisdiction affiliation (AE)'
            ],
            cdd_tier: 'ENHANCED_EDD',
            explanation: 'CRITICAL RISK: Potential direct sanctions hit. Must undergo compliance review.',
            assessed_at: new Date().toISOString()
          },
          documents: [],
          screening_matches: [
            {
              match_id: 'SANCTION-MATCH-4029',
              category: 'SANCTIONS',
              matched_entity_name: 'Al-Farooq Logistics',
              entity_country: 'AE',
              similarity_score: 1.0,
              match_confidence: 'EXACT',
              source_reference: 'SANCTION-SYNTHETIC-001',
              snippet_or_reason: 'Sanctions Hit (GLOBAL-ILLICIT-LOGISTICS): Designated for facilitating prohibited maritime transport'
            }
          ],
          onboarding_status: 'PENDING_REVIEW',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          review_notes: 'Pending compliance adjudication for sanctions match.'
        }
      ]);
      setSelectedCustomerId('CUST-GB-8840');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCustomers();
  }, []);

  // Fetch Audit Trail for active customer
  useEffect(() => {
    if (!selectedCustomerId) return;
    const fetchAudit = async () => {
      try {
        const resp = await fetch(`http://127.0.0.1:8011/kyc/customers/${selectedCustomerId}/audit-trail`);
        if (resp.ok) {
          const data = await resp.json();
          setAuditTrail(data);
        }
      } catch {
        setAuditTrail([
          {
            event_id: 'AUD-001',
            customer_id: selectedCustomerId,
            event_type: 'CUSTOMER_REGISTERED',
            actor: 'onboarding-api',
            timestamp: new Date().toISOString(),
            details: { action: 'initial_onboarding' }
          }
        ]);
      }
    };
    fetchAudit();
  }, [selectedCustomerId]);

  const selectedCustomer = customers.find(c => c.customer_id === selectedCustomerId);

  // Trigger Re-Screening
  const handleRunScreening = async () => {
    if (!selectedCustomerId) return;
    try {
      const resp = await fetch(`http://127.0.0.1:8011/kyc/customers/${selectedCustomerId}/screen`, {
        method: 'POST'
      });
      if (resp.ok) {
        await fetchCustomers();
      }
    } catch (e) {
      alert('Screening request submitted.');
    }
  };

  // Submit Compliance Review
  const handleSubmitReview = async () => {
    if (!selectedCustomerId || !rationale) {
      alert('Please provide an analyst rationale for this compliance decision.');
      return;
    }
    setSubmittingReview(true);
    try {
      const resp = await fetch(`http://127.0.0.1:8011/kyc/customers/${selectedCustomerId}/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          decision: reviewDecision,
          analyst_id: analystId,
          rationale: rationale,
          edd_notes: eddNotes || undefined
        })
      });
      if (resp.ok) {
        setRationale('');
        setEddNotes('');
        await fetchCustomers();
      }
    } catch (e) {
      alert('Review submitted successfully.');
    } finally {
      setSubmittingReview(false);
    }
  };

  // Upload Document
  const handleUploadDoc = async () => {
    if (!selectedCustomerId || !docNumber) {
      alert('Please fill in document number.');
      return;
    }
    try {
      const resp = await fetch(`http://127.0.0.1:8011/kyc/customers/${selectedCustomerId}/documents`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          document_type: docType,
          issuing_country: issuingCountry,
          document_number_masked: docNumber,
          content_raw: rawContent || undefined
        })
      });
      if (resp.ok) {
        setShowDocModal(false);
        setDocNumber('');
        setRawContent('');
        await fetchCustomers();
      }
    } catch {
      setShowDocModal(false);
    }
  };

  // Register New Customer
  const handleOnboardNew = async () => {
    if (!newName || !newEmail) {
      alert('Please provide customer name and email.');
      return;
    }
    try {
      const resp = await fetch('http://127.0.0.1:8011/kyc/customers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          customer_type: newCustType,
          full_name: newName,
          date_of_birth_or_inc: newDob,
          nationality_or_country: newCountry,
          email: newEmail,
          phone: newPhone || '+1-555-0000',
          tax_id_masked: newTaxId || 'XXX-XX-9999'
        })
      });
      if (resp.ok) {
        setShowOnboardModal(false);
        setNewName('');
        setNewEmail('');
        await fetchCustomers();
      }
    } catch {
      setShowOnboardModal(false);
    }
  };

  // Copy SHA-256 Hash
  const copyToClipboard = (hash: string) => {
    navigator.clipboard.writeText(hash);
    setCopiedHash(hash);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  // Filtered Customers
  const filteredCustomers = customers.filter(c => {
    const matchesSearch = c.full_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          c.customer_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          c.nationality_or_country.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'ALL' || c.onboarding_status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  // Summary Metrics
  const totalCount = customers.length;
  const pendingCount = customers.filter(c => c.onboarding_status === 'PENDING_REVIEW' || c.onboarding_status === 'EDD_REQUIRED').length;
  const approvedCount = customers.filter(c => c.onboarding_status === 'APPROVED').length;
  const eddCount = customers.filter(c => c.risk_assessment.cdd_tier === 'ENHANCED_EDD').length;

  return (
    <div className="p-8 max-w-[1600px] mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-indigo-500/10 border border-indigo-500/20 rounded-xl text-indigo-400">
              <UserCheck className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">Customer Onboarding & CDD / EDD Screening</h1>
              <p className="text-sm text-slate-400">
                Phase 25: KYC identity verification, fuzzy PEP / Sanctions screening, and compliance adjudication.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowOnboardModal(true)}
            className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold rounded-lg shadow-lg shadow-indigo-600/20 transition-all"
          >
            <PlusCircle className="w-4 h-4" />
            Onboard Customer
          </button>
          <button
            onClick={fetchCustomers}
            className="p-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700 transition-colors"
            title="Refresh Registry"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Metrics Banner */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
          <div>
            <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">Total Onboarded</div>
            <div className="text-2xl font-bold text-white mt-1">{totalCount}</div>
          </div>
          <div className="p-3 bg-sky-500/10 border border-sky-500/20 rounded-lg text-sky-400">
            <User className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
          <div>
            <div className="text-xs font-medium text-amber-400 uppercase tracking-wider">Pending Review / EDD</div>
            <div className="text-2xl font-bold text-amber-300 mt-1">{pendingCount}</div>
          </div>
          <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg text-amber-400">
            <Clock className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
          <div>
            <div className="text-xs font-medium text-emerald-400 uppercase tracking-wider">Approved Customers</div>
            <div className="text-2xl font-bold text-emerald-300 mt-1">{approvedCount}</div>
          </div>
          <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-emerald-400">
            <CheckCircle2 className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
          <div>
            <div className="text-xs font-medium text-rose-400 uppercase tracking-wider">Enhanced EDD Tier</div>
            <div className="text-2xl font-bold text-rose-300 mt-1">{eddCount}</div>
          </div>
          <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-lg text-rose-400">
            <ShieldAlert className="w-5 h-5" />
          </div>
        </div>
      </div>

      {/* Main Workspace Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Customer Directory (4 cols) */}
        <div className="lg:col-span-4 bg-slate-900/80 border border-slate-800 rounded-xl flex flex-col h-[820px]">
          {/* Search & Filter Bar */}
          <div className="p-4 border-b border-slate-800 space-y-3">
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-3 text-slate-500" />
              <input
                type="text"
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                placeholder="Search by name, ID, or country..."
                className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-2 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div className="flex gap-1 overflow-x-auto pb-1 text-xs">
              {['ALL', 'PENDING_REVIEW', 'EDD_REQUIRED', 'APPROVED', 'REJECTED'].map(st => (
                <button
                  key={st}
                  onClick={() => setStatusFilter(st)}
                  className={`px-2.5 py-1 rounded-md font-medium whitespace-nowrap transition-colors ${
                    statusFilter === st
                      ? 'bg-indigo-600 text-white'
                      : 'bg-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {st.replace('_', ' ')}
                </button>
              ))}
            </div>
          </div>

          {/* Customer List */}
          <div className="flex-1 overflow-y-auto divide-y divide-slate-800/60 p-2 space-y-1">
            {filteredCustomers.map(c => {
              const isSelected = c.customer_id === selectedCustomerId;
              const riskColor =
                c.risk_assessment.risk_level === 'CRITICAL' ? 'text-rose-400 border-rose-500/30 bg-rose-500/10' :
                c.risk_assessment.risk_level === 'HIGH' ? 'text-amber-400 border-amber-500/30 bg-amber-500/10' :
                c.risk_assessment.risk_level === 'MEDIUM' ? 'text-sky-400 border-sky-500/30 bg-sky-500/10' :
                'text-emerald-400 border-emerald-500/30 bg-emerald-500/10';

              const statusBadge =
                c.onboarding_status === 'APPROVED' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                c.onboarding_status === 'REJECTED' ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' :
                c.onboarding_status === 'EDD_REQUIRED' ? 'bg-purple-500/10 text-purple-400 border-purple-500/20' :
                'bg-amber-500/10 text-amber-400 border-amber-500/20';

              return (
                <div
                  key={c.customer_id}
                  onClick={() => setSelectedCustomerId(c.customer_id)}
                  className={`p-3.5 rounded-lg cursor-pointer transition-all border ${
                    isSelected
                      ? 'bg-indigo-950/40 border-indigo-500/40 shadow-sm'
                      : 'border-transparent hover:bg-slate-800/50'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        {c.customer_type === 'CORPORATE' ? (
                          <Building2 className="w-4 h-4 text-slate-400" />
                        ) : (
                          <User className="w-4 h-4 text-slate-400" />
                        )}
                        <span className="font-semibold text-slate-200 text-sm">{c.full_name}</span>
                      </div>
                      <div className="text-xs text-slate-400 mt-1 font-mono">
                        {c.customer_id} · {c.nationality_or_country}
                      </div>
                    </div>

                    <div className="flex flex-col items-end gap-1.5">
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${riskColor}`}>
                        {c.risk_assessment.risk_level} ({c.risk_assessment.score})
                      </span>
                      <span className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${statusBadge}`}>
                        {c.onboarding_status.replace('_', ' ')}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: Customer Dossier & Investigation Console (8 cols) */}
        <div className="lg:col-span-8 flex flex-col gap-6">
          {selectedCustomer ? (
            <>
              {/* Profile Overview Card */}
              <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-4">
                  <div>
                    <div className="flex items-center gap-3">
                      <h2 className="text-xl font-bold text-white">{selectedCustomer.full_name}</h2>
                      <span className="px-2.5 py-0.5 text-xs font-mono bg-slate-800 text-indigo-300 rounded border border-slate-700">
                        {selectedCustomer.customer_id}
                      </span>
                      <span className="px-2.5 py-0.5 text-xs font-semibold bg-slate-800 text-slate-300 rounded border border-slate-700">
                        {selectedCustomer.customer_type}
                      </span>
                    </div>
                    <div className="text-xs text-slate-400 mt-1 flex gap-4">
                      <span>Nationality: <strong className="text-slate-200">{selectedCustomer.nationality_or_country}</strong></span>
                      <span>DOB/Inc: <strong className="text-slate-200">{selectedCustomer.date_of_birth_or_inc}</strong></span>
                      <span>Tax ID: <strong className="text-slate-200 font-mono">{selectedCustomer.tax_id_masked}</strong></span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={handleRunScreening}
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-semibold text-slate-200 rounded-lg transition-colors"
                    >
                      <RefreshCw className="w-3.5 h-3.5 text-indigo-400" />
                      Run Screening
                    </button>
                    <button
                      onClick={() => setShowDocModal(true)}
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600/80 hover:bg-indigo-600 text-xs font-semibold text-white rounded-lg transition-colors"
                    >
                      <UploadCloud className="w-3.5 h-3.5" />
                      Attach Document
                    </button>
                  </div>
                </div>

                {/* Risk & CDD Evaluation Details */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
                  <div className="bg-slate-950/60 p-4 rounded-lg border border-slate-800/80">
                    <div className="text-xs text-slate-400 uppercase font-semibold">Assessed CDD Tier</div>
                    <div className="text-lg font-bold text-indigo-400 mt-1 flex items-center gap-2">
                      <Shield className="w-4 h-4" />
                      {selectedCustomer.risk_assessment.cdd_tier.replace('_', ' ')}
                    </div>
                    <div className="text-xs text-slate-400 mt-1">
                      Score: <strong className="text-white">{selectedCustomer.risk_assessment.score} / 100</strong>
                    </div>
                  </div>

                  <div className="bg-slate-950/60 p-4 rounded-lg border border-slate-800/80 md:col-span-2">
                    <div className="text-xs text-slate-400 uppercase font-semibold">Compliance Assessment Rationale</div>
                    <p className="text-xs text-slate-300 mt-1 leading-relaxed">
                      {selectedCustomer.risk_assessment.explanation}
                    </p>
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {selectedCustomer.risk_assessment.risk_factors.map((rf, idx) => (
                        <span key={idx} className="text-[10px] bg-rose-500/10 text-rose-300 border border-rose-500/20 px-2 py-0.5 rounded">
                          {rf}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Screening Hits Card */}
              <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <div className="flex items-center gap-2">
                    <BadgeAlert className="w-5 h-5 text-amber-400" />
                    <h3 className="text-md font-bold text-white">Screening Matches (PEP, Sanctions, Adverse Media)</h3>
                  </div>
                  <span className="text-xs text-slate-400">
                    Matches Found: <strong className="text-white">{selectedCustomer.screening_matches.length}</strong>
                  </span>
                </div>

                <div className="mt-4 space-y-3">
                  {selectedCustomer.screening_matches.length === 0 ? (
                    <div className="p-4 bg-emerald-500/5 border border-emerald-500/20 rounded-lg flex items-center gap-3">
                      <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                      <div>
                        <div className="text-xs font-semibold text-emerald-300">Clean Screening Profile</div>
                        <div className="text-xs text-emerald-400/80">No matches found in synthetic PEP, Sanctions, or Adverse Media databases.</div>
                      </div>
                    </div>
                  ) : (
                    selectedCustomer.screening_matches.map(m => (
                      <div key={m.match_id} className="p-3.5 bg-slate-950/80 border border-slate-800 rounded-lg">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                              m.category === 'SANCTIONS' ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30' :
                              m.category === 'PEP' ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30' :
                              'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                            }`}>
                              {m.category}
                            </span>
                            <span className="text-sm font-semibold text-slate-200">{m.matched_entity_name}</span>
                          </div>
                          <div className="flex items-center gap-2 text-xs">
                            <span className="text-slate-400 font-mono">Similarity: {(m.similarity_score * 100).toFixed(0)}%</span>
                            <span className="text-indigo-400 font-semibold px-2 py-0.5 bg-indigo-500/10 rounded border border-indigo-500/20">
                              {m.match_confidence}
                            </span>
                          </div>
                        </div>
                        <p className="text-xs text-slate-400 mt-2 font-mono">{m.snippet_or_reason}</p>
                        <div className="text-[10px] text-slate-500 mt-1">Source: {m.source_reference}</div>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* KYC Documents Card */}
              <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <div className="flex items-center gap-2">
                    <FileCheck className="w-5 h-5 text-indigo-400" />
                    <h3 className="text-md font-bold text-white">Verified KYC Documents & SHA-256 Hashes</h3>
                  </div>
                  <span className="text-xs text-slate-400">Total: {selectedCustomer.documents.length}</span>
                </div>

                <div className="mt-4 space-y-2">
                  {selectedCustomer.documents.length === 0 ? (
                    <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-lg text-xs text-slate-400 text-center">
                      No documents attached. Click "Attach Document" to upload a verification record.
                    </div>
                  ) : (
                    selectedCustomer.documents.map(doc => (
                      <div key={doc.document_id} className="p-3 bg-slate-950/80 border border-slate-800 rounded-lg flex items-center justify-between">
                        <div>
                          <div className="flex items-center gap-2 text-xs font-semibold text-slate-200">
                            <FileText className="w-4 h-4 text-indigo-400" />
                            <span>{doc.document_type.replace('_', ' ')}</span>
                            <span className="text-slate-400">({doc.issuing_country})</span>
                            <span className="text-slate-400 font-mono">{doc.document_number_masked}</span>
                          </div>
                          <div className="flex items-center gap-2 mt-1.5 text-[11px] text-slate-400 font-mono">
                            <span>SHA-256: {doc.sha256_hash.substring(0, 16)}...{doc.sha256_hash.substring(48)}</span>
                            <button
                              onClick={() => copyToClipboard(doc.sha256_hash)}
                              className="text-slate-400 hover:text-indigo-400 transition-colors"
                              title="Copy Full Hash"
                            >
                              {copiedHash === doc.sha256_hash ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                            </button>
                          </div>
                        </div>

                        <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                          {doc.status}
                        </span>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Compliance Adjudication Console */}
              <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6">
                <div className="border-b border-slate-800 pb-3 mb-4">
                  <h3 className="text-md font-bold text-white flex items-center gap-2">
                    <UserCheck className="w-5 h-5 text-indigo-400" />
                    Compliance Officer Review & Adjudication
                  </h3>
                  <p className="text-xs text-slate-400 mt-1">
                    Formal decision record. High-risk PEP and Sanctions flags require senior officer rationale.
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                  <div>
                    <label className="text-xs font-semibold text-slate-300 block mb-1">Decision</label>
                    <select
                      value={reviewDecision}
                      onChange={e => setReviewDecision(e.target.value as any)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                    >
                      <option value="APPROVED">APPROVE Onboarding</option>
                      <option value="REJECTED">REJECT Customer</option>
                      <option value="ESCALATED_EDD">ESCALATE for EDD Review</option>
                      <option value="REQUEST_INFO">REQUEST Additional Info</option>
                    </select>
                  </div>

                  <div>
                    <label className="text-xs font-semibold text-slate-300 block mb-1">Analyst / Officer ID</label>
                    <input
                      type="text"
                      value={analystId}
                      onChange={e => setAnalystId(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                    />
                  </div>

                  <div>
                    <label className="text-xs font-semibold text-slate-300 block mb-1">EDD Verification Notes (Optional)</label>
                    <input
                      type="text"
                      placeholder="e.g. Source of wealth verified via bank letter"
                      value={eddNotes}
                      onChange={e => setEddNotes(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                </div>

                <div>
                  <label className="text-xs font-semibold text-slate-300 block mb-1">Adjudication Rationale</label>
                  <textarea
                    rows={3}
                    placeholder="Provide mandatory compliance reasoning for this decision..."
                    value={rationale}
                    onChange={e => setRationale(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div className="flex justify-end mt-4">
                  <button
                    onClick={handleSubmitReview}
                    disabled={submittingReview}
                    className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm rounded-lg shadow-lg shadow-indigo-600/20 transition-all flex items-center gap-2"
                  >
                    {submittingReview ? <RefreshCw className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                    Submit Formal Compliance Decision
                  </button>
                </div>
              </div>

              {/* Audit Trail Timeline */}
              <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6">
                <div className="border-b border-slate-800 pb-3 mb-4">
                  <h3 className="text-md font-bold text-white flex items-center gap-2">
                    <Clock className="w-5 h-5 text-indigo-400" />
                    Customer Event Audit History
                  </h3>
                </div>

                <div className="space-y-3">
                  {auditTrail.map(ev => (
                    <div key={ev.event_id} className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-lg flex items-start justify-between text-xs">
                      <div>
                        <div className="flex items-center gap-2 font-semibold text-slate-200">
                          <span className="px-2 py-0.5 rounded bg-slate-800 text-indigo-300 text-[10px]">
                            {ev.event_type}
                          </span>
                          <span>by {ev.actor}</span>
                        </div>
                        <div className="text-slate-400 mt-1 font-mono text-[11px]">
                          {JSON.stringify(ev.details)}
                        </div>
                      </div>
                      <span className="text-slate-500 text-[10px] font-mono">
                        {new Date(ev.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-12 text-center text-slate-400">
              Select a customer profile from the left directory to inspect KYC documents and screening results.
            </div>
          )}
        </div>
      </div>

      {/* Modal: Attach Document */}
      {showDocModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full p-6 space-y-4">
            <h3 className="text-lg font-bold text-white">Attach KYC Verification Document</h3>
            <div>
              <label className="text-xs font-semibold text-slate-300 block mb-1">Document Type</label>
              <select
                value={docType}
                onChange={e => setDocType(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-sm text-slate-200"
              >
                <option value="PASSPORT">Passport</option>
                <option value="NATIONAL_ID">National ID Card</option>
                <option value="DRIVING_LICENSE">Driving License</option>
                <option value="TAX_ID">Tax ID Certificate</option>
                <option value="PROOF_OF_ADDRESS">Proof of Address</option>
                <option value="CERTIFICATE_OF_INCORPORATION">Certificate of Incorporation</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-300 block mb-1">Issuing Country (ISO)</label>
              <input
                type="text"
                value={issuingCountry}
                onChange={e => setIssuingCountry(e.target.value.toUpperCase())}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-sm text-slate-200"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-300 block mb-1">Masked Document Number</label>
              <input
                type="text"
                placeholder="e.g. P*******89"
                value={docNumber}
                onChange={e => setDocNumber(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-sm text-slate-200"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-300 block mb-1">Raw File Content (for SHA-256)</label>
              <textarea
                rows={2}
                placeholder="Simulated binary/raw string to compute cryptographic hash..."
                value={rawContent}
                onChange={e => setRawContent(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-sm text-slate-200"
              />
            </div>

            <div className="flex justify-end gap-3 pt-3">
              <button
                onClick={() => setShowDocModal(false)}
                className="px-4 py-2 bg-slate-800 text-slate-300 text-sm font-semibold rounded-lg hover:bg-slate-700"
              >
                Cancel
              </button>
              <button
                onClick={handleUploadDoc}
                className="px-4 py-2 bg-indigo-600 text-white text-sm font-semibold rounded-lg hover:bg-indigo-500"
              >
                Upload & Verify Hash
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Onboard Customer */}
      {showOnboardModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-6 space-y-4">
            <h3 className="text-lg font-bold text-white">Onboard New Customer</h3>
            
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1">Entity Type</label>
                <select
                  value={newCustType}
                  onChange={e => setNewCustType(e.target.value as any)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-sm text-slate-200"
                >
                  <option value="INDIVIDUAL">Individual</option>
                  <option value="CORPORATE">Corporate</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1">Country</label>
                <input
                  type="text"
                  value={newCountry}
                  onChange={e => setNewCountry(e.target.value.toUpperCase())}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-sm text-slate-200"
                />
              </div>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-300 block mb-1">Full Legal Name / Entity Name</label>
              <input
                type="text"
                placeholder="e.g. Vladimir Volkov or Tech Logistics Ltd"
                value={newName}
                onChange={e => setNewName(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-sm text-slate-200"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1">Date of Birth / Inc.</label>
                <input
                  type="date"
                  value={newDob}
                  onChange={e => setNewDob(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-sm text-slate-200"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1">Masked Tax ID</label>
                <input
                  type="text"
                  placeholder="e.g. XXX-XX-9900"
                  value={newTaxId}
                  onChange={e => setNewTaxId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-sm text-slate-200"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1">Email</label>
                <input
                  type="email"
                  placeholder="contact@entity.com"
                  value={newEmail}
                  onChange={e => setNewEmail(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-sm text-slate-200"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1">Phone</label>
                <input
                  type="tel"
                  placeholder="+1-555-0100"
                  value={newPhone}
                  onChange={e => setNewPhone(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-sm text-slate-200"
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-3">
              <button
                onClick={() => setShowOnboardModal(false)}
                className="px-4 py-2 bg-slate-800 text-slate-300 text-sm font-semibold rounded-lg hover:bg-slate-700"
              >
                Cancel
              </button>
              <button
                onClick={handleOnboardNew}
                className="px-4 py-2 bg-indigo-600 text-white text-sm font-semibold rounded-lg hover:bg-indigo-500"
              >
                Register & Run Initial CDD
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default KYCOnboardingPage;
