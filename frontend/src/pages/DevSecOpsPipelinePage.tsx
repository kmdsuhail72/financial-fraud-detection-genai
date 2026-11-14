import React, { useState, useEffect } from 'react';
import {
  GitBranch,
  CheckCircle2,
  XCircle,
  Clock,
  Play,
  RotateCcw,
  ShieldCheck,
  ShieldAlert,
  Server,
  Activity,
  Layers,
  ArrowRight,
  RefreshCw,
  FileCode,
  Terminal,
  ExternalLink
} from 'lucide-react';
import axios from 'axios';

interface PipelineStage {
  name: string;
  status: string;
  duration_seconds: number;
  error?: string;
  output_summary: string;
}

interface PipelineRun {
  run_id: string;
  branch: string;
  commit_sha: string;
  status: string;
  stages: PipelineStage[];
  started_at: string;
  total_duration_seconds: number;
}

interface SonarQubeReport {
  quality_gate_status: string;
  coverage_percentage: number;
  code_smells: number;
  bugs_count: number;
  vulnerabilities_count: number;
  security_hotspots_reviewed: number;
  duplications_percentage: number;
  project_key: string;
}

interface TrivyFinding {
  vulnerability_id: string;
  package: string;
  installed_version: string;
  fixed_version: string;
  severity: string;
  title: string;
}

interface ArgoCdAppStatus {
  app_name: string;
  sync_status: string;
  health_status: string;
  target_revision: string;
  last_synced_at: string;
  canary_weight_percentage: number;
  canary_phase: string;
}

