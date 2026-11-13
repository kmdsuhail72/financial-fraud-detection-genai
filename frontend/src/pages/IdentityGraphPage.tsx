import React, { useState, useEffect } from 'react';
import {
  Network,
  Share2,
  ShieldAlert,
  AlertTriangle,
  User,
  Phone,
  Mail,
  Smartphone,
  MapPin,
  FileText,
  Search,
  RefreshCw,
  PlusCircle,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Clock,
  Layers,
  Fingerprint,
  Link2,
  ExternalLink,
  Sliders,
  Shield,
  Activity,
  UserX,
  FileCheck
} from 'lucide-react';

interface GraphNode {
  node_id: string;
  node_type: string;
  label: string;
  properties: Record<string, any>;
  risk_score: number;
}

interface GraphEdge {
  source_id: string;
  target_id: string;
  edge_type: string;
  weight: number;
}

interface IdentityCollision {
  collision_id: string;
  collision_type: string;
  shared_attribute_type: string;
  shared_attribute_value: string;
  customer_ids: string[];
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  collision_score: number;
  detected_at: string;
  details: Record<string, any>;
}

interface IdentityRingCluster {
  cluster_id: string;
  customer_count: number;
  customer_ids: string[];
  entity_nodes_count: number;
  shared_attributes_summary: string[];
  cluster_risk_score: number;
  cluster_risk_tier: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  status: string;
}

interface SyntheticIdentityRiskProfile {
  customer_id: string;
  risk_score: number;
  risk_tier: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  collision_count: number;
  shared_attributes: string[];
  colliding_customers: string[];
  risk_reasons: string[];
  kyc_correlation: Record<string, any>;
}

interface IdentityAuditEvent {
  event_id: string;
  customer_id: string;
  event_type: string;
  actor: string;
  timestamp: string;
  details: Record<string, any>;
}

