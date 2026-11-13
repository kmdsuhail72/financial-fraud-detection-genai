import React, { useState } from 'react';
import {
  Sliders,
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Zap,
  Activity,
  Layers,
  ArrowRight,
  TrendingUp,
  Fingerprint,
  Share2,
  Crosshair,
  Clock,
  Cpu,
  RefreshCw,
  Search,
  Filter
} from 'lucide-react';

interface SignalContributionItem {
  signal_name: string;
  raw_score: number;
  effective_weight: number;
  weighted_score: number;
  percentage_contribution: number;
}

interface DecisionOutput {
  decision_id: string;
  transaction_id: string;
  account_id: string;
  composite_risk_score: number;
  classification: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  priority: 'P0' | 'P1' | 'P2' | 'P3';
  recommended_action: 'APPROVE' | 'MONITOR' | 'CHALLENGE' | 'ESCALATE';
  signal_coverage_pct: number;
  signals_evaluated: number;
  signal_contributions: SignalContributionItem[];
  risk_reasons: string[];
  policy_version: string;
  is_advisory: boolean;
}

export const FraudDecisionEnginePage: React.FC = () => {
  // Input states
  const [transactionId, setTransactionId] = useState<string>('TXN-20261113-DEC001');
  const [accountId, setAccountId] = useState<string>('ACC-BURST-01');
  const [amount, setAmount] = useState<number>(14500.0);

  // 5 Signal scores
  const [mlScore, setMlScore] = useState<number>(0.94);
  const [includeMl, setIncludeMl] = useState<boolean>(true);

  const [uebaScore, setUebaScore] = useState<number>(0.88);
  const [includeUeba, setIncludeUeba] = useState<boolean>(true);

  const [graphScore, setGraphScore] = useState<number>(0.96);
  const [includeGraph, setIncludeGraph] = useState<boolean>(true);

  const [temporalScore, setTemporalScore] = useState<number>(0.98);
  const [includeTemporal, setIncludeTemporal] = useState<boolean>(true);

  const [threatScore, setThreatScore] = useState<number>(0.92);
  const [includeThreat, setIncludeThreat] = useState<boolean>(true);

  // Context flags
  const [isEmulator, setIsEmulator] = useState<boolean>(true);
  const [isTor, setIsTor] = useState<boolean>(true);
  const [isVelocityBurst, setIsVelocityBurst] = useState<boolean>(true);

  const [isLoadingDecision, setIsLoadingDecision] = useState<boolean>(false);
  const [priorityFilter, setPriorityFilter] = useState<string>('ALL');

  // Active decision state
  const [decision, setDecision] = useState<DecisionOutput>({
    decision_id: 'DEC-20261113-A8F19B02',
    transaction_id: 'TXN-20261113-DEC001',
    account_id: 'ACC-BURST-01',
    composite_risk_score: 0.941,
    classification: 'CRITICAL',
    priority: 'P0',
    recommended_action: 'ESCALATE',
    signal_coverage_pct: 100.0,
    signals_evaluated: 5,
    signal_contributions: [
      { signal_name: 'ml', raw_score: 0.94, effective_weight: 0.35, weighted_score: 0.329, percentage_contribution: 35.0 },
      { signal_name: 'graph', raw_score: 0.96, effective_weight: 0.20, weighted_score: 0.192, percentage_contribution: 20.4 },
      { signal_name: 'ueba', raw_score: 0.88, effective_weight: 0.20, weighted_score: 0.176, percentage_contribution: 18.7 },
      { signal_name: 'temporal', raw_score: 0.98, effective_weight: 0.15, weighted_score: 0.147, percentage_contribution: 15.6 },
      { signal_name: 'threat_intel', raw_score: 0.92, effective_weight: 0.10, weighted_score: 0.092, percentage_contribution: 9.8 }
    ],
    risk_reasons: [
      'Composite risk score of 0.94 maps to CRITICAL classification (Priority P0).',
      "Leading risk driver: 'ML' signal (score: 0.94, 35.0% contribution).",
      'Critical red flag: Hardware emulator profile observed in device metadata.',
      'Network red flag: Traffic ingress through anonymized Tor or proxy network.',
      'Temporal red flag: High-frequency transaction velocity burst within 5-minute window.',
      'Full multi-signal coverage: 100% of detection pillars evaluated.'
    ],
    policy_version: '2026.11-v1',
    is_advisory: true
  });

  // Recent decisions audit log
  const [recentDecisions, setRecentDecisions] = useState<DecisionOutput[]>([
    {
      decision_id: 'DEC-20261113-A8F19B02',
      transaction_id: 'TXN-20261113-DEC001',
      account_id: 'ACC-BURST-01',
      composite_risk_score: 0.941,
      classification: 'CRITICAL',
      priority: 'P0',
      recommended_action: 'ESCALATE',
      signal_coverage_pct: 100.0,
      signals_evaluated: 5,
      signal_contributions: [],
      risk_reasons: ['Syndicate cluster and emulator detected.'],
      policy_version: '2026.11-v1',
      is_advisory: true
    },
    {
      decision_id: 'DEC-20261113-F4C91E01',
      transaction_id: 'TXN-20261113-DEC002',
      account_id: 'ACC-TEMP-012',
      composite_risk_score: 0.785,
      classification: 'HIGH',
      priority: 'P1',
      recommended_action: 'CHALLENGE',
      signal_coverage_pct: 80.0,
      signals_evaluated: 4,
      signal_contributions: [],
      risk_reasons: ['Elevated UEBA deviation and new device.'],
      policy_version: '2026.11-v1',
      is_advisory: true
    },
    {
      decision_id: 'DEC-20261113-B1D28C03',
      transaction_id: 'TXN-20261113-DEC003',
      account_id: 'ACC-RETAIL-08',
      composite_risk_score: 0.420,
      classification: 'MEDIUM',
      priority: 'P2',
      recommended_action: 'MONITOR',
      signal_coverage_pct: 60.0,
      signals_evaluated: 3,
      signal_contributions: [],
      risk_reasons: ['Moderate velocity burst; nominal account history.'],
      policy_version: '2026.11-v1',
      is_advisory: true
    },
    {
      decision_id: 'DEC-20261113-9E2A0144',
      transaction_id: 'TXN-20261113-DEC004',
      account_id: 'ACC-NOMINAL-55',
      composite_risk_score: 0.085,
      classification: 'LOW',
      priority: 'P3',
      recommended_action: 'APPROVE',
      signal_coverage_pct: 100.0,
      signals_evaluated: 5,
      signal_contributions: [],
      risk_reasons: ['Standard recurring grocery payment.'],
      policy_version: '2026.11-v1',
      is_advisory: true
    }
  ]);

  const handleEvaluateDecision = async () => {
    setIsLoadingDecision(true);
    const payload = {
      transaction_id: transactionId,
      account_id: accountId,
      amount: amount,
      currency: 'USD',
      signals: {
        ml_score: includeMl ? mlScore : null,
        ueba_anomaly_score: includeUeba ? uebaScore : null,
        graph_risk_score: includeGraph ? graphScore : null,
        temporal_risk_score: includeTemporal ? temporalScore : null,
        threat_intel_score: includeThreat ? threatScore : null,
        metadata: {
          is_emulator: isEmulator,
          is_tor: isTor,
          velocity_burst: isVelocityBurst
        }
      }
    };

    try {
      const resp = await fetch('/decisions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (resp.ok) {
        const data = await resp.json();
        setDecision(data);
        setRecentDecisions(prev => [data, ...prev.slice(0, 9)]);
      } else {
        simulateOfflineDecision();
      }
    } catch {
      simulateOfflineDecision();
    } finally {
      setIsLoadingDecision(false);
    }
  };

  const simulateOfflineDecision = () => {
    // Renormalize active signals offline
    const activeWeights: Record<string, number> = {
      ...(includeMl ? { ml: 0.35 } : {}),
      ...(includeUeba ? { ueba: 0.20 } : {}),
      ...(includeGraph ? { graph: 0.20 } : {}),
      ...(includeTemporal ? { temporal: 0.15 } : {}),
      ...(includeThreat ? { threat_intel: 0.10 } : {})
    };

    const weightSum = Object.values(activeWeights).reduce((a, b) => a + b, 0) || 1.0;
    let score = 0;
    const contribs: SignalContributionItem[] = [];

    if (includeMl) {
      const eff = 0.35 / weightSum;
      const w = eff * mlScore;
      score += w;
      contribs.push({ signal_name: 'ml', raw_score: mlScore, effective_weight: eff, weighted_score: w, percentage_contribution: 0 });
    }
    if (includeUeba) {
      const eff = 0.20 / weightSum;
      const w = eff * uebaScore;
      score += w;
      contribs.push({ signal_name: 'ueba', raw_score: uebaScore, effective_weight: eff, weighted_score: w, percentage_contribution: 0 });
    }
    if (includeGraph) {
      const eff = 0.20 / weightSum;
      const w = eff * graphScore;
      score += w;
      contribs.push({ signal_name: 'graph', raw_score: graphScore, effective_weight: eff, weighted_score: w, percentage_contribution: 0 });
    }
    if (includeTemporal) {
      const eff = 0.15 / weightSum;
      const w = eff * temporalScore;
      score += w;
      contribs.push({ signal_name: 'temporal', raw_score: temporalScore, effective_weight: eff, weighted_score: w, percentage_contribution: 0 });
    }
    if (includeThreat) {
      const eff = 0.10 / weightSum;
      const w = eff * threatScore;
      score += w;
      contribs.push({ signal_name: 'threat_intel', raw_score: threatScore, effective_weight: eff, weighted_score: w, percentage_contribution: 0 });
    }

    const rounded = Math.min(1.0, Math.max(0.0, Math.round(score * 1000) / 1000));
    contribs.forEach(c => {
      c.percentage_contribution = rounded > 0 ? Math.round((c.weighted_score / rounded) * 1000) / 10 : 0;
    });

    let cls: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' = 'LOW';
    let pri: 'P0' | 'P1' | 'P2' | 'P3' = 'P3';
    let act: 'APPROVE' | 'MONITOR' | 'CHALLENGE' | 'ESCALATE' = 'APPROVE';

    if (rounded <= 0.35) {
      cls = 'LOW'; pri = 'P3'; act = 'APPROVE';
    } else if (rounded <= 0.70) {
      cls = 'MEDIUM'; pri = 'P2'; act = 'MONITOR';
    } else if (rounded <= 0.90) {
      cls = 'HIGH'; pri = 'P1'; act = 'CHALLENGE';
    } else {
      cls = 'CRITICAL'; pri = 'P0'; act = 'ESCALATE';
    }

    const coverage = Math.round((Object.keys(activeWeights).length / 5) * 100);
    const newDec: DecisionOutput = {
      decision_id: `DEC-20261113-${Math.random().toString(36).substring(2, 10).toUpperCase()}`,
      transaction_id: transactionId,
      account_id: accountId,
      composite_risk_score: rounded,
      classification: cls,
      priority: pri,
      recommended_action: act,
      signal_coverage_pct: coverage,
      signals_evaluated: Object.keys(activeWeights).length,
      signal_contributions: contribs,
      risk_reasons: [
        `Composite score of ${rounded.toFixed(2)} maps to ${cls} classification (${pri}).`,
        `Signal coverage: ${coverage}% (${Object.keys(activeWeights).length}/5 signals active).`,
        ...(isEmulator ? ['Hardware emulator profile observed.'] : []),
        ...(isTor ? ['Tor proxy network ingress identified.'] : []),
        ...(isVelocityBurst ? ['High-frequency transaction velocity burst.'] : [])
      ],
      policy_version: '2026.11-v1',
      is_advisory: true
    };

    setDecision(newDec);
    setRecentDecisions(prev => [newDec, ...prev.slice(0, 9)]);
  };

  const filteredDecisions = recentDecisions.filter(d => {
    if (priorityFilter === 'ALL') return true;
    return d.priority === priorityFilter;
  });

  return (
    <div className="space-y-6">
      {/* Top Advisory Notice */}
      <div className="p-4 rounded-xl border border-indigo-500/30 bg-indigo-500/10 flex items-start space-x-3">
        <Sliders className="w-6 h-6 text-indigo-400 flex-shrink-0 mt-0.5" />
        <div className="text-sm">
          <span className="font-semibold text-indigo-300">Phase 20 Multi-Signal Risk Orchestration: </span>
          <span className="text-slate-300">
            Fuses 5 specialized detection pillars: ML (35%), UEBA (20%), Graph (20%), Temporal (15%), and Threat Intel (10%).
            Missing signals are dynamically excluded and renormalized. Alert priorities (P0–P3) and recommended actions are{' '}
            <strong className="text-white">advisory decision-support aids</strong>. Human investigators retain ultimate approval authority.
          </span>
        </div>
      </div>

      {/* KPI Policy Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-4 bg-slate-900/80 border border-slate-800 rounded-xl space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Risk Policy Version</span>
            <Sliders className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-lg font-bold text-slate-100">POL-DEFAULT-V1</div>
          <div className="text-xs text-indigo-400 font-mono">Semantic: 2026.11-v1</div>
        </div>

        <div className="p-4 bg-slate-900/80 border border-slate-800 rounded-xl space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Signal Weights</span>
            <Activity className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-lg font-bold text-slate-100">5 Detection Pillars</div>
          <div className="text-xs text-cyan-400 font-mono">ML 35% · UEBA 20% · Graph 20%</div>
        </div>

        <div className="p-4 bg-slate-900/80 border border-slate-800 rounded-xl space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Alert Priority Tiers</span>
            <ShieldAlert className="w-4 h-4 text-rose-400" />
          </div>
          <div className="flex items-center space-x-2">
            <span className="px-1.5 py-0.5 bg-rose-500/20 text-rose-400 rounded text-xs font-bold font-mono">P0</span>
            <span className="px-1.5 py-0.5 bg-amber-500/20 text-amber-400 rounded text-xs font-bold font-mono">P1</span>
            <span className="px-1.5 py-0.5 bg-yellow-500/20 text-yellow-400 rounded text-xs font-bold font-mono">P2</span>
            <span className="px-1.5 py-0.5 bg-emerald-500/20 text-emerald-400 rounded text-xs font-bold font-mono">P3</span>
          </div>
          <div className="text-xs text-slate-400 font-mono">0.35 / 0.70 / 0.90 Cutoffs</div>
        </div>

        <div className="p-4 bg-slate-900/80 border border-slate-800 rounded-xl space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Decision Store</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-lg font-bold text-slate-100">Idempotent Store</div>
          <div className="text-xs text-emerald-400 font-mono">Terraform DynamoDB Foundation</div>
        </div>
      </div>

      {/* Main Grid: Simulator & Decision Card */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Decision Simulator Form */}
        <div className="lg:col-span-2 space-y-6">
          <div className="p-6 bg-slate-900/90 border border-slate-800 rounded-xl space-y-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Cpu className="w-5 h-5 text-indigo-400" />
                <h3 className="text-base font-semibold text-slate-100">Real-Time Multi-Signal Decision Simulator</h3>
              </div>
              <span className="text-xs text-slate-400">Dynamic Renormalization Active</span>
            </div>

            {/* Transaction metadata */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="text-xs text-slate-400 block mb-1">Transaction ID</label>
                <input
                  type="text"
                  value={transactionId}
                  onChange={e => setTransactionId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 font-mono"
                />
              </div>
              <div>
                <label className="text-xs text-slate-400 block mb-1">Account ID</label>
                <input
                  type="text"
                  value={accountId}
                  onChange={e => setAccountId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 font-mono"
                />
              </div>
              <div>
                <label className="text-xs text-slate-400 block mb-1">Amount ($ USD)</label>
                <input
                  type="number"
                  value={amount}
                  onChange={e => setAmount(parseFloat(e.target.value) || 0)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 font-mono"
                />
              </div>
            </div>

            {/* Signal Sliders with Exclusion Checkboxes */}
            <div className="space-y-4 pt-2 border-t border-slate-800/80">
              <div className="text-xs font-semibold text-slate-300">Pillar Telemetry Signals (Toggle checkbox to simulate missing signals):</div>

              {/* 1. ML Score */}
              <div className="p-3 bg-slate-950/70 border border-slate-800 rounded-lg space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <label className="flex items-center space-x-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={includeMl}
                      onChange={e => setIncludeMl(e.target.checked)}
                      className="rounded bg-slate-800 border-slate-700 text-indigo-600 focus:ring-0"
                    />
                    <span className="font-semibold text-slate-200">ML Fraud Probability (Base: 35%)</span>
                  </label>
                  <span className="font-mono font-bold text-slate-100">{includeMl ? mlScore.toFixed(2) : 'EXCLUDED'}</span>
                </div>
                {includeMl && (
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.01"
                    value={mlScore}
                    onChange={e => setMlScore(parseFloat(e.target.value))}
                    className="w-full accent-indigo-500"
                  />
                )}
              </div>

              {/* 2. UEBA Score */}
              <div className="p-3 bg-slate-950/70 border border-slate-800 rounded-lg space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <label className="flex items-center space-x-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={includeUeba}
                      onChange={e => setIncludeUeba(e.target.checked)}
                      className="rounded bg-slate-800 border-slate-700 text-cyan-600 focus:ring-0"
                    />
                    <span className="font-semibold text-slate-200">UEBA Behavioral Deviation (Base: 20%)</span>
                  </label>
                  <span className="font-mono font-bold text-slate-100">{includeUeba ? uebaScore.toFixed(2) : 'EXCLUDED'}</span>
                </div>
                {includeUeba && (
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.01"
                    value={uebaScore}
                    onChange={e => setUebaScore(parseFloat(e.target.value))}
                    className="w-full accent-cyan-500"
                  />
                )}
              </div>

              {/* 3. Graph Risk Score */}
              <div className="p-3 bg-slate-950/70 border border-slate-800 rounded-lg space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <label className="flex items-center space-x-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={includeGraph}
                      onChange={e => setIncludeGraph(e.target.checked)}
                      className="rounded bg-slate-800 border-slate-700 text-purple-600 focus:ring-0"
                    />
                    <span className="font-semibold text-slate-200">Graph Community & GNN Risk (Base: 20%)</span>
                  </label>
                  <span className="font-mono font-bold text-slate-100">{includeGraph ? graphScore.toFixed(2) : 'EXCLUDED'}</span>
                </div>
                {includeGraph && (
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.01"
                    value={graphScore}
                    onChange={e => setGraphScore(parseFloat(e.target.value))}
                    className="w-full accent-purple-500"
                  />
                )}
              </div>

              {/* 4. Temporal Risk Score */}
              <div className="p-3 bg-slate-950/70 border border-slate-800 rounded-lg space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <label className="flex items-center space-x-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={includeTemporal}
                      onChange={e => setIncludeTemporal(e.target.checked)}
                      className="rounded bg-slate-800 border-slate-700 text-amber-600 focus:ring-0"
                    />
                    <span className="font-semibold text-slate-200">Temporal Velocity & GRU Risk (Base: 15%)</span>
                  </label>
                  <span className="font-mono font-bold text-slate-100">{includeTemporal ? temporalScore.toFixed(2) : 'EXCLUDED'}</span>
                </div>
                {includeTemporal && (
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.01"
                    value={temporalScore}
                    onChange={e => setTemporalScore(parseFloat(e.target.value))}
                    className="w-full accent-amber-500"
                  />
                )}
              </div>

              {/* 5. Threat Intel Score */}
              <div className="p-3 bg-slate-950/70 border border-slate-800 rounded-lg space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <label className="flex items-center space-x-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={includeThreat}
                      onChange={e => setIncludeThreat(e.target.checked)}
                      className="rounded bg-slate-800 border-slate-700 text-rose-600 focus:ring-0"
                    />
                    <span className="font-semibold text-slate-200">Threat Intel IOC Reputation (Base: 10%)</span>
                  </label>
                  <span className="font-mono font-bold text-slate-100">{includeThreat ? threatScore.toFixed(2) : 'EXCLUDED'}</span>
                </div>
                {includeThreat && (
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.01"
                    value={threatScore}
                    onChange={e => setThreatScore(parseFloat(e.target.value))}
                    className="w-full accent-rose-500"
                  />
                )}
              </div>
            </div>

            {/* Context Flags */}
            <div className="flex flex-wrap gap-4 pt-2 text-xs text-slate-300">
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={isEmulator}
                  onChange={e => setIsEmulator(e.target.checked)}
                  className="rounded bg-slate-800 border-slate-700 text-indigo-600"
                />
                <span>Emulator Device Observed</span>
              </label>
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={isTor}
                  onChange={e => setIsTor(e.target.checked)}
                  className="rounded bg-slate-800 border-slate-700 text-indigo-600"
                />
                <span>Tor/VPN Ingress Observed</span>
              </label>
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={isVelocityBurst}
                  onChange={e => setIsVelocityBurst(e.target.checked)}
                  className="rounded bg-slate-800 border-slate-700 text-indigo-600"
                />
                <span>Velocity Burst Observed</span>
              </label>
            </div>

            <button
              onClick={handleEvaluateDecision}
              disabled={isLoadingDecision}
              className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-semibold transition flex items-center justify-center space-x-2 shadow-lg shadow-indigo-600/20"
            >
              {isLoadingDecision ? <RefreshCw className="w-4 h-4 animate-spin" /> : <span>Orchestrate Real-Time Decision</span>}
            </button>
          </div>
        </div>

        {/* Right Column: Orchestrated Decision Output Card */}
        <div className="space-y-6">
          <div className="p-6 bg-slate-900/90 border border-slate-800 rounded-xl space-y-5">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-semibold text-slate-100">Decision Outcome</h3>
              <span className="font-mono text-xs text-slate-400">{decision.decision_id}</span>
            </div>

            {/* Priority & Action Badges */}
            <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-400">Alert Priority</span>
                <span
                  className={`px-3 py-1 rounded-full text-xs font-bold font-mono tracking-wider ${
                    decision.priority === 'P0'
                      ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                      : decision.priority === 'P1'
                      ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                      : decision.priority === 'P2'
                      ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30'
                      : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                  }`}
                >
                  {decision.priority} · {decision.classification}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-400">Recommended Action</span>
                <span className="text-xs font-bold text-slate-100 font-mono px-2 py-0.5 rounded bg-slate-800 border border-slate-700">
                  {decision.recommended_action}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-400">Signal Coverage</span>
                <span className="text-xs font-mono font-bold text-cyan-400">{decision.signal_coverage_pct}% ({decision.signals_evaluated}/5)</span>
              </div>

              {/* Composite Risk Score Bar */}
              <div className="space-y-1 pt-1">
                <div className="flex justify-between text-xs">
                  <span className="text-slate-400">Composite Risk Score</span>
                  <span className="font-mono font-bold text-slate-100">{decision.composite_risk_score.toFixed(3)}</span>
                </div>
                <div className="w-full bg-slate-800 rounded-full h-2.5 overflow-hidden">
                  <div
                    className={`h-2.5 rounded-full transition-all duration-500 ${
                      decision.composite_risk_score > 0.90
                        ? 'bg-rose-500'
                        : decision.composite_risk_score > 0.70
                        ? 'bg-amber-500'
                        : decision.composite_risk_score > 0.35
                        ? 'bg-yellow-500'
                        : 'bg-emerald-500'
                    }`}
                    style={{ width: `${Math.max(5, decision.composite_risk_score * 100)}%` }}
                  />
                </div>
              </div>
            </div>

            {/* Signal Attribution Breakdown */}
            <div className="space-y-2">
              <div className="text-xs font-semibold text-slate-300">Renormalized Signal Attribution:</div>
              <div className="space-y-1.5">
                {decision.signal_contributions.map(sig => (
                  <div key={sig.signal_name} className="p-2 bg-slate-950/60 rounded border border-slate-800/80 text-xs flex justify-between items-center">
                    <div>
                      <span className="font-mono font-semibold uppercase text-indigo-300">{sig.signal_name}</span>
                      <span className="text-slate-500 ml-1.5 text-[11px] font-mono">(raw: {sig.raw_score.toFixed(2)})</span>
                    </div>
                    <div className="font-mono text-slate-300 text-right">
                      <span>+{sig.weighted_score.toFixed(3)} </span>
                      <span className="text-slate-500 text-[10px]">({sig.percentage_contribution}%)</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Explainable Decision Reasons */}
            <div className="space-y-1.5 pt-2 border-t border-slate-800/80">
              <div className="text-xs font-semibold text-slate-300">Decision Evidence & Reasons:</div>
              <ul className="space-y-1">
                {decision.risk_reasons.map((r, i) => (
                  <li key={i} className="text-xs text-slate-400 flex items-start space-x-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 mt-1 flex-shrink-0" />
                    <span>{r}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Section: Past Evaluated Decisions Table */}
      <div className="p-6 bg-slate-900/90 border border-slate-800 rounded-xl space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center space-x-2">
            <Layers className="w-5 h-5 text-indigo-400" />
            <h3 className="text-base font-semibold text-slate-100">Evaluated Decisions History (Idempotent Store)</h3>
          </div>

          {/* Priority Filter */}
          <div className="flex items-center space-x-2 text-xs">
            <span className="text-slate-400">Filter Priority:</span>
            {['ALL', 'P0', 'P1', 'P2', 'P3'].map(p => (
              <button
                key={p}
                onClick={() => setPriorityFilter(p)}
                className={`px-2.5 py-1 rounded font-mono font-medium transition ${
                  priorityFilter === p
                    ? 'bg-indigo-600 text-white'
                    : 'bg-slate-800 text-slate-400 hover:text-slate-200'
                }`}
              >
                {p}
              </button>
            ))}
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-slate-950/80 text-slate-400 border-b border-slate-800 font-mono uppercase text-[11px]">
              <tr>
                <th className="py-2.5 px-3">Decision ID</th>
                <th className="py-2.5 px-3">Transaction</th>
                <th className="py-2.5 px-3">Account</th>
                <th className="py-2.5 px-3">Priority</th>
                <th className="py-2.5 px-3">Score</th>
                <th className="py-2.5 px-3">Coverage</th>
                <th className="py-2.5 px-3">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {filteredDecisions.map(d => (
                <tr key={d.decision_id} className="hover:bg-slate-800/40 transition">
                  <td className="py-2.5 px-3 font-semibold text-slate-200">{d.decision_id}</td>
                  <td className="py-2.5 px-3 text-slate-400">{d.transaction_id}</td>
                  <td className="py-2.5 px-3 text-slate-400">{d.account_id}</td>
                  <td className="py-2.5 px-3">
                    <span
                      className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                        d.priority === 'P0'
                          ? 'bg-rose-500/20 text-rose-400'
                          : d.priority === 'P1'
                          ? 'bg-amber-500/20 text-amber-400'
                          : d.priority === 'P2'
                          ? 'bg-yellow-500/20 text-yellow-400'
                          : 'bg-emerald-500/20 text-emerald-400'
                      }`}
                    >
                      {d.priority}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 font-bold text-slate-200">{d.composite_risk_score.toFixed(3)}</td>
                  <td className="py-2.5 px-3 text-cyan-400">{d.signal_coverage_pct}%</td>
                  <td className="py-2.5 px-3">
                    <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                      {d.recommended_action}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

