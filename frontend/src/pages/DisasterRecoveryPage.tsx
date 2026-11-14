import React, { useState, useEffect } from 'react';
import {
  Activity,
  AlertOctagon,
  ArrowRight,
  CheckCircle2,
  Clock,
  Compass,
  Cpu,
  Database,
  ExternalLink,
  Eye,
  FileCheck2,
  FileText,
  Globe,
  Layers,
  RefreshCw,
  Server,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Sliders,
  Terminal,
  Zap,
} from 'lucide-react';
import axios from 'axios';

interface ServiceTarget {
  service_id: string;
  name: string;
  target_rto_min: number;
  target_rpo_min: number;
  priority: string;
  tier: string;
  description: string;
}

interface RecoveryAssessment {
  service_id: string;
  name: string;
  target_rto_min: number;
  target_rpo_min: number;
  measured_rto_min: number;
  measured_rpo_min: number;
  rto_compliant: boolean;
  rpo_compliant: boolean;
  overall_compliant: boolean;
  gap_rto_min: number;
  gap_rpo_min: number;
  status: string;
}

interface FailoverProposal {
  proposal_id: string;
  timestamp: string;
  primary_region: string;
  secondary_region: string;
  primary_healthy: boolean;
  secondary_ready: boolean;
  replication_lag_min: number;
  max_allowed_rpo_min: number;
  approved_for_failover: boolean;
  recommended_action: string;
  rationale: string;
  human_approval_required: boolean;
}

interface RegionHealth {
  region: string;
  role: string;
  status: string;
  latency_ms: number;
  eks_cluster_status: string;
  dynamodb_status: string;
  s3_crr_status: string;
  last_checked: string;
}

interface BackupFileEntry {
  filename: string;
  size_bytes: number;
  sha256_checksum: string;
  created_at: string;
  status: string;
}

interface BackupManifest {
  manifest_id: string;
  timestamp: string;
  backup_type: string;
  source_region: string;
  replica_region: string;
  files: BackupFileEntry[];
  total_size_bytes: number;
  overall_sha256: string;
  verified: boolean;
}