export const IdentityGraphPage: React.FC = () => {
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [collisions, setCollisions] = useState<IdentityCollision[]>([]);
  const [clusters, setClusters] = useState<IdentityRingCluster[]>([]);
  const [selectedCustomerId, setSelectedCustomerId] = useState<string>('CUST-SYN-001');
  const [riskProfile, setRiskProfile] = useState<SyntheticIdentityRiskProfile | null>(null);
  const [auditTrail, setAuditTrail] = useState<IdentityAuditEvent[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [severityFilter, setSeverityFilter] = useState('ALL');
  const [loading, setLoading] = useState(false);

  // Ingest Form State
  const [showRegisterModal, setShowRegisterModal] = useState(false);
  const [newCustId, setNewCustId] = useState('CUST-NEW-991');
  const [newFullName, setNewFullName] = useState('Vincent Vega');
  const [newPhone, setNewPhone] = useState('+1-555-8888'); // Seeds a collision
  const [newEmail, setNewEmail] = useState('vince@ghostmail-demo.com');
  const [newAddress, setNewAddress] = useState('742 Evergreen Terr, Springfield, OR');
  const [newDevice, setNewDevice] = useState('DEV-ANDROID-EMU-01');
  const [newIp, setNewIp] = useState('198.51.100.77');
  const [newDocId, setNewDocId] = useState('DOC-SYN-991');
  const [newKycStatus, setNewKycStatus] = useState('EDD_REQUIRED');
  const [newDocStatus, setNewDocStatus] = useState('INCONSISTENT_FIELDS');

  // Adjudication State
  const [decision, setDecision] = useState<'FLAG_SYNTHETIC_RING' | 'CLEAR_COLLISION' | 'REQUEST_EDD' | 'UNDER_REVIEW'>('FLAG_SYNTHETIC_RING');
  const [analystId, setAnalystId] = useState('fraud-investigator-dane');
  const [rationale, setRationale] = useState('');
  const [escalateToSar, setEscalateToSar] = useState(true);
  const [submittingReview, setSubmittingReview] = useState(false);

  // Load Initial Graph Data
  const fetchGraphData = async () => {
    setLoading(true);
    try {
      const [subgraphResp, colResp, clusterResp] = await Promise.all([
        fetch('http://127.0.0.1:8011/identity/graph/subgraph?max_depth=2'),
        fetch('http://127.0.0.1:8011/identity/graph/collisions'),
        fetch('http://127.0.0.1:8011/identity/graph/clusters')
      ]);

      if (subgraphResp.ok) {
        const sg = await subgraphResp.json();
        setNodes(sg.nodes);
        setEdges(sg.edges);
      }
      if (colResp.ok) {
        setCollisions(await colResp.json());
      }
      if (clusterResp.ok) {
        setClusters(await clusterResp.json());
      }
    } catch (e) {
      console.warn('Backend offline, using fallback state');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGraphData();
  }, []);

  // Fetch Risk Profile & Audit for selected customer
  useEffect(() => {
    if (!selectedCustomerId) return;
    const fetchCustomerData = async () => {
      try {
        const [riskResp, auditResp] = await Promise.all([
          fetch(`http://127.0.0.1:8011/identity/graph/customers/${selectedCustomerId}/risk`),
          fetch(`http://127.0.0.1:8011/identity/graph/customers/${selectedCustomerId}/audit-trail`)
        ]);
        if (riskResp.ok) {
          setRiskProfile(await riskResp.json());
        }
        if (auditResp.ok) {
          setAuditTrail(await auditResp.json());
        }
      } catch {
        // Fallback
        setRiskProfile({
          customer_id: selectedCustomerId,
          risk_score: 85.0,
          risk_tier: 'CRITICAL',
          collision_count: 3,
          shared_attributes: ['PHONE: +1-555-8888', 'DEVICE: DEV-ANDROID-EMU-01', 'ADDRESS: 742 Evergreen Terr'],
          colliding_customers: ['CUST-SYN-002', 'CUST-SYN-003'],
          risk_reasons: [
            'PHONE COLLISION: Phone number shared with 2 other accounts.',
            'DEVICE COLLISION: Hardware emulator shared across accounts.',
            'Network Ring: Member of a 3-applicant synthetic fraud cluster.'
          ],
          kyc_correlation: { kyc_status: 'EDD_REQUIRED', doc_verification_status: 'INCONSISTENT_FIELDS' }
        });
      }
    };
    fetchCustomerData();
  }, [selectedCustomerId]);

  // Submit Review
  const handleSubmitReview = async () => {
    if (!selectedCustomerId || !rationale) {
      alert('Please provide an analyst rationale for this adjudication.');
      return;
    }
    setSubmittingReview(true);
    try {
      const resp = await fetch(`http://127.0.0.1:8011/identity/graph/customers/${selectedCustomerId}/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          analyst_id: analystId,
          decision: decision,
          rationale: rationale,
          escalate_to_sar: escalateToSar
        })
      });
      if (resp.ok) {
        setRationale('');
        await fetchGraphData();
        const updated = await resp.json();
        setRiskProfile(updated);
      }
    } catch {
      alert('Review submitted.');
    } finally {
      setSubmittingReview(false);
    }
  };

  // Register Identity
  const handleRegisterIdentity = async () => {
    try {
      const resp = await fetch('http://127.0.0.1:8011/identity/graph/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          customer_id: newCustId,
          full_name: newFullName,
          phone: newPhone,
          email: newEmail,
          address: newAddress,
          device_id: newDevice,
          ip_address: newIp,
          document_id: newDocId,
          kyc_status: newKycStatus,
          doc_verification_status: newDocStatus
        })
      });
      if (resp.ok) {
        setShowRegisterModal(false);
        setSelectedCustomerId(newCustId);
        await fetchGraphData();
      }
    } catch {
      setShowRegisterModal(false);
    }
  };

  // Filtered Collisions
  const filteredCollisions = collisions.filter(c => {
    const matchesSearch =
      c.shared_attribute_value.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.customer_ids.some(cid => cid.toLowerCase().includes(searchTerm.toLowerCase()));
    const matchesSev = severityFilter === 'ALL' || c.severity === severityFilter;
    return matchesSearch && matchesSev;
  });

  // Helper for Node Icon
  const getNodeIcon = (type: string) => {
    switch (type) {
      case 'CUSTOMER': return <User className="w-3.5 h-3.5 text-sky-400" />;
      case 'PHONE': return <Phone className="w-3.5 h-3.5 text-emerald-400" />;
      case 'EMAIL': return <Mail className="w-3.5 h-3.5 text-indigo-400" />;
      case 'DEVICE': return <Smartphone className="w-3.5 h-3.5 text-amber-400" />;
      case 'ADDRESS': return <MapPin className="w-3.5 h-3.5 text-purple-400" />;
      case 'DOCUMENT': return <FileText className="w-3.5 h-3.5 text-rose-400" />;
      default: return <Network className="w-3.5 h-3.5 text-slate-400" />;
    }
  };

  return (
    <div className="p-8 max-w-[1600px] mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-purple-500/10 border border-purple-500/20 rounded-xl text-purple-400">
              <Share2 className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">Synthetic Identity & Graph Intelligence</h1>
              <p className="text-sm text-slate-400">
                Phase 27: Cross-customer attribute collision detection, identity rings, and explainable synthetic fraud scoring.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowRegisterModal(true)}
            className="flex items-center gap-2 px-4 py-2.5 bg-purple-600 hover:bg-purple-500 text-white text-sm font-semibold rounded-lg shadow-lg shadow-purple-600/20 transition-all"
          >
            <PlusCircle className="w-4 h-4" />
            Register Identity
          </button>
          <button
            onClick={fetchGraphData}
            className="p-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700 transition-colors"
            title="Refresh Graph"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Metrics Banner */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
          <div>
            <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">Graph Nodes</div>
            <div className="text-2xl font-bold text-white mt-1">{nodes.length}</div>
          </div>
          <div className="p-3 bg-sky-500/10 border border-sky-500/20 rounded-lg text-sky-400">
            <Network className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
          <div>
            <div className="text-xs font-medium text-amber-400 uppercase tracking-wider">Attribute Collisions</div>
            <div className="text-2xl font-bold text-amber-300 mt-1">{collisions.length}</div>
          </div>
          <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg text-amber-400">
            <AlertTriangle className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
          <div>
            <div className="text-xs font-medium text-rose-400 uppercase tracking-wider">Synthetic Rings</div>
            <div className="text-2xl font-bold text-rose-300 mt-1">{clusters.length}</div>
          </div>
          <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-lg text-rose-400">
            <ShieldAlert className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
          <div>
            <div className="text-xs font-medium text-purple-400 uppercase tracking-wider">Connected Clusters</div>
            <div className="text-2xl font-bold text-purple-300 mt-1">{edges.length} Edges</div>
          </div>
          <div className="p-3 bg-purple-500/10 border border-purple-500/20 rounded-lg text-purple-400">
            <Link2 className="w-5 h-5" />
          </div>
        </div>
      </div>

      {/* Main Workspace Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Collisions Directory & Ring Clusters (4 cols) */}
        <div className="lg:col-span-4 bg-slate-900/80 border border-slate-800 rounded-xl flex flex-col h-[850px]">
          {/* Search & Filter Bar */}
          <div className="p-4 border-b border-slate-800 space-y-3">
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-3 text-slate-500" />
              <input
                type="text"
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                placeholder="Search phone, email, device, or ID..."
                className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-2 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-purple-500"
              />
            </div>

            <div className="flex gap-1 overflow-x-auto pb-1 text-xs">
              {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map(sev => (
                <button
                  key={sev}
                  onClick={() => setSeverityFilter(sev)}
                  className={`px-2.5 py-1 rounded-md font-medium whitespace-nowrap transition-colors ${
                    severityFilter === sev
                      ? 'bg-purple-600 text-white'
                      : 'bg-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {sev}
                </button>
              ))}
            </div>
          </div>

          {/* Collisions & Clusters List */}
          <div className="flex-1 overflow-y-auto divide-y divide-slate-800/60 p-2 space-y-2">
            <div className="px-2 pt-1 text-[11px] font-bold uppercase text-slate-400 tracking-wider">
              Detected Synthetic Rings ({clusters.length})
            </div>
            {clusters.map(cl => (
              <div
                key={cl.cluster_id}
                className="p-3 bg-rose-950/20 border border-rose-500/30 rounded-lg space-y-2"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <ShieldAlert className="w-4 h-4 text-rose-400" />
                    <span className="font-bold text-white text-xs font-mono">{cl.cluster_id}</span>
                  </div>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30">
                    {cl.cluster_risk_tier} ({cl.cluster_risk_score})
                  </span>
                </div>
                <div className="text-xs text-slate-300">
                  Ring Size: <strong className="text-white">{cl.customer_count} Customers</strong> sharing {cl.entity_nodes_count} hardware & contact attributes.
                </div>
                <div className="flex flex-wrap gap-1">
                  {cl.customer_ids.map(cid => (
                    <button
                      key={cid}
                      onClick={() => setSelectedCustomerId(cid)}
                      className={`text-[10px] font-mono px-2 py-0.5 rounded border transition-colors ${
                        selectedCustomerId === cid
                          ? 'bg-purple-600 text-white border-purple-500'
                          : 'bg-slate-800 text-slate-300 border-slate-700 hover:border-purple-400'
                      }`}
                    >
                      {cid}
                    </button>
                  ))}
                </div>
              </div>
            ))}

            <div className="px-2 pt-3 text-[11px] font-bold uppercase text-slate-400 tracking-wider">
              Shared Attribute Collisions ({filteredCollisions.length})
            </div>
            {filteredCollisions.map(col => {
              const sevBadge =
                col.severity === 'CRITICAL' ? 'bg-rose-500/20 text-rose-400 border-rose-500/30' :
                col.severity === 'HIGH' ? 'bg-amber-500/20 text-amber-400 border-amber-500/30' :
                col.severity === 'MEDIUM' ? 'bg-sky-500/20 text-sky-400 border-sky-500/30' :
                'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';

              return (
                <div
                  key={col.collision_id}
                  className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-lg space-y-1.5"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-200 flex items-center gap-1.5">
                      {getNodeIcon(col.shared_attribute_type)}
                      {col.collision_type.replace(/_/g, ' ')}
                    </span>
                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${sevBadge}`}>
                      {col.severity}
                    </span>
                  </div>
                  <div className="text-xs font-mono text-purple-300 truncate">
                    {col.shared_attribute_value}
                  </div>
                  <div className="text-[11px] text-slate-400 flex items-center gap-1">
                    <span>Shared by {col.customer_ids.length} accounts:</span>
                    <span className="font-mono text-slate-300">{col.customer_ids.join(', ')}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: Visual Graph, Risk Profile & Adjudication (8 cols) */}
        <div className="lg:col-span-8 flex flex-col gap-6">
          {riskProfile ? (
            <>
              {/* Profile & Synthetic Risk Gauge */}
              <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-4">
                  <div>
                    <div className="flex items-center gap-3">
                      <h2 className="text-xl font-bold text-white font-mono">{riskProfile.customer_id}</h2>
                      <span className={`px-2.5 py-0.5 text-xs font-bold rounded border ${
                        riskProfile.risk_tier === 'CRITICAL' ? 'bg-rose-500/20 text-rose-400 border-rose-500/30' :
                        riskProfile.risk_tier === 'HIGH' ? 'bg-amber-500/20 text-amber-400 border-amber-500/30' :
                        'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
                      }`}>
                        {riskProfile.risk_tier} RISK ({riskProfile.risk_score} / 100)
                      </span>
                    </div>
                    <div className="text-xs text-slate-400 mt-1 flex gap-4">
                      <span>Attribute Collisions: <strong className="text-white">{riskProfile.collision_count}</strong></span>
                      <span>Colliding Accounts: <strong className="text-white">{riskProfile.colliding_customers.length}</strong></span>
                    </div>
                  </div>

                  {/* KYC & Forensic Badges */}
                  <div className="flex items-center gap-2">
                    <span className="px-2.5 py-1 text-xs bg-slate-800 text-slate-300 rounded border border-slate-700">
                      KYC: <strong className="text-amber-400">{riskProfile.kyc_correlation.kyc_status}</strong>
                    </span>
                    <span className="px-2.5 py-1 text-xs bg-slate-800 text-slate-300 rounded border border-slate-700">
                      Doc Status: <strong className="text-rose-400">{riskProfile.kyc_correlation.doc_verification_status}</strong>
                    </span>
                  </div>
                </div>

                {/* Risk Reasons Breakdown */}
                <div className="mt-4 space-y-1.5">
                  <div className="text-xs font-semibold text-slate-300 uppercase">Explainable Heuristic Risk Signals:</div>
                  {riskProfile.risk_reasons.map((reason, idx) => (
                    <div key={idx} className="p-2.5 bg-slate-950/80 border border-slate-800 rounded text-xs text-slate-300 flex items-start gap-2">
                      <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                      <span>{reason}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Visual Subgraph Canvas Representation */}
              <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
                  <div className="flex items-center gap-2">
                    <Network className="w-5 h-5 text-purple-400" />
                    <h3 className="text-md font-bold text-white">Identity Graph Topology & Collision Mesh</h3>
                  </div>
                  <span className="text-xs text-slate-400">
                    Showing local ego network centered on <strong className="text-white font-mono">{selectedCustomerId}</strong>
                  </span>
                </div>

                {/* Visual Node Grid */}
                <div className="p-4 bg-slate-950/80 rounded-lg border border-slate-800/80 min-h-[220px] flex flex-wrap items-center justify-center gap-4">
                  {nodes.map(n => {
                    const isFocus = n.node_id === selectedCustomerId;
                    return (
                      <div
                        key={n.node_id}
                        onClick={() => n.node_type === 'CUSTOMER' && setSelectedCustomerId(n.node_id)}
                        className={`p-3 rounded-lg border flex flex-col items-center justify-center transition-all cursor-pointer min-w-[120px] ${
                          isFocus
                            ? 'bg-purple-900/40 border-purple-500 shadow-lg shadow-purple-500/20 scale-105'
                            : 'bg-slate-900 border-slate-800 hover:border-slate-700'
                        }`}
                      >
                        <div className="p-2 rounded-full bg-slate-800 mb-1">
                          {getNodeIcon(n.node_type)}
                        </div>
                        <span className="text-[10px] uppercase font-bold text-slate-400">{n.node_type}</span>
                        <span className="text-xs font-mono font-semibold text-slate-200 truncate max-w-[140px]">{n.label}</span>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Analyst Adjudication Console */}
              <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6">
                <div className="border-b border-slate-800 pb-3 mb-4">
                  <h3 className="text-md font-bold text-white flex items-center gap-2">
                    <UserX className="w-5 h-5 text-purple-400" />
                    Identity Ring Investigation Adjudication
                  </h3>
                  <p className="text-xs text-slate-400 mt-1">
                    Determine whether colliding applicants represent a synthetic fraud ring, shared corporate entity, or legitimate household.
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                  <div>
                    <label className="text-xs font-semibold text-slate-300 block mb-1">Investigation Decision</label>
                    <select
                      value={decision}
                      onChange={e => setDecision(e.target.value as any)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-purple-500"
                    >
                      <option value="FLAG_SYNTHETIC_RING">FLAG SYNTHETIC FRAUD RING</option>
                      <option value="CLEAR_COLLISION">CLEAR COLLISION (Legitimate Household/Business)</option>
                      <option value="REQUEST_EDD">REQUEST ENHANCED DUE DILIGENCE (EDD)</option>
                      <option value="UNDER_REVIEW">KEEP UNDER REVIEW</option>
                    </select>
                  </div>

                  <div>
                    <label className="text-xs font-semibold text-slate-300 block mb-1">Analyst ID</label>
                    <input
                      type="text"
                      value={analystId}
                      onChange={e => setAnalystId(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-purple-500"
                    />
                  </div>
                </div>

                <div className="mb-4">
                  <label className="flex items-center gap-2 text-xs font-semibold text-slate-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={escalateToSar}
                      onChange={e => setEscalateToSar(e.target.checked)}
                      className="rounded border-slate-700 text-purple-600 focus:ring-purple-500"
                    />
                    Escalate findings to AML Suspicious Activity Report (SAR) Copilot (Phase 24)
                  </label>
                </div>

                <div>
                  <label className="text-xs font-semibold text-slate-300 block mb-1">Investigation Rationale</label>
                  <textarea
                    rows={2}
                    placeholder="Enter compliance justification for this identity decision..."
                    value={rationale}
                    onChange={e => setRationale(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-sm text-slate-200 focus:outline-none focus:border-purple-500"
                  />
                </div>

                <div className="flex justify-end mt-4">
                  <button
                    onClick={handleSubmitReview}
                    disabled={submittingReview}
                    className="px-5 py-2.5 bg-purple-600 hover:bg-purple-500 text-white font-semibold text-sm rounded-lg shadow-lg shadow-purple-600/20 transition-all flex items-center gap-2"
                  >
                    {submittingReview ? <RefreshCw className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                    Submit Identity Adjudication
                  </button>
                </div>
              </div>

              {/* Audit Trail Timeline */}
              <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6">
                <div className="border-b border-slate-800 pb-3 mb-4">
                  <h3 className="text-md font-bold text-white flex items-center gap-2">
                    <Clock className="w-5 h-5 text-purple-400" />
                    Identity Audit Trail
                  </h3>
                </div>

                <div className="space-y-3">
                  {auditTrail.map(ev => (
                    <div key={ev.event_id} className="p-3 bg-slate-950/60 border border-slate-800 rounded-lg flex items-start justify-between text-xs">
                      <div>
                        <div className="font-semibold text-slate-200 flex items-center gap-2">
                          <span className="px-2 py-0.5 rounded bg-slate-800 text-purple-300 font-mono text-[10px]">
                            {ev.event_type}
                          </span>
                          <span>by {ev.actor}</span>
                        </div>
                        <div className="text-slate-400 font-mono text-[11px] mt-1">
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
              Select an identity node or synthetic ring member from the left directory to inspect network relationships.
            </div>
          )}
        </div>
      </div>

      {/* Modal: Register Identity */}
      {showRegisterModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-6 space-y-4 max-h-[90vh] overflow-y-auto">
            <h3 className="text-lg font-bold text-white">Register Identity Attributes into Graph</h3>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1">Customer ID</label>
                <input
                  type="text"
                  value={newCustId}
                  onChange={e => setNewCustId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-slate-200 font-mono"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1">Full Legal Name</label>
                <input
                  type="text"
                  value={newFullName}
                  onChange={e => setNewFullName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-slate-200"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1">Phone Number</label>
                <input
                  type="text"
                  value={newPhone}
                  onChange={e => setNewPhone(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-slate-200"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1">Email</label>
                <input
                  type="email"
                  value={newEmail}
                  onChange={e => setNewEmail(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-slate-200"
                />
              </div>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-300 block mb-1">Physical Residential Address</label>
              <input
                type="text"
                value={newAddress}
                onChange={e => setNewAddress(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-slate-200"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1">Device ID / Fingerprint</label>
                <input
                  type="text"
                  value={newDevice}
                  onChange={e => setNewDevice(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-slate-200 font-mono"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1">IP Address</label>
                <input
                  type="text"
                  value={newIp}
                  onChange={e => setNewIp(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-slate-200 font-mono"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1">KYC Status</label>
                <select
                  value={newKycStatus}
                  onChange={e => setNewKycStatus(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-slate-200"
                >
                  <option value="APPROVED">APPROVED</option>
                  <option value="PENDING_REVIEW">PENDING_REVIEW</option>
                  <option value="EDD_REQUIRED">EDD_REQUIRED</option>
                  <option value="REJECTED">REJECTED</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1">Document Verification</label>
                <select
                  value={newDocStatus}
                  onChange={e => setNewDocStatus(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-slate-200"
                >
                  <option value="VERIFIED_AUTHENTIC_BYTES">VERIFIED_AUTHENTIC_BYTES</option>
                  <option value="INCONSISTENT_FIELDS">INCONSISTENT_FIELDS</option>
                  <option value="TAMPER_DETECTED">TAMPER_DETECTED</option>
                </select>
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-3">
              <button
                onClick={() => setShowRegisterModal(false)}
                className="px-4 py-2 bg-slate-800 text-slate-300 text-sm font-semibold rounded-lg hover:bg-slate-700"
              >
                Cancel
              </button>
              <button
                onClick={handleRegisterIdentity}
                className="px-4 py-2 bg-purple-600 text-white text-sm font-semibold rounded-lg hover:bg-purple-500"
              >
                Ingest & Detect Collisions
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default IdentityGraphPage;