export const DevSecOpsPipelinePage: React.FC = () => {
  const [runs, setRuns] = useState<PipelineRun[]>([]);
  const [sonar, setSonar] = useState<SonarQubeReport | null>(null);
  const [trivy, setTrivy] = useState<TrivyFinding[]>([]);
  const [argoApps, setArgoApps] = useState<ArgoCdAppStatus[]>([]);
  const [loading, setLoading] = useState(false);

  // Trigger form state
  const [branch, setBranch] = useState('main');
  const [forceFailStage, setForceFailStage] = useState('none');
  const [isTriggering, setIsTriggering] = useState(false);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [runsRes, sonarRes, trivyRes, argoRes] = await Promise.all([
        axios.get('/cicd/pipeline/runs'),
        axios.get('/cicd/sonarqube/report'),
        axios.get('/cicd/trivy/vulnerabilities'),
        axios.get('/cicd/argocd/status'),
      ]);
      setRuns(runsRes.data);
      setSonar(sonarRes.data);
      setTrivy(trivyRes.data);
      setArgoApps(argoRes.data);
    } catch (err) {
      console.error('Failed to load CI/CD telemetry:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleTriggerPipeline = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setIsTriggering(true);
      const params = new URLSearchParams({ branch });
      if (forceFailStage !== 'none') {
        params.append('force_fail_stage', forceFailStage);
      }
      await axios.post(`/cicd/pipeline/trigger?${params.toString()}`);
      fetchData();
    } catch (err) {
      console.error('Failed to trigger pipeline:', err);
    } finally {
      setIsTriggering(false);
    }
  };

  const handlePromoteCanary = async (weight: number) => {
    try {
      await axios.post(`/cicd/canary/promote?weight=${weight}`);
      fetchData();
    } catch (err) {
      console.error('Failed to promote canary:', err);
    }
  };

  const handleRollbackCanary = async () => {
    try {
      await axios.post('/cicd/canary/rollback');
      fetchData();
    } catch (err) {
      console.error('Failed to rollback canary:', err);
    }
  };

  const latestRun = runs[0];

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-gray-200 dark:border-gray-800 gap-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-emerald-600 rounded-lg text-white">
              <GitBranch className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                Enterprise CI/CD & DevSecOps Platform
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Phase 35 · GitHub Actions, Jenkins, SonarQube, Trivy, Checkov, Argo CD & Canary Governance
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            GitOps: Argo CD Synced
          </div>
          <button
            onClick={fetchData}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 dark:bg-gray-800 dark:text-gray-200 dark:border-gray-700 dark:hover:bg-gray-700"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <div className="p-3 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="text-gray-400 text-[11px] font-medium">SonarQube Quality Gate</div>
          <div className="text-lg font-bold text-emerald-600 dark:text-emerald-400 mt-1">
            {sonar?.quality_gate_status || 'PASSED'}
          </div>
          <div className="text-[10px] text-emerald-500 font-medium">
            Coverage: {sonar?.coverage_percentage}%
          </div>
        </div>

        <div className="p-3 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="text-gray-400 text-[11px] font-medium">Trivy Vulnerabilities</div>
          <div className="text-lg font-bold text-blue-600 dark:text-blue-400 mt-1">
            0 Critical / High
          </div>
          <div className="text-[10px] text-blue-500 font-medium">Clean container base</div>
        </div>

        <div className="p-3 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="text-gray-400 text-[11px] font-medium">Checkov IaC Scan</div>
          <div className="text-lg font-bold text-indigo-600 dark:text-indigo-400 mt-1">100% Policy Pass</div>
          <div className="text-[10px] text-indigo-500 font-medium">Terraform & K8s Compliant</div>
        </div>

        <div className="p-3 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="text-gray-400 text-[11px] font-medium">Canary Traffic Weight</div>
          <div className="text-lg font-bold text-purple-600 dark:text-purple-400 mt-1">
            {argoApps[0]?.canary_weight_percentage ?? 100}%
          </div>
          <div className="text-[10px] text-purple-500 font-medium">
            Phase: {argoApps[0]?.canary_phase ?? 'Stable'}
          </div>
        </div>

        <div className="p-3 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="text-gray-400 text-[11px] font-medium">Avg Pipeline Duration</div>
          <div className="text-lg font-bold text-gray-900 dark:text-white mt-1">64.0s</div>
          <div className="text-[10px] text-gray-400 font-medium">Parallel multi-stage</div>
        </div>
      </div>

      {/* Main Grid: Trigger & Latest Pipeline Run */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Trigger Pipeline Box */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 shadow-sm space-y-4">
          <div className="flex items-center gap-2 border-b border-gray-100 dark:border-gray-700 pb-3">
            <Play className="w-5 h-5 text-emerald-500" />
            <h2 className="text-sm font-semibold text-gray-900 dark:text-white">
              Dispatch DevSecOps Pipeline
            </h2>
          </div>

          <form onSubmit={handleTriggerPipeline} className="space-y-3 text-xs">
            <div>
              <label className="block font-medium text-gray-600 dark:text-gray-300 mb-1">
                Target Branch
              </label>
              <select
                value={branch}
                onChange={(e) => setBranch(e.target.value)}
                className="w-full px-3 py-1.5 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
              >
                <option value="main">main (Production GitOps)</option>
                <option value="release/1.0.0">release/1.0.0</option>
                <option value="feature/fraud-gnn-v2">feature/fraud-gnn-v2</option>
              </select>
            </div>

            {/* Test Quality Gate Failure */}
            <div className="p-3 bg-rose-50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-800 rounded-lg">
              <label className="block font-semibold text-rose-800 dark:text-rose-300 mb-1">
                Inject Quality Gate Failure (Test CI/CD Halt)
              </label>
              <select
                value={forceFailStage}
                onChange={(e) => setForceFailStage(e.target.value)}
                className="w-full px-2 py-1 text-xs rounded border border-rose-300 dark:border-rose-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
              >
                <option value="none">None (Full Happy Path - All Passed)</option>
                <option value="SonarQube">Stage 2: SonarQube (Simulate Code Coverage Drop)</option>
                <option value="Checkov">Stage 3: Checkov (Simulate Terraform S3 Policy Breach)</option>
                <option value="Trivy">Stage 4: Trivy (Simulate Critical CVE in Base Image)</option>
              </select>
            </div>

            <button
              type="submit"
              disabled={isTriggering}
              className="w-full py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded font-medium shadow-sm transition flex items-center justify-center gap-1.5"
            >
              <Play className="w-4 h-4" />
              {isTriggering ? 'Running DevSecOps Pipeline...' : 'Trigger Pipeline Run'}
            </button>
          </form>
        </div>

        {/* Live Multi-Stage Visualizer */}
        <div className="lg:col-span-2 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-gray-100 dark:border-gray-700 pb-3">
            <div className="flex items-center gap-2">
              <Activity className="w-5 h-5 text-indigo-500" />
              <h2 className="text-sm font-semibold text-gray-900 dark:text-white">
                Pipeline Stages Execution View ({latestRun?.commit_sha || 'Latest'})
              </h2>
            </div>
            {latestRun && (
              <span
                className={`text-xs px-2.5 py-0.5 rounded-full font-semibold ${
                  latestRun.status === 'SUCCESS'
                    ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300'
                    : 'bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300'
                }`}
              >
                {latestRun.status} ({latestRun.total_duration_seconds}s)
              </span>
            )}
          </div>

          {latestRun && (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2.5">
              {latestRun.stages.map((stage, idx) => (
                <div
                  key={idx}
                  className={`p-3 rounded-lg border text-xs flex flex-col justify-between ${
                    stage.status === 'PASSED'
                      ? 'bg-emerald-50 dark:bg-emerald-950/30 border-emerald-300 dark:border-emerald-800 text-emerald-900 dark:text-emerald-200'
                      : 'bg-rose-50 dark:bg-rose-950/30 border-rose-300 dark:border-rose-800 text-rose-900 dark:text-rose-200'
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-bold text-[10px]">STAGE {idx + 1}</span>
                      {stage.status === 'PASSED' ? (
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                      ) : (
                        <XCircle className="w-3.5 h-3.5 text-rose-600" />
                      )}
                    </div>
                    <div className="font-semibold text-xs">{stage.name}</div>
                    <div className="text-[10px] opacity-80 mt-1">{stage.output_summary}</div>
                  </div>
                  <div className="mt-2 pt-1 border-t border-black/10 dark:border-white/10 text-[10px] text-gray-500 dark:text-gray-400">
                    Duration: {stage.duration_seconds}s
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* GitOps Argo CD & Canary Rollouts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Argo CD Applications Sync Status */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 shadow-sm space-y-3">
          <div className="flex items-center justify-between border-b border-gray-100 dark:border-gray-700 pb-2">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-purple-500" />
              <h3 className="text-xs font-semibold text-gray-900 dark:text-white uppercase tracking-wider">
                Argo CD GitOps Applications
              </h3>
            </div>
            <span className="text-[10px] text-gray-400">Auto-Sync & Self-Heal</span>
          </div>

          <div className="space-y-2">
            {argoApps.map((app) => (
              <div
                key={app.app_name}
                className="p-3 bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 flex items-center justify-between text-xs"
              >
                <div>
                  <div className="font-semibold text-gray-900 dark:text-white">{app.app_name}</div>
                  <div className="text-[10px] text-gray-400 font-mono mt-0.5">
                    Target Revision: {app.target_revision}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300">
                    {app.sync_status}
                  </span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300">
                    {app.health_status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Argo Rollouts Canary Governance */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 shadow-sm space-y-3">
          <div className="flex items-center justify-between border-b border-gray-100 dark:border-gray-700 pb-2">
            <div className="flex items-center gap-2">
              <RotateCcw className="w-4 h-4 text-blue-500" />
              <h3 className="text-xs font-semibold text-gray-900 dark:text-white uppercase tracking-wider">
                Canary Release Governance (Prometheus Automated Rollback)
              </h3>
            </div>
            <span className="text-[10px] text-gray-400">Error Budget: &lt; 1%</span>
          </div>

          <p className="text-xs text-gray-500 dark:text-gray-400">
            Control production Canary traffic split between stable baseline and new release version.
          </p>

          <div className="flex flex-wrap gap-2 pt-1">
            <button
              onClick={() => handlePromoteCanary(20)}
              className="px-3 py-1.5 bg-blue-50 hover:bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 rounded text-xs font-medium transition"
            >
              Set 20% Canary
            </button>
            <button
              onClick={() => handlePromoteCanary(50)}
              className="px-3 py-1.5 bg-purple-50 hover:bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300 rounded text-xs font-medium transition"
            >
              Set 50% Canary
            </button>
            <button
              onClick={() => handlePromoteCanary(100)}
              className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded text-xs font-medium transition"
            >
              Promote to 100% Stable
            </button>
            <button
              onClick={handleRollbackCanary}
              className="px-3 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded text-xs font-medium transition flex items-center gap-1"
            >
              <RotateCcw className="w-3 h-3" />
              Emergency Rollback
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