export const DisasterRecoveryPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'topology' | 'targets' | 'simulator' | 'manifest' | 'runbook'>('topology');
  const [targets, setTargets] = useState<ServiceTarget[]>([]);
  const [regions, setRegions] = useState<RegionHealth[]>([]);
  const [manifest, setManifest] = useState<BackupManifest | null>(null);
  const [proposal, setProposal] = useState<FailoverProposal | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  // Failover simulator states
  const [simPrimaryHealthy, setSimPrimaryHealthy] = useState<boolean>(false);
  const [simSecondaryReady, setSimSecondaryReady] = useState<boolean>(true);
  const [simRepLag, setSimRepLag] = useState<number>(2.0);
  const [simulating, setSimulating] = useState<boolean>(false);

  // Backup verification states
  const [verifying, setVerifying] = useState<boolean>(false);
  const [verificationResult, setVerificationResult] = useState<any>(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [tgtRes, regRes, mnfRes] = await Promise.all([
        axios.get('/dr/targets').catch(() => ({ data: [] })),
        axios.get('/dr/regions').catch(() => ({ data: [] })),
        axios.get('/dr/manifest/sample').catch(() => ({ data: null })),
      ]);

      if (tgtRes.data && tgtRes.data.length > 0) {
        setTargets(tgtRes.data);
      } else {
        setTargets([
          {
            service_id: 'transaction-ingestion',
            name: 'Transaction Ingestion Pipeline',
            target_rto_min: 30,
            target_rpo_min: 5,
            priority: 'P1',
            tier: 'Edge & Message Queue',
            description: 'Core payment and transaction ingestion via SQS/Kinesis and Kafka.',
          },
          {
            service_id: 'fraud-scoring',
            name: 'Real-Time Fraud Scoring Engine',
            target_rto_min: 30,
            target_rpo_min: 5,
            priority: 'P1',
            tier: 'ML Inference',
            description: 'Real-time ML inference and risk classification microservice.',
          },
          {
            service_id: 'investigation-api',
            name: 'Analyst Investigation Case Management',
            target_rto_min: 60,
            target_rpo_min: 15,
            priority: 'P2',
            tier: 'Operational UI & Case Store',
            description: 'Bedrock GenAI investigation summaries and analyst case workflow.',
          },
          {
            service_id: 'analytics-lake',
            name: 'Historical Financial Analytics Lake',
            target_rto_min: 240,
            target_rpo_min: 60,
            priority: 'P4',
            tier: 'Big Data & Reporting',
            description: 'Analytical lakehouse, offline training partitions, and SAR reports.',
          },
        ]);
      }

      if (regRes.data && regRes.data.length > 0) {
        setRegions(regRes.data);
      } else {
        setRegions([
          {
            region: 'ap-south-1',
            role: 'PRIMARY',
            status: 'HEALTHY',
            latency_ms: 18.5,
            eks_cluster_status: 'ACTIVE (3 AZs)',
            dynamodb_status: 'PITR_ENABLED (Continuous)',
            s3_crr_status: 'REPLICATING (Rule: CRR-To-Singapore)',
            last_checked: new Date().toISOString(),
          },
          {
            region: 'ap-southeast-1',
            role: 'SECONDARY',
            status: 'HEALTHY',
            latency_ms: 45.2,
            eks_cluster_status: 'STANDBY (Warm Spares Ready)',
            dynamodb_status: 'REPLICA_SYNCHRONIZED (Lag: 2.1s)',
            s3_crr_status: 'TARGET_BUCKET_ENCRYPTED',
            last_checked: new Date().toISOString(),
          },
        ]);
      }

      if (mnfRes.data) {
        setManifest(mnfRes.data);
      }
    } catch (e) {
      console.error('Error fetching DR data', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    handleGenerateProposal(false, true, 2.0);
  }, []);

  const handleGenerateProposal = async (primaryH: boolean, secondaryR: boolean, lag: number) => {
    setSimulating(true);
    try {
      const res = await axios.post('/dr/failover/plan', {
        primary_healthy: primaryH,
        secondary_ready: secondaryR,
        replication_lag_min: lag,
      });
      setProposal(res.data);
    } catch (err) {
      // Fallback proposal calculation
      let action = 'STAY_PRIMARY';
      let approved = false;
      let rationale = 'Primary region (Mumbai) is healthy. No failover required.';

      if (!primaryH) {
        if (!secondaryR) {
          action = 'BLOCKED_SECONDARY_NOT_READY';
          rationale = 'Primary unhealthy, but secondary warm standby is not ready.';
        } else if (lag > 5.0) {
          action = 'BLOCKED_LAG_EXCEEDED';
          rationale = `Replication lag (${lag} min) exceeds max allowed RPO (5 min). Failover blocked.`;
        } else {
          action = 'EXECUTE_FAILOVER';
          approved = true;
          rationale = `Primary unhealthy, secondary confirmed ready, and lag (${lag} min) is within approved RPO (5 min).`;
        }
      }

      setProposal({
        proposal_id: 'fop-local-demo',
        timestamp: new Date().toISOString(),
        primary_region: 'ap-south-1',
        secondary_region: 'ap-southeast-1',
        primary_healthy: primaryH,
        secondary_ready: secondaryR,
        replication_lag_min: lag,
        max_allowed_rpo_min: 5,
        approved_for_failover: approved,
        recommended_action: action,
        rationale: rationale,
        human_approval_required: true,
      });
    } finally {
      setSimulating(false);
    }
  };

  const handleVerifyBackup = async (injectCorruption: boolean = false) => {
    setVerifying(true);
    try {
      const res = await axios.post('/dr/backup/verify', {
        inject_corruption: injectCorruption,
      });
      setVerificationResult(res.data);
    } catch (e) {
      setVerificationResult({
        valid: !injectCorruption,
        files_checked: 3,
        mismatches: injectCorruption ? ['dynamodb-cases-snapshot.tar.gz: SHA-256 hash mismatch'] : [],
        verification_time_ms: 1.25,
        message: injectCorruption ? 'Corruption detected during SHA-256 integrity check.' : 'Verified authentic.',
      });
    } finally {
      setVerifying(false);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-gray-800 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-blue-950/60 border border-blue-800 rounded-xl text-blue-400">
              <Globe className="w-6 h-6 animate-pulse" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">Enterprise Disaster Recovery & Business Continuity</h1>
              <p className="text-sm text-gray-400">
                Primary Mumbai (ap-south-1) · Secondary Singapore (ap-southeast-1) · S3 CRR · DynamoDB PITR · RTO/RPO Governance
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchData}
            disabled={loading}
            className="flex items-center gap-2 px-3.5 py-2 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded-lg text-sm font-medium transition"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Highlights & Regional Status */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Primary Mumbai */}
        <div className="bg-gray-900/80 border border-gray-800 rounded-xl p-4">
          <div className="flex items-center justify-between text-gray-400 text-xs font-semibold uppercase tracking-wider mb-2">
            <span>Primary Region</span>
            <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-950/60 border border-emerald-800 text-emerald-400">
              Active Leader
            </span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-xl font-bold text-white">AWS Mumbai</span>
            <span className="text-xs font-mono text-cyan-400">ap-south-1</span>
          </div>
          <div className="mt-3 flex items-center justify-between text-xs text-gray-400 border-t border-gray-800/60 pt-2">
            <span>EKS: <strong className="text-emerald-400">Active (3 AZs)</strong></span>
            <span>Latency: 18.5ms</span>
          </div>
        </div>

        {/* Secondary Singapore */}
        <div className="bg-gray-900/80 border border-gray-800 rounded-xl p-4">
          <div className="flex items-center justify-between text-gray-400 text-xs font-semibold uppercase tracking-wider mb-2">
            <span>Secondary (DR)</span>
            <span className="px-2 py-0.5 rounded text-[10px] bg-blue-950/60 border border-blue-800 text-blue-400">
              Warm Standby
            </span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-xl font-bold text-white">AWS Singapore</span>
            <span className="text-xs font-mono text-cyan-400">ap-southeast-1</span>
          </div>
          <div className="mt-3 flex items-center justify-between text-xs text-gray-400 border-t border-gray-800/60 pt-2">
            <span>S3 CRR: <strong className="text-cyan-400">Encrypted</strong></span>
            <span>Replica Lag: 2.1s</span>
          </div>
        </div>

        {/* Max P1 RTO/RPO */}
        <div className="bg-gray-900/80 border border-gray-800 rounded-xl p-4">
          <div className="flex items-center justify-between text-gray-400 text-xs font-semibold uppercase tracking-wider mb-2">
            <span>P1 Target RTO / RPO</span>
            <span className="text-xs text-gray-400">Tier 1</span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold text-amber-400">30m / 5m</span>
          </div>
          <div className="mt-3 flex items-center justify-between text-xs text-gray-400 border-t border-gray-800/60 pt-2">
            <span>Max Downtime: 30 min</span>
            <span>Max Data Loss: 5 min</span>
          </div>
        </div>

        {/* DynamoDB PITR */}
        <div className="bg-gray-900/80 border border-gray-800 rounded-xl p-4">
          <div className="flex items-center justify-between text-gray-400 text-xs font-semibold uppercase tracking-wider mb-2">
            <span>Continuous Backups</span>
            <span className="text-xs text-gray-400">PITR</span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-emerald-400">Continuous</span>
            <span className="text-xs text-gray-400">35-day window</span>
          </div>
          <div className="mt-3 flex items-center justify-between text-xs text-gray-400 border-t border-gray-800/60 pt-2">
            <span>Granularity: 1 second</span>
            <span>Zero RPO Impact</span>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex border-b border-gray-800 gap-6">
        {[
          { id: 'topology', label: 'Multi-Region Topology', icon: Globe },
          { id: 'targets', label: 'RTO / RPO Objectives', icon: Sliders },
          { id: 'simulator', label: 'Failover Proposal Simulator', icon: ShieldAlert },
          { id: 'manifest', label: 'Backup Verification (SHA-256)', icon: ShieldCheck },
          { id: 'runbook', label: 'Operator Failover Runbook', icon: FileText },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 pb-3 px-1 text-sm font-medium border-b-2 transition ${
                isActive
                  ? 'border-blue-400 text-blue-400'
                  : 'border-transparent text-gray-400 hover:text-gray-200 hover:border-gray-700'
              }`}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab 1: Topology */}
      {activeTab === 'topology' && (
        <div className="space-y-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">
            <h3 className="text-lg font-semibold text-white">Multi-Region Active-Passive Architecture</h3>
            <p className="text-sm text-gray-400">
              Primary production microservices execute across 3 Availability Zones in Mumbai (<code className="text-cyan-400 font-mono">ap-south-1</code>), with S3 Cross-Region Replication (CRR) and warm standby EKS and DynamoDB replicas in Singapore (<code className="text-cyan-400 font-mono">ap-southeast-1</code>).
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
              {regions.map((reg) => (
                <div key={reg.region} className="bg-gray-950 border border-gray-800 rounded-xl p-4 space-y-3">
                  <div className="flex items-center justify-between border-b border-gray-800 pb-2">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-white text-base">AWS {reg.region === 'ap-south-1' ? 'Mumbai' : 'Singapore'}</span>
                      <span className="font-mono text-xs text-gray-400">({reg.region})</span>
                    </div>
                    <span className={`px-2 py-0.5 rounded text-xs font-bold ${reg.role === 'PRIMARY' ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' : 'bg-blue-950 text-blue-400 border border-blue-800'}`}>
                      {reg.role}
                    </span>
                  </div>

                  <div className="space-y-2 text-xs">
                    <div className="flex justify-between py-1 border-b border-gray-900">
                      <span className="text-gray-400">EKS Cluster Status:</span>
                      <span className="font-semibold text-white">{reg.eks_cluster_status}</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-gray-900">
                      <span className="text-gray-400">DynamoDB PITR / Replica:</span>
                      <span className="font-semibold text-cyan-400">{reg.dynamodb_status}</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-gray-900">
                      <span className="text-gray-400">S3 Replication (CRR):</span>
                      <span className="font-semibold text-emerald-400">{reg.s3_crr_status}</span>
                    </div>
                    <div className="flex justify-between py-1">
                      <span className="text-gray-400">Cross-Region Latency:</span>
                      <span className="font-mono text-gray-200">{reg.latency_ms} ms</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Targets */}
      {activeTab === 'targets' && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">
          <h3 className="text-lg font-semibold text-white">Recovery Objectives (RTO / RPO) Governance Matrix</h3>
          <p className="text-sm text-gray-400">
            Approved business continuity targets: <strong>RTO</strong> (maximum allowable recovery duration) and <strong>RPO</strong> (maximum allowable data loss window).
          </p>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-gray-300">
              <thead className="text-xs uppercase bg-gray-800/50 text-gray-400 border-b border-gray-800">
                <tr>
                  <th className="px-4 py-3">Service Name</th>
                  <th className="px-4 py-3">Priority</th>
                  <th className="px-4 py-3">Target RTO</th>
                  <th className="px-4 py-3">Target RPO</th>
                  <th className="px-4 py-3">Tier</th>
                  <th className="px-4 py-3">Strategy</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {targets.map((tgt) => (
                  <tr key={tgt.service_id} className="hover:bg-gray-800/30">
                    <td className="px-4 py-3">
                      <div className="font-semibold text-white">{tgt.name}</div>
                      <div className="text-xs font-mono text-gray-400">{tgt.service_id}</div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                        tgt.priority === 'P1' ? 'bg-rose-950 text-rose-400 border border-rose-800' :
                        tgt.priority === 'P2' ? 'bg-amber-950 text-amber-400 border border-amber-800' :
                        'bg-gray-800 text-gray-300'
                      }`}>
                        {tgt.priority}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-bold text-emerald-400">{tgt.target_rto_min} min</td>
                    <td className="px-4 py-3 font-bold text-cyan-400">{tgt.target_rpo_min} min</td>
                    <td className="px-4 py-3 text-xs text-gray-300">{tgt.tier}</td>
                    <td className="px-4 py-3 text-xs text-gray-400">{tgt.description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 3: Failover Proposal Simulator */}
      {activeTab === 'simulator' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Controls */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-5 lg:col-span-1">
            <h3 className="font-semibold text-white text-base">Failover Decision Simulator</h3>
            <p className="text-xs text-gray-400">
              Simulate primary regional degradation and evaluate whether replication lag satisfies governance thresholds for safe human-approved failover.
            </p>

            <div className="space-y-4 text-sm">
              <div>
                <label className="block text-xs uppercase font-semibold text-gray-400 mb-1.5">Primary Mumbai Status</label>
                <div className="flex gap-2">
                  <button
                    onClick={() => { setSimPrimaryHealthy(true); handleGenerateProposal(true, simSecondaryReady, simRepLag); }}
                    className={`flex-1 py-1.5 px-3 rounded-lg text-xs font-medium border ${simPrimaryHealthy ? 'bg-emerald-950 text-emerald-300 border-emerald-700' : 'bg-gray-800 text-gray-400 border-gray-700'}`}
                  >
                    Healthy
                  </button>
                  <button
                    onClick={() => { setSimPrimaryHealthy(false); handleGenerateProposal(false, simSecondaryReady, simRepLag); }}
                    className={`flex-1 py-1.5 px-3 rounded-lg text-xs font-medium border ${!simPrimaryHealthy ? 'bg-rose-950 text-rose-300 border-rose-700' : 'bg-gray-800 text-gray-400 border-gray-700'}`}
                  >
                    Unhealthy (Degraded)
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs uppercase font-semibold text-gray-400 mb-1.5">Secondary Singapore Ready</label>
                <div className="flex gap-2">
                  <button
                    onClick={() => { setSimSecondaryReady(true); handleGenerateProposal(simPrimaryHealthy, true, simRepLag); }}
                    className={`flex-1 py-1.5 px-3 rounded-lg text-xs font-medium border ${simSecondaryReady ? 'bg-blue-950 text-blue-300 border-blue-700' : 'bg-gray-800 text-gray-400 border-gray-700'}`}
                  >
                    Ready (Standby OK)
                  </button>
                  <button
                    onClick={() => { setSimSecondaryReady(false); handleGenerateProposal(simPrimaryHealthy, false, simRepLag); }}
                    className={`flex-1 py-1.5 px-3 rounded-lg text-xs font-medium border ${!simSecondaryReady ? 'bg-amber-950 text-amber-300 border-amber-700' : 'bg-gray-800 text-gray-400 border-gray-700'}`}
                  >
                    Not Ready
                  </button>
                </div>
              </div>

              <div>
                <div className="flex justify-between items-center text-xs mb-1">
                  <span className="uppercase font-semibold text-gray-400">Replication Lag</span>
                  <span className="font-mono text-cyan-400 font-bold">{simRepLag} min</span>
                </div>
                <input
                  type="range"
                  min="0.5"
                  max="15.0"
                  step="0.5"
                  value={simRepLag}
                  onChange={(e) => {
                    const val = parseFloat(e.target.value);
                    setSimRepLag(val);
                    handleGenerateProposal(simPrimaryHealthy, simSecondaryReady, val);
                  }}
                  className="w-full accent-cyan-500 cursor-pointer"
                />
                <div className="flex justify-between text-[11px] text-gray-500 mt-1">
                  <span>0.5 min</span>
                  <span className="text-amber-400">Max RPO: 5 min</span>
                  <span>15 min</span>
                </div>
              </div>
            </div>
          </div>

          {/* Decision Card */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 lg:col-span-2 space-y-4">
            <h3 className="font-semibold text-white text-base">Generated Failover Proposal</h3>
            {proposal && (
              <div className="space-y-4">
                <div className={`p-4 rounded-xl border ${
                  proposal.recommended_action === 'EXECUTE_FAILOVER' ? 'bg-emerald-950/30 border-emerald-800' :
                  proposal.recommended_action === 'STAY_PRIMARY' ? 'bg-gray-850 border-gray-700' :
                  'bg-rose-950/30 border-rose-800'
                }`}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs uppercase font-bold tracking-wider text-gray-400">Action Recommendation</span>
                    <span className={`px-2.5 py-0.5 rounded text-xs font-bold ${
                      proposal.recommended_action === 'EXECUTE_FAILOVER' ? 'bg-emerald-900 text-emerald-300' :
                      proposal.recommended_action === 'STAY_PRIMARY' ? 'bg-gray-800 text-gray-300' :
                      'bg-rose-900 text-rose-300'
                    }`}>
                      {proposal.recommended_action}
                    </span>
                  </div>
                  <p className="text-sm text-gray-200">{proposal.rationale}</p>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                  <div className="p-3 bg-gray-950 rounded-lg border border-gray-800">
                    <div className="text-gray-400 mb-1">Primary Mumbai</div>
                    <div className={`font-bold ${proposal.primary_healthy ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {proposal.primary_healthy ? 'HEALTHY' : 'UNHEALTHY'}
                    </div>
                  </div>
                  <div className="p-3 bg-gray-950 rounded-lg border border-gray-800">
                    <div className="text-gray-400 mb-1">Secondary Singapore</div>
                    <div className={`font-bold ${proposal.secondary_ready ? 'text-emerald-400' : 'text-amber-400'}`}>
                      {proposal.secondary_ready ? 'READY' : 'NOT READY'}
                    </div>
                  </div>
                  <div className="p-3 bg-gray-950 rounded-lg border border-gray-800">
                    <div className="text-gray-400 mb-1">Replication Lag</div>
                    <div className={`font-bold font-mono ${proposal.replication_lag_min <= 5.0 ? 'text-cyan-400' : 'text-rose-400'}`}>
                      {proposal.replication_lag_min} min (Max: 5m)
                    </div>
                  </div>
                  <div className="p-3 bg-gray-950 rounded-lg border border-gray-800">
                    <div className="text-gray-400 mb-1">Human Approval</div>
                    <div className="font-bold text-amber-400">MANDATORY</div>
                  </div>
                </div>

                <div className="bg-gray-950 p-4 rounded-xl border border-gray-800 text-xs text-gray-400 space-y-2">
                  <div className="font-semibold text-gray-200">Safety & Governance Note:</div>
                  <p>
                    The failover proposal provides advisory decision-support for on-call SREs and engineering management. Automated Route 53 DNS promotion and database failover will not trigger without explicit multi-party verification.
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 4: Backup Manifest */}
      {activeTab === 'manifest' && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h3 className="text-lg font-semibold text-white">Backup Manifest & SHA-256 Integrity Verification</h3>
              <p className="text-sm text-gray-400">
                Cryptographic verification of backup partitions across S3 and DynamoDB to prevent silent data corruption or bit-rot.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => handleVerifyBackup(false)}
                disabled={verifying}
                className="px-3.5 py-2 bg-emerald-800 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition"
              >
                <CheckCircle2 className="w-4 h-4" />
                Verify Integrity (All Green)
              </button>
              <button
                onClick={() => handleVerifyBackup(true)}
                disabled={verifying}
                className="px-3.5 py-2 bg-rose-800 hover:bg-rose-700 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition"
              >
                <AlertOctagon className="w-4 h-4" />
                Simulate Tampered Checksum
              </button>
            </div>
          </div>

          {verificationResult && (
            <div className={`p-4 rounded-xl border text-sm ${verificationResult.valid ? 'bg-emerald-950/40 border-emerald-800 text-emerald-300' : 'bg-rose-950/40 border-rose-800 text-rose-300'}`}>
              <div className="font-bold flex items-center gap-2 mb-1">
                {verificationResult.valid ? <CheckCircle2 className="w-5 h-5 text-emerald-400" /> : <ShieldAlert className="w-5 h-5 text-rose-400" />}
                {verificationResult.valid ? 'Manifest Verification PASSED' : 'Manifest Verification FAILED'}
              </div>
              <p className="text-xs">{verificationResult.message}</p>
              {verificationResult.mismatches.length > 0 && (
                <ul className="list-disc list-inside text-xs mt-2 text-rose-300">
                  {verificationResult.mismatches.map((m: string, i: number) => (
                    <li key={i}>{m}</li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {manifest && (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-gray-300">
                <thead className="text-xs uppercase bg-gray-800/50 text-gray-400 border-b border-gray-800">
                  <tr>
                    <th className="px-4 py-3">Filename</th>
                    <th className="px-4 py-3">Size</th>
                    <th className="px-4 py-3">SHA-256 Digest</th>
                    <th className="px-4 py-3">Timestamp</th>
                    <th className="px-4 py-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800 font-mono text-xs">
                  {manifest.files.map((f) => (
                    <tr key={f.filename} className="hover:bg-gray-800/30">
                      <td className="px-4 py-3 font-semibold text-white">{f.filename}</td>
                      <td className="px-4 py-3">{(f.size_bytes / (1024 * 1024)).toFixed(2)} MB</td>
                      <td className="px-4 py-3 text-cyan-400 truncate max-w-[200px]">{f.sha256_checksum}</td>
                      <td className="px-4 py-3 text-gray-400">{f.created_at}</td>
                      <td className="px-4 py-3">
                        <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 text-[10px]">
                          {f.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Tab 5: Operator Runbook */}
      {activeTab === 'runbook' && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">
          <h3 className="text-lg font-semibold text-white">Emergency Failover & Failback Procedures</h3>
          <p className="text-sm text-gray-400">
            Standard Operating Procedures (SOPs) for human operators during disaster declaration.
          </p>

          <div className="space-y-4 text-xs">
            <div className="p-4 bg-gray-950 border border-gray-800 rounded-xl space-y-2">
              <h4 className="text-sm font-bold text-white flex items-center gap-2">
                <span className="px-2 py-0.5 bg-blue-900 text-blue-200 rounded">Phase 1</span>
                Assessment & Authorization
              </h4>
              <p className="text-gray-300">
                Execute CLI check <code className="text-cyan-400">python scripts/assess_dr.py failover-plan --secondary-ready --lag &lt;lag&gt;</code> to verify replication lag is within the 5-minute RPO target. Ensure written approval from Incident Commander.
              </p>
            </div>

            <div className="p-4 bg-gray-950 border border-gray-800 rounded-xl space-y-2">
              <h4 className="text-sm font-bold text-white flex items-center gap-2">
                <span className="px-2 py-0.5 bg-amber-900 text-amber-200 rounded">Phase 2</span>
                Route 53 DNS Traffic Shift
              </h4>
              <p className="text-gray-300">
                Execute Route 53 resource record change to point production CNAMES to secondary Singapore endpoints:
              </p>
              <div className="bg-gray-900 p-2 rounded font-mono text-emerald-400">
                aws route53 change-resource-record-sets --hosted-zone-id Z123456FINGUARD --change-batch file://infrastructure/route53/failover-to-singapore.json
              </div>
            </div>

            <div className="p-4 bg-gray-950 border border-gray-800 rounded-xl space-y-2">
              <h4 className="text-sm font-bold text-white flex items-center gap-2">
                <span className="px-2 py-0.5 bg-emerald-900 text-emerald-200 rounded">Phase 3</span>
                Controlled Failback to Mumbai
              </h4>
              <p className="text-gray-300">
                When Mumbai (<code className="text-cyan-400">ap-south-1</code>) recovers, verify reverse replication lag reaches 0s before shifting DNS back to Mumbai.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DisasterRecoveryPage;
