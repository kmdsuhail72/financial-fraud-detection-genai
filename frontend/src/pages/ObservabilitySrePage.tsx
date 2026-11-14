import React, { useState, useEffect } from 'react';
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Compass,
  Cpu,
  Database,
  ExternalLink,
  Eye,
  FileText,
  Layers,
  LineChart,
  RefreshCw,
  Server,
  Shield,
  ShieldAlert,
  Sliders,
  Terminal,
  Zap,
} from 'lucide-react';
import axios from 'axios';

interface SLOStatus {
  slo_id: string;
  name: string;
  service: string;
  target_percentage: number;
  current_percentage: number;
  status: string;
  error_budget_total_percentage: number;
  error_budget_consumed_percentage: number;
  error_budget_remaining_percentage: number;
  burn_rate_1h: number;
  burn_rate_6h: number;
  total_requests: number;
  bad_requests: number;
  p50_latency_ms: number;
  p90_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
}

interface SpanRecord {
  trace_id: string;
  span_id: string;
  parent_span_id?: string;
  name: string;
  service_name: string;
  kind: string;
  duration_ms?: number;
  status_code: string;
  status_message?: string;
  attributes: Record<string, any>;
}

interface TraceRecord {
  trace_id: string;
  root_span_name: string;
  service_name: string;
  total_spans: number;
  duration_ms: number;
  has_errors: boolean;
  spans: SpanRecord[];
}

interface ActiveAlert {
  id: string;
  alert_name: string;
  severity: string;
  state: string;
  service: string;
  summary: string;
  started_at: string;
  runbook_url?: string;
}

interface RunbookItem {
  id: string;
  title: string;
  severity: string;
  trigger_condition: string;
  immediate_actions: string[];
  investigation_steps: string[];
  mitigation_steps: string[];
  rollback_command?: string;
  escalation_contacts: string[];
}

