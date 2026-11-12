import React from 'react';
import {
  ShieldAlert,
  AlertCircle,
  Clock,
  CheckCircle,
  TrendingUp,
  Activity,
  ArrowUpRight,
  CreditCard,
  Smartphone,
  Globe,
  Radio
} from 'lucide-react';
import { InvestigationCase, DashboardMetrics } from '../types/case';
import { KpiCard } from '../components/KpiCard';
import { RiskBadge } from '../components/RiskBadge';
import { StatusBadge } from '../components/StatusBadge';

interface DashboardPageProps {
  cases: InvestigationCase[];
  metrics: DashboardMetrics;
  onSelectCase: (caseId: string) => void;
  onViewAllQueue: () => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({
  cases,
  metrics,
  onSelectCase,
  onViewAllQueue
}) => {
  const highPriorityCases = cases
    .filter((c) => c.status !== 'RESOLVED' && c.status !== 'CLOSED')
    .sort((a, b) => b.risk_score - a.risk_score)
    .slice(0, 5);

  const formatCurrency = (amt: number, currency: string = 'INR') => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: currency || 'INR',
      maximumFractionDigits: 0
    }).format(amt);
  };

  return (
    <div className="space-y-6">
      {/* Top Welcome / Live Banner */}
      <div className="bg-gradient-to-r from-sky-950/60 via-slate-900 to-indigo-950/40 border border-slate-800 rounded-xl p-6 relative overflow-hidden">
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2 text-sky-400 font-mono text-xs font-semibold mb-1">
              <span className="w-2 h-2 rounded-full bg-sky-400 animate-ping" />
              <span>KINESIS REAL-TIME STREAM ACTIVE</span>
            </div>
            <h2 className="text-xl md:text-2xl font-bold text-white tracking-tight">
              FinGuard AI Fraud Operations Center
            </h2>
            <p className="text-sm text-slate-300 mt-1 max-w-2xl">
              Multi-layered fraud defense powered by SageMaker ML inference (XGBoost + Isolation Forest) and Amazon Bedrock GenAI for high-velocity investigation synthesis.
            </p>
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={onViewAllQueue}
              className="px-4 py-2 bg-sky-600 hover:bg-sky-500 text-white rounded-lg text-xs font-semibold tracking-wide flex items-center space-x-2 transition-all shadow-md shadow-sky-600/30"
            >
              <span>Open Queue ({cases.length})</span>
              <ArrowUpRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* 4 Primary KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          title="Total Active Cases"
          value={metrics.total_cases}
          icon={<Activity className="w-5 h-5" />}
          subtitle="All flagged transactions"
          variant="default"
        />
        <KpiCard
          title="Critical & High Risk"
          value={metrics.critical_cases + metrics.high_risk_cases}
          icon={<AlertCircle className="w-5 h-5" />}
          subtitle="Immediate analyst action needed"
          variant="critical"
        />
        <KpiCard
          title="Under Active Review"
          value={metrics.in_review_cases}
          icon={<Clock className="w-5 h-5" />}
          subtitle="Claimed by Tier-1/2 analysts"
          variant="warning"
        />
        <KpiCard
          title="Resolved Today"
          value={metrics.resolved_today}
          icon={<CheckCircle className="w-5 h-5" />}
          subtitle="Human-verified verdicts"
          variant="success"
        />
      </div>

      {/* Middle Grid: Risk Distribution + Channel Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Risk Distribution Breakdown */}
        <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white tracking-tight flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-sky-400" />
              Risk Severity Breakdown
            </h3>
            <span className="text-[11px] font-mono text-slate-400">Total: {metrics.total_cases}</span>
          </div>

          <div className="space-y-3">
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-rose-400 font-medium">Critical Risk (Score &gt; 0.85)</span>
                <span className="font-mono text-slate-300 font-semibold">{metrics.critical_cases}</span>
              </div>
              <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-rose-500 h-2 rounded-full transition-all duration-500"
                  style={{
                    width: `${metrics.total_cases ? (metrics.critical_cases / metrics.total_cases) * 100 : 0}%`
                  }}
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-orange-400 font-medium">High Risk (0.70 &ndash; 0.85)</span>
                <span className="font-mono text-slate-300 font-semibold">{metrics.high_risk_cases}</span>
              </div>
              <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-orange-500 h-2 rounded-full transition-all duration-500"
                  style={{
                    width: `${metrics.total_cases ? (metrics.high_risk_cases / metrics.total_cases) * 100 : 0}%`
                  }}
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-amber-400 font-medium">Review Tier (0.50 &ndash; 0.70)</span>
                <span className="font-mono text-slate-300 font-semibold">
                  {Math.max(0, metrics.total_cases - metrics.critical_cases - metrics.high_risk_cases)}
                </span>
              </div>
              <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-amber-400 h-2 rounded-full transition-all duration-500"
                  style={{
                    width: `${metrics.total_cases ? ((metrics.total_cases - metrics.critical_cases - metrics.high_risk_cases) / metrics.total_cases) * 100 : 0}%`
                  }}
                />
              </div>
            </div>
          </div>

          <div className="pt-3 border-t border-slate-800 text-xs text-slate-400 flex items-center justify-between">
            <span>Avg Investigation Time:</span>
            <span className="font-mono font-semibold text-slate-200">
              {metrics.avg_resolution_time_minutes} mins
            </span>
          </div>
        </div>

        {/* Banking Channels Telemetry */}
        <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white tracking-tight flex items-center gap-2">
              <Radio className="w-4 h-4 text-indigo-400" />
              Channel Attack Surface
            </h3>
            <span className="text-[11px] font-mono text-slate-400">Past 24h</span>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800 flex items-center space-x-3">
              <div className="p-2 rounded bg-sky-500/10 text-sky-400 border border-sky-500/20">
                <Smartphone className="w-4 h-4" />
              </div>
              <div>
                <div className="text-[11px] text-slate-400">UPI / P2P</div>
                <div className="text-sm font-bold text-white font-mono">46%</div>
              </div>
            </div>

            <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800 flex items-center space-x-3">
              <div className="p-2 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                <CreditCard className="w-4 h-4" />
              </div>
              <div>
                <div className="text-[11px] text-slate-400">Card POS/E-Com</div>
                <div className="text-sm font-bold text-white font-mono">34%</div>
              </div>
            </div>

            <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800 flex items-center space-x-3">
              <div className="p-2 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <Globe className="w-4 h-4" />
              </div>
              <div>
                <div className="text-[11px] text-slate-400">NetBanking</div>
                <div className="text-sm font-bold text-white font-mono">15%</div>
              </div>
            </div>

            <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800 flex items-center space-x-3">
              <div className="p-2 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                <Activity className="w-4 h-4" />
              </div>
              <div>
                <div className="text-[11px] text-slate-400">ATM Cash</div>
                <div className="text-sm font-bold text-white font-mono">5%</div>
              </div>
            </div>
          </div>

          <div className="text-[11px] text-slate-400 leading-relaxed font-sans">
            Spike detected in rapid succession UPI transfers from newly provisioned mobile devices.
          </div>
        </div>

        {/* GenAI Bedrock Copilot Status */}
        <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white tracking-tight flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-emerald-400" />
              Investigation Guardrails
            </h3>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              Compliant
            </span>
          </div>

          <div className="space-y-2 text-xs text-slate-300">
            <div className="flex items-start gap-2 p-2 bg-slate-950/50 rounded border border-slate-800/80">
              <CheckCircle className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold text-slate-200">Zero Autonomous Action:</span> All account freeze and card blocking actions require dual analyst sign-off.
              </div>
            </div>
            <div className="flex items-start gap-2 p-2 bg-slate-950/50 rounded border border-slate-800/80">
              <CheckCircle className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold text-slate-200">Strict Evidence Grounding:</span> Bedrock prompt strictly denies external hallucination beyond transaction telemetry.
              </div>
            </div>
            <div className="flex items-start gap-2 p-2 bg-slate-950/50 rounded border border-slate-800/80">
              <CheckCircle className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold text-slate-200">Immutable Audit Trail:</span> DynamoDB records all analyst notes and state transitions with TTL.
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Priority Investigation Queue Table */}
      <div className="bg-slate-900/70 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-white tracking-tight">
              High Priority Investigation Cases
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Flagged by SageMaker endpoint &bull; Sorted by composite risk score
            </p>
          </div>
          <button
            onClick={onViewAllQueue}
            className="text-xs text-sky-400 hover:text-sky-300 font-semibold font-mono flex items-center space-x-1"
          >
            <span>View All Queue &rarr;</span>
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/60 text-slate-400 uppercase font-mono text-[10px] tracking-wider border-b border-slate-800">
              <tr>
                <th className="py-3 px-4">Case ID</th>
                <th className="py-3 px-4">Customer</th>
                <th className="py-3 px-4">Channel</th>
                <th className="py-3 px-4">Amount</th>
                <th className="py-3 px-4">Risk Level</th>
                <th className="py-3 px-4">Fraud Prob</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 font-sans">
              {highPriorityCases.map((c) => (
                <tr
                  key={c.case_id}
                  onClick={() => onSelectCase(c.case_id)}
                  className="hover:bg-slate-800/40 cursor-pointer transition-colors"
                >
                  <td className="py-3 px-4 font-mono font-semibold text-sky-400">
                    {c.case_id}
                  </td>
                  <td className="py-3 px-4">
                    <div className="text-slate-200 font-medium">{c.customer_id}</div>
                    <div className="text-[10px] text-slate-500 font-mono">{c.account_id}</div>
                  </td>
                  <td className="py-3 px-4">
                    <span className="font-mono text-slate-300 uppercase">{c.channel}</span>
                  </td>
                  <td className="py-3 px-4 font-mono font-semibold text-slate-200">
                    {formatCurrency(c.amount, c.currency)}
                  </td>
                  <td className="py-3 px-4">
                    <RiskBadge level={c.risk_level} score={c.risk_score} />
                  </td>
                  <td className="py-3 px-4 font-mono text-slate-300">
                    {Math.round((c.fraud_probability ?? 0.5) * 100)}%
                  </td>
                  <td className="py-3 px-4">
                    <StatusBadge status={c.status} />
                  </td>
                  <td className="py-3 px-4 text-right">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectCase(c.case_id);
                      }}
                      className="px-2.5 py-1 rounded bg-sky-500/10 hover:bg-sky-500/20 text-sky-400 font-medium text-xs transition-colors"
                    >
                      Investigate
                    </button>
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

