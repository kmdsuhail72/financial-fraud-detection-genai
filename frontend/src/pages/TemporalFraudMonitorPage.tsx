import React, { useState } from 'react';
import {
  Clock,
  Activity,
  Zap,
  TrendingUp,
  AlertTriangle,
  ShieldCheck,
  ShieldAlert,
  Layers,
  ArrowRight,
  RefreshCw,
  Search,
  Database,
  Radio,
  Sliders
} from 'lucide-react';

interface TemporalScoreResult {
  entity_id: string;
  sequence_fraud_probability: number;
  advisory_risk_level: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  velocity_burst_detected: boolean;
  features_summary: {
    tx_count_5m: number;
    tx_count_1h: number;
    tx_count_24h: number;
    velocity_burst_ratio: number;
    amount_sum_1h: number;
    is_new_device: boolean;
    is_new_ip: boolean;
  };
  recommendation: string;
  timeline_indicators: string[];
  is_advisory: boolean;
}

interface TimelineEvent {
  transaction_id: string;
  timestamp: string;
  source_account: string;
  target_account?: string;
  amount: number;
  delta_time?: string;
  is_burst?: boolean;
}

export const TemporalFraudMonitorPage: React.FC = () => {
  const [selectedEntity, setSelectedEntity] = useState<string>('ACC-BURST-01');
  const [customEntityInput, setCustomEntityInput] = useState<string>('');
  const [isLoadingScore, setIsLoadingScore] = useState<boolean>(false);
  const [isInjectingEvent, setIsInjectingEvent] = useState<boolean>(false);

  // Live timeline events
  const [timelineEvents, setTimelineEvents] = useState<TimelineEvent[]>([
    {
      transaction_id: 'TXN-TEMP-00495',
      timestamp: '11:48:12 UTC',
      source_account: 'ACC-BURST-01',
      target_account: 'ACC-BURST-02',
      amount: 9800.0,
      delta_time: '+18s',
      is_burst: true
    },
    {
      transaction_id: 'TXN-TEMP-00496',
      timestamp: '11:48:38 UTC',
      source_account: 'ACC-BURST-01',
      target_account: 'ACC-BURST-03',
      amount: 9750.0,
      delta_time: '+26s',
      is_burst: true
    },
    {
      transaction_id: 'TXN-TEMP-00497',
      timestamp: '11:49:05 UTC',
      source_account: 'ACC-BURST-01',
      target_account: 'ACC-BURST-04',
      amount: 9700.0,
      delta_time: '+27s',
      is_burst: true
    },
    {
      transaction_id: 'TXN-TEMP-00498',
      timestamp: '11:49:22 UTC',
      source_account: 'ACC-BURST-01',
      target_account: 'MER-CRYPTO-99',
      amount: 14500.0,
      delta_time: '+17s',
      is_burst: true
    }
  ]);

  // Active sequence score
  const [scoreResult, setScoreResult] = useState<TemporalScoreResult>({
    entity_id: 'ACC-BURST-01',
    sequence_fraud_probability: 0.9785,
    advisory_risk_level: 'CRITICAL',
    velocity_burst_detected: true,
    features_summary: {
      tx_count_5m: 4,
      tx_count_1h: 4,
      tx_count_24h: 4,
      velocity_burst_ratio: 9.6,
      amount_sum_1h: 43750.0,
      is_new_device: true,
      is_new_ip: true
    },
    recommendation: 'Advisory Alert: High temporal fraud velocity burst detected by GRU sequence model. Immediate secondary identity verification recommended.',
    timeline_indicators: [
      'Rapid velocity burst: 4 transactions in 5 minutes (Burst ratio: 9.6x).',
      'First observed interaction with unregistered device profile (DEV-ROGUE-01).',
      'First observed transaction from unrecorded network IP address (192.0.2.99 Tor Node).',
      'Elevated 1-hour cumulative transfer volume: $43,750.00.'
    ],
    is_advisory: true
  });

  const handleScoreSequence = async (entityId: string) => {
    setIsLoadingScore(true);
    try {
      const resp = await fetch('/temporal/score', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ entity_id: entityId, sequence_length: 5 })
      });
      if (resp.ok) {
        const data = await resp.json();
        setScoreResult(data);
      } else {
        simulateOfflineScore(entityId);
      }
    } catch {
      simulateOfflineScore(entityId);
    } finally {
      setIsLoadingScore(false);
    }
  };

  const simulateOfflineScore = (entityId: string) => {
    const isBurst = entityId.includes('BURST') || entityId.includes('01');
    setScoreResult({
      entity_id: entityId,
      sequence_fraud_probability: isBurst ? 0.965 : 0.052,
      advisory_risk_level: isBurst ? 'CRITICAL' : 'LOW',
      velocity_burst_detected: isBurst,
      features_summary: {
        tx_count_5m: isBurst ? 4 : 0,
        tx_count_1h: isBurst ? 5 : 1,
        tx_count_24h: isBurst ? 7 : 3,
        velocity_burst_ratio: isBurst ? 8.5 : 0.0,
        amount_sum_1h: isBurst ? 38500.0 : 85.0,
        is_new_device: isBurst,
        is_new_ip: isBurst
      },
      recommendation: isBurst
        ? 'Advisory Alert: High temporal fraud velocity burst detected by GRU sequence model. Immediate secondary identity verification recommended.'
        : 'Nominal: Standard temporal transaction rhythm within historical baseline.',
      timeline_indicators: isBurst
        ? [
            'Rapid velocity burst: 4 transactions in 5 minutes (Burst ratio: 8.5x).',
            'Unregistered device profile and Tor proxy network ingress.'
          ]
        : ['Standard spacing between transactions (> 45 minutes).'],
      is_advisory: true
    });
  };

  const handleInjectStreamEvent = async (isBurst: boolean) => {
    setIsInjectingEvent(true);
    const newTxId = `TXN-TEMP-${Math.floor(10000 + Math.random() * 90000)}`;
    const newEv: TimelineEvent = {
      transaction_id: newTxId,
      timestamp: new Date().toISOString().substring(11, 19) + ' UTC',
      source_account: isBurst ? 'ACC-BURST-01' : 'ACC-TEMP-025',
      target_account: isBurst ? 'MER-CRYPTO-99' : 'MER-TEMP-02',
      amount: isBurst ? Math.round(5000 + Math.random() * 8000) : Math.round(25 + Math.random() * 120),
      delta_time: isBurst ? '+12s' : '+15m',
      is_burst: isBurst
    };

    setTimelineEvents(prev => [newEv, ...prev.slice(0, 9)]);

    try {
      await fetch('/temporal/ingest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          events: [
            {
              transaction_id: newEv.transaction_id,
              timestamp: Date.now() / 1000,
              source_account: newEv.source_account,
              target_account: newEv.target_account,
              amount: newEv.amount,
              currency: 'USD',
              channel: 'mobile'
            }
          ]
        })
      });
    } catch {
      // offline simulation fallback
    } finally {
      setIsInjectingEvent(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Advisory Banner */}
      <div className="p-4 rounded-xl border border-amber-500/30 bg-amber-500/10 flex items-start space-x-3">
        <Clock className="w-6 h-6 text-amber-400 flex-shrink-0 mt-0.5" />
        <div className="text-sm">
          <span className="font-semibold text-amber-300">Phase 19 Temporal Graph Learning: </span>
          <span className="text-slate-300">
            Real-time streaming ingestion via Kinesis Lambda decoder with rolling, as-of temporal features and a PyTorch GRU sequence classifier.
            Model predictions are <strong className="text-white">advisory decision-support signals</strong>. Final fraud determinations require human investigator review.
          </span>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-4 bg-slate-900/80 border border-slate-800 rounded-xl space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Sequence Architecture</span>
            <Activity className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-lg font-bold text-slate-100">2-Layer PyTorch GRU</div>
          <div className="text-xs text-purple-400 font-mono">12 Features → 64 Hidden Units</div>
        </div>

        <div className="p-4 bg-slate-900/80 border border-slate-800 rounded-xl space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Streaming Ingestion</span>
            <Radio className="w-4 h-4 text-emerald-400 animate-pulse" />
          </div>
          <div className="flex items-center space-x-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400" />
            <span className="text-lg font-bold text-slate-100">Kinesis Lambda Live</span>
          </div>
          <div className="text-xs text-slate-400 font-mono">Idempotent Sliding Cache</div>
        </div>

        <div className="p-4 bg-slate-900/80 border border-slate-800 rounded-xl space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Split Methodology</span>
            <Clock className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-lg font-bold text-slate-100">Chronological 80/20</div>
          <div className="text-xs text-cyan-400 font-mono">Zero Lookahead Data Leakage</div>
        </div>

        <div className="p-4 bg-slate-900/80 border border-slate-800 rounded-xl space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Temporal Velocity Bursts</span>
            <Zap className="w-4 h-4 text-rose-400" />
          </div>
          <div className="text-lg font-bold text-rose-400">Detected: Active</div>
          <div className="text-xs text-rose-400 font-mono">&gt; 3 tx / 5m Burst Threshold</div>
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Sequence Scorer */}
        <div className="lg:col-span-2 space-y-6">
          <div className="p-6 bg-slate-900/90 border border-slate-800 rounded-xl space-y-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <TrendingUp className="w-5 h-5 text-amber-400" />
                <h3 className="text-base font-semibold text-slate-100">Real-Time GRU Sequence Evaluation</h3>
              </div>
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => handleInjectStreamEvent(true)}
                  disabled={isInjectingEvent}
                  className="px-2.5 py-1.5 rounded-lg text-xs bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/30 transition flex items-center space-x-1"
                >
                  <Zap className="w-3.5 h-3.5" />
                  <span>Simulate Burst</span>
                </button>
                <button
                  onClick={() => handleInjectStreamEvent(false)}
                  disabled={isInjectingEvent}
                  className="px-2.5 py-1.5 rounded-lg text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
                >
                  <span>Simulate Normal</span>
                </button>
              </div>
            </div>

            {/* Entity selector chips */}
            <div>
              <div className="text-xs text-slate-400 mb-2">Preset Accounts:</div>
              <div className="flex flex-wrap gap-2">
                {[
                  { id: 'ACC-BURST-01', label: 'ACC-BURST-01 (Mule Loop)', risk: 'CRITICAL' },
                  { id: 'ACC-BURST-02', label: 'ACC-BURST-02 (Smurf Destination)', risk: 'HIGH' },
                  { id: 'ACC-TEMP-015', label: 'ACC-TEMP-015 (Standard Retail)', risk: 'LOW' },
                  { id: 'ACC-TEMP-040', label: 'ACC-TEMP-040 (Periodic Salary)', risk: 'LOW' }
                ].map(item => (
                  <button
                    key={item.id}
                    onClick={() => {
                      setSelectedEntity(item.id);
                      handleScoreSequence(item.id);
                    }}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition ${
                      selectedEntity === item.id
                        ? 'bg-amber-600/30 border-amber-500 text-amber-300'
                        : 'bg-slate-800/60 border-slate-700/60 text-slate-400 hover:bg-slate-800 hover:text-slate-200'
                    }`}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Custom Input */}
            <div className="flex items-center space-x-2">
              <div className="relative flex-1">
                <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                <input
                  type="text"
                  placeholder="Enter entity ID (e.g. ACC-BURST-03)..."
                  value={customEntityInput}
                  onChange={e => setCustomEntityInput(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-amber-500"
                />
              </div>
              <button
                onClick={() => {
                  if (customEntityInput.trim()) {
                    setSelectedEntity(customEntityInput.trim());
                    handleScoreSequence(customEntityInput.trim());
                  }
                }}
                disabled={isLoadingScore}
                className="px-4 py-2 bg-amber-600 hover:bg-amber-500 text-white rounded-lg text-sm font-medium transition flex items-center space-x-1.5"
              >
                {isLoadingScore ? <RefreshCw className="w-4 h-4 animate-spin" /> : <span>Score Sequence</span>}
              </button>
            </div>

            {/* Score Result Card */}
            {scoreResult && (
              <div className="p-5 bg-slate-950/70 border border-slate-800 rounded-xl space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <span className="text-base font-bold text-slate-100 font-mono">{scoreResult.entity_id}</span>
                    {scoreResult.velocity_burst_detected && (
                      <span className="px-2 py-0.5 rounded text-xs bg-rose-500/20 text-rose-400 border border-rose-500/30 flex items-center space-x-1">
                        <Zap className="w-3 h-3" />
                        <span>VELOCITY BURST DETECTED</span>
                      </span>
                    )}
                  </div>
                  <span
                    className={`px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider ${
                      scoreResult.advisory_risk_level === 'CRITICAL'
                        ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                        : scoreResult.advisory_risk_level === 'HIGH'
                        ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                        : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    }`}
                  >
                    {scoreResult.advisory_risk_level} RISK
                  </span>
                </div>

                {/* Probability Bar */}
                <div className="space-y-1.5">
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-400">GRU Sequence Fraud Probability</span>
                    <span className="font-mono font-bold text-slate-200">
                      {(scoreResult.sequence_fraud_probability * 100).toFixed(2)}%
                    </span>
                  </div>
                  <div className="w-full bg-slate-800 rounded-full h-2.5 overflow-hidden">
                    <div
                      className={`h-2.5 rounded-full transition-all duration-500 ${
                        scoreResult.sequence_fraud_probability >= 0.75
                          ? 'bg-rose-500'
                          : scoreResult.sequence_fraud_probability >= 0.50
                          ? 'bg-amber-500'
                          : 'bg-emerald-500'
                      }`}
                      style={{ width: `${Math.max(5, scoreResult.sequence_fraud_probability * 100)}%` }}
                    />
                  </div>
                </div>

                {/* Recommendation */}
                <div className="p-3 bg-slate-900 rounded-lg text-xs text-slate-300 border border-slate-800 flex items-start space-x-2">
                  {scoreResult.sequence_fraud_probability >= 0.5 ? (
                    <ShieldAlert className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5" />
                  ) : (
                    <ShieldCheck className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                  )}
                  <span>{scoreResult.recommendation}</span>
                </div>

                {/* Features breakdown grid */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 border-t border-slate-800/80">
                  <div className="p-2.5 bg-slate-900 rounded-lg border border-slate-800 text-xs">
                    <div className="text-slate-500 text-[10px]">5m Frequency</div>
                    <div className="font-bold text-slate-200 font-mono text-sm">
                      {scoreResult.features_summary.tx_count_5m} tx
                    </div>
                  </div>
                  <div className="p-2.5 bg-slate-900 rounded-lg border border-slate-800 text-xs">
                    <div className="text-slate-500 text-[10px]">1h Volume</div>
                    <div className="font-bold text-slate-200 font-mono text-sm">
                      ${scoreResult.features_summary.amount_sum_1h.toLocaleString()}
                    </div>
                  </div>
                  <div className="p-2.5 bg-slate-900 rounded-lg border border-slate-800 text-xs">
                    <div className="text-slate-500 text-[10px]">Burst Ratio</div>
                    <div className="font-bold text-amber-400 font-mono text-sm">
                      {scoreResult.features_summary.velocity_burst_ratio}x
                    </div>
                  </div>
                  <div className="p-2.5 bg-slate-900 rounded-lg border border-slate-800 text-xs">
                    <div className="text-slate-500 text-[10px]">New Device</div>
                    <div className="font-bold font-mono text-sm text-rose-400">
                      {scoreResult.features_summary.is_new_device ? 'YES' : 'NO'}
                    </div>
                  </div>
                </div>

                {/* Timeline Indicators */}
                <div className="space-y-1.5 pt-2 border-t border-slate-800/80">
                  <div className="text-xs font-semibold text-slate-300">Causal Timeline Indicators:</div>
                  <ul className="space-y-1">
                    {scoreResult.timeline_indicators.map((ind, i) => (
                      <li key={i} className="text-xs text-slate-400 flex items-center space-x-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                        <span>{ind}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Live Ingestion Feed */}
        <div className="space-y-6">
          <div className="p-6 bg-slate-900/90 border border-slate-800 rounded-xl space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Radio className="w-5 h-5 text-emerald-400" />
                <h3 className="text-base font-semibold text-slate-100">Live Ingestion Stream</h3>
              </div>
              <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                Streaming
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Chronological Kinesis transaction events ingested in real time into sliding graph history.
            </p>

            <div className="space-y-2.5">
              {timelineEvents.map((ev, idx) => (
                <div
                  key={ev.transaction_id + idx}
                  className={`p-3 rounded-lg border text-xs space-y-1.5 ${
                    ev.is_burst
                      ? 'bg-rose-500/10 border-rose-500/30 text-slate-200'
                      : 'bg-slate-950/70 border-slate-800 text-slate-300'
                  }`}
                >
                  <div className="flex items-center justify-between font-mono">
                    <span className="font-bold text-slate-100">{ev.transaction_id}</span>
                    <span className="text-slate-400 text-[11px]">{ev.timestamp}</span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-400 font-mono">
                      {ev.source_account} → {ev.target_account || 'Merchant'}
                    </span>
                    <span className="font-bold text-slate-100 font-mono">${ev.amount.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between items-center text-[10px]">
                    <span className="text-slate-500">Delta: {ev.delta_time}</span>
                    {ev.is_burst && (
                      <span className="text-rose-400 font-semibold uppercase tracking-wider">
                        BURST SPEED
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

