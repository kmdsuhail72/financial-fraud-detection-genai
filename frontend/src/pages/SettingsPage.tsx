import React, { useState } from 'react';
import {
  Settings,
  Server,
  CloudOff,
  Activity,
  CheckCircle2,
  XCircle,
  Shield,
  Key,
  Database,
  Cpu,
  RefreshCw
} from 'lucide-react';

interface SettingsPageProps {
  isDemoMode: boolean;
  onToggleDemoMode: () => void;
  apiBaseUrl: string;
  onUpdateApiBaseUrl: (url: string) => void;
  onTestBackend: () => Promise<boolean>;
}

export const SettingsPage: React.FC<SettingsPageProps> = ({
  isDemoMode,
  onToggleDemoMode,
  apiBaseUrl,
  onUpdateApiBaseUrl,
  onTestBackend
}) => {
  const [urlInput, setUrlInput] = useState(apiBaseUrl);
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);

  const handleSaveUrl = (e: React.FormEvent) => {
    e.preventDefault();
    onUpdateApiBaseUrl(urlInput.trim());
  };

  const handleRunTest = async () => {
    setIsTesting(true);
    setTestResult(null);
    try {
      const ok = await onTestBackend();
      if (ok) {
        setTestResult({
          success: true,
          message: 'Successfully reached FinGuard AI Backend API (status: 200 OK)'
        });
      } else {
        setTestResult({
          success: false,
          message: 'Failed to reach API endpoint. Ensure FastAPI server is running on port 8001.'
        });
      }
    } catch (err: any) {
      setTestResult({
        success: false,
        message: `Error connecting to backend: ${err.message || 'Network error'}`
      });
    } finally {
      setIsTesting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h2 className="text-xl font-bold text-white tracking-tight">Platform Governance & Environment Settings</h2>
        <p className="text-xs text-slate-400 mt-1">
          Configure API connection endpoints, sandbox emulation, and view cloud infrastructure parameters.
        </p>
      </div>

      {/* Execution Mode Card */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className={`p-2 rounded-lg ${isDemoMode ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'}`}>
              {isDemoMode ? <CloudOff className="w-5 h-5" /> : <Server className="w-5 h-5" />}
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white">
                {isDemoMode ? 'Offline Demo Sandbox Mode' : 'Live AWS Backend Mode'}
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                {isDemoMode
                  ? 'Active: Operating with rich pre-packaged mock cases and immediate state mutations in browser.'
                  : 'Active: Routing API calls directly to FastAPI backend on port 8001 / DynamoDB.'}
              </p>
            </div>
          </div>

          <button
            onClick={onToggleDemoMode}
            className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all shadow-sm ${
              isDemoMode
                ? 'bg-sky-600 hover:bg-sky-500 text-white'
                : 'bg-amber-600 hover:bg-amber-500 text-white'
            }`}
          >
            {isDemoMode ? 'Switch to Live API' : 'Switch to Demo Sandbox'}
          </button>
        </div>
      </div>

      {/* Backend API Configuration */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-4">
        <h3 className="text-sm font-semibold text-white tracking-tight flex items-center gap-2">
          <Server className="w-4 h-4 text-sky-400" />
          Backend API Connection
        </h3>

        <form onSubmit={handleSaveUrl} className="space-y-3">
          <div>
            <label className="block text-xs font-mono text-slate-400 mb-1">
              API Base URL / Proxy Path
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={urlInput}
                onChange={(e) => setUrlInput(e.target.value)}
                placeholder="/api or http://localhost:8001"
                className="flex-1 bg-slate-950/80 border border-slate-800 rounded-lg px-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:ring-1 focus:ring-sky-500"
              />
              <button
                type="submit"
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg transition-colors"
              >
                Save
              </button>
              <button
                type="button"
                onClick={handleRunTest}
                disabled={isTesting}
                className="px-4 py-2 bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold rounded-lg flex items-center space-x-1.5 transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isTesting ? 'animate-spin' : ''}`} />
                <span>Test Connection</span>
              </button>
            </div>
          </div>
        </form>

        {testResult && (
          <div
            className={`p-3 rounded-lg border text-xs flex items-center space-x-2 ${
              testResult.success
                ? 'bg-emerald-950/30 border-emerald-800/40 text-emerald-300'
                : 'bg-rose-950/30 border-rose-800/40 text-rose-300'
            }`}
          >
            {testResult.success ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            ) : (
              <XCircle className="w-4 h-4 text-rose-400 shrink-0" />
            )}
            <span>{testResult.message}</span>
          </div>
        )}
      </div>

      {/* Cloud & ML Infrastructure Architecture Blueprint */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-4">
        <h3 className="text-sm font-semibold text-white tracking-tight flex items-center gap-2">
          <Database className="w-4 h-4 text-indigo-400" />
          AWS Cloud Architecture Parameters
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
          <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800 space-y-1">
            <div className="text-[10px] font-mono uppercase text-slate-500">AWS Target Region</div>
            <div className="font-mono font-semibold text-slate-200">ap-south-1 (Mumbai)</div>
          </div>

          <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800 space-y-1">
            <div className="text-[10px] font-mono uppercase text-slate-500">Kinesis Stream</div>
            <div className="font-mono font-semibold text-slate-200">finguard-ai-transactions-stream</div>
          </div>

          <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800 space-y-1">
            <div className="text-[10px] font-mono uppercase text-slate-500">SageMaker Real-Time Endpoint</div>
            <div className="font-mono font-semibold text-slate-200">finguard-ai-fraud-scoring-endpoint</div>
          </div>

          <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800 space-y-1">
            <div className="text-[10px] font-mono uppercase text-slate-500">Amazon Bedrock Model</div>
            <div className="font-mono font-semibold text-slate-200">anthropic.claude-3-5-sonnet-20241022-v2:0</div>
          </div>

          <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800 space-y-1">
            <div className="text-[10px] font-mono uppercase text-slate-500">DynamoDB Case Store</div>
            <div className="font-mono font-semibold text-slate-200">finguard-ai-investigation-cases</div>
          </div>

          <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800 space-y-1">
            <div className="text-[10px] font-mono uppercase text-slate-500">DynamoDB Decision Store</div>
            <div className="font-mono font-semibold text-slate-200">finguard-ai-fraud-decisions</div>
          </div>
        </div>
      </div>

      {/* Investigator Identity Card */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-3">
        <h3 className="text-sm font-semibold text-white tracking-tight flex items-center gap-2">
          <Shield className="w-4 h-4 text-sky-400" />
          Active Investigator Credentials & RBAC
        </h3>

        <div className="flex items-center space-x-4 p-3 bg-slate-950/60 rounded-lg border border-slate-800">
          <div className="w-12 h-12 rounded-full bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center font-bold text-sm text-white shadow-md">
            AM
          </div>
          <div className="space-y-0.5">
            <div className="text-sm font-bold text-white">Alex Mercer</div>
            <div className="text-xs text-sky-400 font-mono">Senior Fraud Investigator (Tier-2)</div>
            <div className="text-[11px] text-slate-400 font-mono">
              Role: <span className="text-slate-300">FraudAnalyst_Write_Resolve</span> &bull; Session TTL: 7h 45m
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