export const ObservabilitySrePage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'slo' | 'traces' | 'metrics' | 'alerts' | 'runbooks'>('slo');
  const [slos, setSlos] = useState<SLOStatus[]>([]);
  const [traces, setTraces] = useState<TraceRecord[]>([]);
  const [selectedTrace, setSelectedTrace] = useState<TraceRecord | null>(null);
  const [activeAlerts, setActiveAlerts] = useState<ActiveAlert[]>([]);
  const [runbooks, setRunbooks] = useState<RunbookItem[]>([]);
  const [metricsText, setMetricsText] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  const [simulatingAlert, setSimulatingAlert] = useState<boolean>(false);
  const [alertFilter, setAlertFilter] = useState<'normal' | '5xx_breach' | 'latency_breach'>('normal');

  const fetchData = async () => {
    setLoading(true);
    try {
      const [sloRes, traceRes, alertRes, rbRes, metricsRes] = await Promise.all([
        axios.get('/observability/slo').catch(() => ({ data: [] })),
        axios.get('/observability/traces').catch(() => ({ data: [] })),
        axios.get('/observability/alerts').catch(() => ({ data: [] })),
        axios.get('/observability/runbooks').catch(() => ({ data: [] })),
        axios.get('/observability/metrics').catch(() => ({ data: '# Prometheus exporter ready' })),
      ]);

      if (sloRes.data && sloRes.data.length > 0) {
        setSlos(sloRes.data);
      } else {
        // Fallback demo SLOs
        setSlos([
          {
            slo_id: 'slo-avail-core',
            name: 'FinGuard Core API Availability',
            service: 'finguard-gateway',
            target_percentage: 99.9,
            current_percentage: 99.97,
            status: 'MET',
            error_budget_total_percentage: 0.1,
            error_budget_consumed_percentage: 28.0,
            error_budget_remaining_percentage: 72.0,
            burn_rate_1h: 0.35,
            burn_rate_6h: 0.33,
            total_requests: 150000,
            bad_requests: 42,
            p50_latency_ms: 18.4,
            p90_latency_ms: 45.1,
            p95_latency_ms: 62.8,
            p99_latency_ms: 95.3,
          },
          {
            slo_id: 'slo-lat-scoring',
            name: 'Fraud Scoring Latency p95',
            service: 'fraud-scoring-service',
            target_percentage: 99.5,
            current_percentage: 99.85,
            status: 'MET',
            error_budget_total_percentage: 0.5,
            error_budget_consumed_percentage: 30.0,
            error_budget_remaining_percentage: 70.0,
            burn_rate_1h: 0.42,
            burn_rate_6h: 0.39,
            total_requests: 120000,
            bad_requests: 180,
            p50_latency_ms: 32.5,
            p90_latency_ms: 78.2,
            p95_latency_ms: 98.4,
            p99_latency_ms: 142.1,
          },
        ]);
      }

      if (traceRes.data && traceRes.data.length > 0) {
        setTraces(traceRes.data);
        setSelectedTrace(traceRes.data[0]);
      }
      setActiveAlerts(alertRes.data || []);
      setRunbooks(rbRes.data || []);
      setMetricsText(typeof metricsRes.data === 'string' ? metricsRes.data : JSON.stringify(metricsRes.data, null, 2));
    } catch (e) {
      console.error('Failed to load observability data', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleSimulateAlertCondition = async (type: 'normal' | '5xx_breach' | 'latency_breach') => {
    setSimulatingAlert(true);
    setAlertFilter(type);
    try {
      let payload = {
        error_rate_5xx: 0.002,
        p95_latency_ms: 65.0,
        services_down: null as string[] | null,
        burn_rate_1h: 0.42,
      };

      if (type === '5xx_breach') {
        payload.error_rate_5xx = 0.025; // 2.5%
        payload.burn_rate_1h = 16.5;
      } else if (type === 'latency_breach') {
        payload.p95_latency_ms = 245.0; // 245ms
      }

      const res = await axios.post('/observability/alerts/evaluate', payload);
      setActiveAlerts(res.data);
    } catch (err) {
      console.error('Simulation error:', err);
    } finally {
      setSimulatingAlert(false);
    }
  };

  const coreSlo = slos.find((s) => s.slo_id === 'slo-avail-core') || slos[0];
  const scoringSlo = slos.find((s) => s.slo_id === 'slo-lat-scoring') || slos[1];

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-gray-800 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-cyan-950/60 border border-cyan-800 rounded-xl text-cyan-400">
              <Activity className="w-6 h-6 animate-pulse" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">Enterprise Observability & SRE Console</h1>
              <p className="text-sm text-gray-400">
                OpenTelemetry Tracing · Prometheus Metrics · Grafana Dashboards · AWS CloudWatch Logs & Alarms (Mumbai ap-south-1)
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

      {/* Golden Signals & SLO Highlights */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Availability Card */}
        <div className="bg-gray-900/80 border border-gray-800 rounded-xl p-4">
          <div className="flex items-center justify-between text-gray-400 text-xs font-semibold uppercase tracking-wider mb-2">
            <span>Availability SLO (30d)</span>
            <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-950/60 border border-emerald-800 text-emerald-400">
              Target: {coreSlo?.target_percentage ?? 99.9}%
            </span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold text-emerald-400">
              {coreSlo?.current_percentage?.toFixed(2) ?? '99.97'}%
            </span>
            <span className="text-xs text-gray-400">current</span>
          </div>
          <div className="mt-3 flex items-center justify-between text-xs text-gray-400 border-t border-gray-800/60 pt-2">
            <span>Status: <strong className="text-emerald-400">{coreSlo?.status ?? 'MET'}</strong></span>
            <span>Bad req: {coreSlo?.bad_requests ?? 42} / {coreSlo?.total_requests?.toLocaleString() ?? '150,000'}</span>
          </div>
        </div>

        {/* p95 Latency Card */}
        <div className="bg-gray-900/80 border border-gray-800 rounded-xl p-4">
          <div className="flex items-center justify-between text-gray-400 text-xs font-semibold uppercase tracking-wider mb-2">
            <span>Fraud Scoring Latency</span>
            <span className="px-2 py-0.5 rounded text-[10px] bg-cyan-950/60 border border-cyan-800 text-cyan-400">
              SLO &lt; 200ms
            </span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold text-cyan-400">
              {scoringSlo?.p95_latency_ms?.toFixed(1) ?? '62.8'} <span className="text-sm font-normal text-gray-300">ms</span>
            </span>
            <span className="text-xs text-gray-400">p95</span>
          </div>
          <div className="mt-3 flex items-center justify-between text-xs text-gray-400 border-t border-gray-800/60 pt-2">
            <span>p50: {scoringSlo?.p50_latency_ms ?? 18.4}ms</span>
            <span>p99: {scoringSlo?.p99_latency_ms ?? 95.3}ms</span>
          </div>
        </div>

        {/* Error Budget Card */}
        <div className="bg-gray-900/80 border border-gray-800 rounded-xl p-4">
          <div className="flex items-center justify-between text-gray-400 text-xs font-semibold uppercase tracking-wider mb-2">
            <span>Error Budget Remaining</span>
            <span className="text-xs text-gray-400">30-day</span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold text-emerald-400">
              {coreSlo?.error_budget_remaining_percentage?.toFixed(1) ?? '72.0'}%
            </span>
            <span className="text-xs text-gray-400">budget</span>
          </div>
          <div className="mt-3 flex items-center justify-between text-xs text-gray-400 border-t border-gray-800/60 pt-2">
            <span>1h Burn Rate: <strong className="text-gray-200">{coreSlo?.burn_rate_1h ?? 0.35}x</strong></span>
            <span>Consumed: {coreSlo?.error_budget_consumed_percentage ?? 28.0}%</span>
          </div>
        </div>

        {/* Active Alerts Card */}
        <div className="bg-gray-900/80 border border-gray-800 rounded-xl p-4">
          <div className="flex items-center justify-between text-gray-400 text-xs font-semibold uppercase tracking-wider mb-2">
            <span>Active SRE Alerts</span>
            <span className="text-xs text-gray-400">Live</span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className={`text-3xl font-bold ${activeAlerts.length > 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
              {activeAlerts.length}
            </span>
            <span className="text-xs text-gray-400">firing</span>
          </div>
          <div className="mt-3 flex items-center justify-between text-xs text-gray-400 border-t border-gray-800/60 pt-2">
            <span>CloudWatch Alarms: <strong className="text-gray-200">2 OK</strong></span>
            <span>Region: <strong className="text-gray-300">ap-south-1</strong></span>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex border-b border-gray-800 gap-6">
        {[
          { id: 'slo', label: 'SLO & Error Budgets', icon: Sliders },
          { id: 'traces', label: 'Distributed Tracing (OTel)', icon: Compass },
          { id: 'metrics', label: 'Prometheus Metrics', icon: LineChart },
          { id: 'alerts', label: `Alerts (${activeAlerts.length})`, icon: AlertTriangle },
          { id: 'runbooks', label: 'SRE Runbooks & Rollback', icon: FileText },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 pb-3 px-1 text-sm font-medium border-b-2 transition ${
                isActive
                  ? 'border-cyan-400 text-cyan-400'
                  : 'border-transparent text-gray-400 hover:text-gray-200 hover:border-gray-700'
              }`}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab 1: SLO & Error Budgets */}
      {activeTab === 'slo' && (
        <div className="space-y-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <h3 className="text-lg font-semibold text-white mb-2">Service Level Objectives (SLOs)</h3>
            <p className="text-sm text-gray-400 mb-6">
              Track 30-day availability targets, latency thresholds, error-budget consumption, and multi-window burn rates.
            </p>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-gray-300">
                <thead className="text-xs uppercase bg-gray-800/50 text-gray-400 border-b border-gray-800">
                  <tr>
                    <th className="px-4 py-3">SLO Name</th>
                    <th className="px-4 py-3">Service</th>
                    <th className="px-4 py-3">Target</th>
                    <th className="px-4 py-3">Current</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Budget Remaining</th>
                    <th className="px-4 py-3">1h Burn</th>
                    <th className="px-4 py-3">p95 Latency</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800">
                  {slos.map((s) => (
                    <tr key={s.slo_id} className="hover:bg-gray-800/30">
                      <td className="px-4 py-3 font-medium text-white">{s.name}</td>
                      <td className="px-4 py-3 font-mono text-xs text-gray-400">{s.service}</td>
                      <td className="px-4 py-3">{s.target_percentage}%</td>
                      <td className="px-4 py-3 font-bold text-emerald-400">{s.current_percentage}%</td>
                      <td className="px-4 py-3">
                        <span
                          className={`px-2 py-0.5 rounded text-xs font-semibold ${
                            s.status === 'MET'
                              ? 'bg-emerald-950/60 border border-emerald-800 text-emerald-400'
                              : 'bg-rose-950/60 border border-rose-800 text-rose-400'
                          }`}
                        >
                          {s.status}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="w-32 bg-gray-800 rounded-full h-2 mr-2 inline-block">
                          <div
                            className={`h-2 rounded-full ${
                              s.error_budget_remaining_percentage > 50
                                ? 'bg-emerald-500'
                                : s.error_budget_remaining_percentage > 25
                                ? 'bg-amber-500'
                                : 'bg-rose-500'
                            }`}
                            style={{ width: `${Math.min(s.error_budget_remaining_percentage, 100)}%` }}
                          />
                        </div>
                        <span className="text-xs">{s.error_budget_remaining_percentage}%</span>
                      </td>
                      <td className="px-4 py-3 font-mono text-xs">{s.burn_rate_1h}x</td>
                      <td className="px-4 py-3 font-mono text-xs">{s.p95_latency_ms} ms</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Distributed Tracing */}
      {activeTab === 'traces' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Traces List */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 lg:col-span-1 space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-gray-800">
              <h3 className="font-semibold text-white text-sm">Recent Distributed Traces</h3>
              <span className="text-xs text-gray-400">{traces.length} traces</span>
            </div>

            <div className="space-y-2 max-h-[550px] overflow-y-auto">
              {traces.map((tr) => (
                <div
                  key={tr.trace_id}
                  onClick={() => setSelectedTrace(tr)}
                  className={`p-3 rounded-lg border cursor-pointer transition ${
                    selectedTrace?.trace_id === tr.trace_id
                      ? 'bg-cyan-950/40 border-cyan-700'
                      : 'bg-gray-800/40 border-gray-800 hover:bg-gray-800'
                  }`}
                >
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="font-mono text-cyan-400 font-semibold">{tr.root_span_name}</span>
                    <span className={`px-1.5 py-0.5 rounded text-[10px] ${tr.has_errors ? 'bg-rose-950 text-rose-400' : 'bg-emerald-950 text-emerald-400'}`}>
                      {tr.has_errors ? 'ERROR' : 'OK'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-xs text-gray-400">
                    <span className="font-mono truncate max-w-[120px]">{tr.trace_id}</span>
                    <span>{tr.duration_ms} ms · {tr.total_spans} spans</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Trace Spans Tree */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 lg:col-span-2 space-y-4">
            {selectedTrace ? (
              <div>
                <div className="flex items-center justify-between border-b border-gray-800 pb-3 mb-4">
                  <div>
                    <h3 className="text-base font-bold text-white flex items-center gap-2">
                      <Compass className="w-5 h-5 text-cyan-400" />
                      Trace: <span className="font-mono text-cyan-300">{selectedTrace.trace_id}</span>
                    </h3>
                    <p className="text-xs text-gray-400 mt-0.5">
                      Service: <strong className="text-gray-200">{selectedTrace.service_name}</strong> · Total Duration: <strong className="text-gray-200">{selectedTrace.duration_ms} ms</strong> · Spans: {selectedTrace.total_spans}
                    </p>
                  </div>
                </div>

                <div className="space-y-3">
                  <h4 className="text-xs uppercase text-gray-400 font-semibold">Span Hierarchy & Execution Timeline</h4>
                  <div className="space-y-2">
                    {selectedTrace.spans.map((sp, idx) => (
                      <div
                        key={sp.span_id}
                        className={`p-3 rounded-lg border text-xs ${
                          sp.parent_span_id ? 'ml-6 bg-gray-800/30 border-gray-800' : 'bg-gray-800/80 border-cyan-900'
                        }`}
                      >
                        <div className="flex items-center justify-between mb-1.5">
                          <div className="flex items-center gap-2 font-mono">
                            <span className="font-semibold text-white">{sp.name}</span>
                            <span className="px-1.5 py-0.5 rounded bg-gray-700 text-gray-300 text-[10px]">{sp.service_name}</span>
                            <span className="px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-400 text-[10px]">{sp.kind}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-gray-300 font-bold">{sp.duration_ms ?? 0} ms</span>
                            <span className={`px-1.5 py-0.5 rounded text-[10px] ${sp.status_code === 'ERROR' ? 'bg-rose-950 text-rose-400' : 'bg-emerald-950 text-emerald-400'}`}>
                              {sp.status_code}
                            </span>
                          </div>
                        </div>

                        {/* Visual timeline bar */}
                        <div className="w-full bg-gray-800 h-1.5 rounded-full overflow-hidden my-2">
                          <div
                            className="bg-cyan-500 h-full rounded-full"
                            style={{
                              width: `${Math.max(10, Math.min(100, ((sp.duration_ms ?? 1) / Math.max(selectedTrace.duration_ms, 1)) * 100))}%`,
                            }}
                          />
                        </div>

                        {/* Span Attributes */}
                        {Object.keys(sp.attributes).length > 0 && (
                          <div className="bg-gray-950 p-2 rounded text-[11px] font-mono text-gray-400 mt-2">
                            {Object.entries(sp.attributes).map(([k, v]) => (
                              <div key={k}>
                                <span className="text-cyan-400">{k}:</span> {JSON.stringify(v)}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-16 text-gray-500">Select a trace to view span breakdown</div>
            )}
          </div>
        </div>
      )}

      {/* Tab 3: Prometheus Metrics */}
      {activeTab === 'metrics' && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-white">Prometheus Exposition Metrics</h3>
              <p className="text-sm text-gray-400">Scrape endpoint format exposed directly at <code className="text-cyan-400 font-mono">/metrics</code></p>
            </div>
            <a
              href="/metrics"
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-xs font-medium text-gray-200 rounded-lg"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              Open /metrics
            </a>
          </div>

          <pre className="bg-gray-950 p-4 rounded-xl border border-gray-800 text-xs font-mono text-gray-300 max-h-[500px] overflow-y-auto whitespace-pre-wrap">
            {metricsText}
          </pre>
        </div>
      )}

      {/* Tab 4: Active Alerts */}
      {activeTab === 'alerts' && (
        <div className="space-y-4">
          {/* Alert Simulation Bar */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h4 className="text-sm font-semibold text-white">SRE Alert Rule Evaluation Simulator</h4>
              <p className="text-xs text-gray-400">Simulate production failure scenarios to verify automated alerting and runbook escalation.</p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => handleSimulateAlertCondition('normal')}
                disabled={simulatingAlert}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                  alertFilter === 'normal' ? 'bg-emerald-800 text-white' : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                }`}
              >
                Normal (All Green)
              </button>
              <button
                onClick={() => handleSimulateAlertCondition('5xx_breach')}
                disabled={simulatingAlert}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                  alertFilter === '5xx_breach' ? 'bg-rose-800 text-white' : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                }`}
              >
                Inject 5xx Error Spike (&gt;1%)
              </button>
              <button
                onClick={() => handleSimulateAlertCondition('latency_breach')}
                disabled={simulatingAlert}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                  alertFilter === 'latency_breach' ? 'bg-amber-800 text-white' : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                }`}
              >
                Inject p95 Latency (&gt;200ms)
              </button>
            </div>
          </div>

          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <h3 className="text-lg font-semibold text-white mb-4">Firing Incidents & Alerts</h3>
            {activeAlerts.length === 0 ? (
              <div className="text-center py-12 border border-dashed border-gray-800 rounded-xl">
                <CheckCircle2 className="w-10 h-10 text-emerald-400 mx-auto mb-2" />
                <h4 className="text-base font-semibold text-white">All Golden Signals Nominal</h4>
                <p className="text-xs text-gray-400 mt-1">No firing alerts or error-budget exhaustion detected across FinGuard services.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {activeAlerts.map((alt) => (
                  <div
                    key={alt.id}
                    className="p-4 rounded-xl border border-rose-900/60 bg-rose-950/20 flex flex-col md:flex-row md:items-center justify-between gap-4"
                  >
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="px-2 py-0.5 rounded text-xs font-bold bg-rose-950 text-rose-400 border border-rose-800">
                          {alt.severity}
                        </span>
                        <h4 className="font-semibold text-white text-sm">{alt.alert_name}</h4>
                        <span className="text-xs text-gray-400">({alt.service})</span>
                      </div>
                      <p className="text-xs text-rose-300">{alt.summary}</p>
                      <p className="text-[11px] text-gray-500 mt-1">Started: {alt.started_at}</p>
                    </div>

                    {alt.runbook_url && (
                      <button
                        onClick={() => setActiveTab('runbooks')}
                        className="px-3.5 py-1.5 bg-rose-900 hover:bg-rose-800 text-rose-100 rounded-lg text-xs font-medium flex items-center gap-1.5 transition whitespace-nowrap"
                      >
                        <FileText className="w-3.5 h-3.5" />
                        View Triage Runbook
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 5: SRE Runbooks */}
      {activeTab === 'runbooks' && (
        <div className="space-y-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <h3 className="text-lg font-semibold text-white mb-2">SRE Incident Triage & Rollback Runbooks</h3>
            <p className="text-sm text-gray-400 mb-6">
              Standard Operating Procedures (SOPs) for rapid incident triage, rollback execution, and on-call escalation.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {runbooks.map((rb) => (
                <div key={rb.id} className="p-4 bg-gray-950 border border-gray-800 rounded-xl space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="font-semibold text-white text-sm">{rb.title}</h4>
                    <span className="px-2 py-0.5 rounded text-xs font-bold bg-rose-950 text-rose-400 border border-rose-800">
                      {rb.severity}
                    </span>
                  </div>
                  <p className="text-xs text-cyan-400">Trigger: {rb.trigger_condition}</p>

                  <div>
                    <h5 className="text-[11px] uppercase text-gray-400 font-semibold mb-1">Immediate Actions:</h5>
                    <ul className="list-disc list-inside text-xs text-gray-300 space-y-1">
                      {rb.immediate_actions.map((act, i) => (
                        <li key={i}>{act}</li>
                      ))}
                    </ul>
                  </div>

                  {rb.rollback_command && (
                    <div className="pt-2 border-t border-gray-800">
                      <h5 className="text-[11px] uppercase text-amber-400 font-semibold mb-1">Automated Rollback Command:</h5>
                      <div className="bg-gray-900 p-2 rounded text-xs font-mono text-emerald-400 flex items-center justify-between">
                        <code>{rb.rollback_command}</code>
                      </div>
                    </div>
                  )}

                  <div className="pt-2 text-[11px] text-gray-500">
                    Escalation: {rb.escalation_contacts.join(' · ')}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ObservabilitySrePage;
