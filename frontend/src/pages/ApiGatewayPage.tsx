import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  Key,
  Users,
  Server,
  Activity,
  Lock,
  Unlock,
  AlertTriangle,
  RefreshCw,
  PlusCircle,
  Clock,
  Layers,
  Copy,
  CheckCircle,
  FileText
} from 'lucide-react';
import axios from 'axios';

interface GatewayHealth {
  status: string;
  service: string;
  version: string;
  phase: string;
  features: string[];
  request_id: string;
}

interface GatewayMetrics {
  total_requests: number;
  authenticated_requests: number;
  service_requests: number;
  rate_limited_requests: number;
  rate_limit_blocks: number;
  active_tenants_count: number;
  avg_latency_ms: number;
  tenant_traffic_distribution?: Record<string, number>;
}

interface TenantCase {
  case_id: string;
  tenant_id: string;
  title: string;
  severity: string;
  status: string;
  amount: number;
  description?: string;
  created_at: string;
}

export const ApiGatewayPage: React.FC = () => {
  // Config state
  const [health, setHealth] = useState<GatewayHealth | null>(null);
  const [metrics, setMetrics] = useState<GatewayMetrics | null>(null);
  const [loading, setLoading] = useState(false);
  const [copiedToken, setCopiedToken] = useState(false);

  // JWT Token generator form
  const [userId, setUserId] = useState('usr-analyst-01');
  const [tenantId, setTenantId] = useState('tenant-alpha');
  const [role, setRole] = useState('Analyst');
  const [expiresIn, setExpiresIn] = useState(3600);
  const [generatedToken, setGeneratedToken] = useState('');
  const [decodedClaims, setDecodedClaims] = useState<any>(null);

  // Multi-tenant case management
  const [tenantCases, setTenantCases] = useState<TenantCase[]>([]);
  const [newCaseTitle, setNewCaseTitle] = useState('');
  const [newCaseSeverity, setNewCaseSeverity] = useState('HIGH');
  const [newCaseAmount, setNewCaseAmount] = useState('150000');
  const [caseLoading, setCaseLoading] = useState(false);

  // RBAC tester
  const [rbacResult, setRbacResult] = useState<{ status: string; detail: string; role?: string } | null>(null);

  // S2S Echo tester
  const [s2sKey, setS2sKey] = useState('finguard-internal-s2s-secret-key-2026');
  const [s2sService, setS2sService] = useState('fraud-scoring-engine');
  const [s2sAction, setS2sAction] = useState('batch-eval-sync');
  const [s2sResponse, setS2sResponse] = useState<any>(null);

  // Rate limit tester
  const [rateLimitHits, setRateLimitHits] = useState<string[]>([]);
  const [rateLimitBlocked, setRateLimitBlocked] = useState(false);
  const [retryAfterSeconds, setRetryAfterSeconds] = useState<number | null>(null);

  const fetchHealthAndMetrics = async () => {
    try {
      setLoading(true);
      const [healthRes, metricsRes] = await Promise.all([
        axios.get('/api/v1/health'),
        axios.get('/api/v1/gateway/metrics'),
      ]);
      setHealth(healthRes.data);
      setMetrics(metricsRes.data);
    } catch (err) {
      console.error('Failed to fetch gateway telemetry:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealthAndMetrics();
    // Auto-generate initial token for demo
    handleGenerateToken();
  }, []);

  const handleGenerateToken = async () => {
    try {
      const resp = await axios.post('/api/v1/auth/token', {
        user_id: userId,
        tenant_id: tenantId,
        roles: [role],
        role: role,
        expires_in_seconds: expiresIn,
      });
      const token = resp.data.access_token;
      setGeneratedToken(token);

      // Verify token immediately via /auth/me
      const meRes = await axios.get('/api/v1/auth/me', {
        headers: { Authorization: `Bearer ${token}` },
      });
      setDecodedClaims(meRes.data);

      // Auto-refresh tenant cases
      fetchCasesWithToken(token);
    } catch (err: any) {
      console.error('Error issuing token:', err);
    }
  };

  const fetchCasesWithToken = async (tokenToUse?: string) => {
    const token = tokenToUse || generatedToken;
    if (!token) return;
    try {
      setCaseLoading(true);
      const res = await axios.get('/api/v1/cases', {
        headers: { Authorization: `Bearer ${token}` },
      });
      setTenantCases(res.data);
    } catch (err) {
      console.error('Error fetching tenant cases:', err);
    } finally {
      setCaseLoading(false);
    }
  };

  const handleCreateCase = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!generatedToken || !newCaseTitle) return;
    try {
      setCaseLoading(true);
      await axios.post(
        '/api/v1/cases',
        {
          title: newCaseTitle,
          severity: newCaseSeverity,
          amount: parseFloat(newCaseAmount) || 0,
        },
        {
          headers: { Authorization: `Bearer ${generatedToken}` },
        }
      );
      setNewCaseTitle('');
      fetchCasesWithToken(generatedToken);
      fetchHealthAndMetrics();
    } catch (err) {
      console.error('Error creating case:', err);
    } finally {
      setCaseLoading(false);
    }
  };

  const testRbacAudit = async () => {
    if (!generatedToken) return;
    try {
      const res = await axios.get('/api/v1/admin/audit', {
        headers: { Authorization: `Bearer ${generatedToken}` },
      });
      setRbacResult({
        status: 'GRANTED (200 OK)',
        detail: `Access granted for privileged scope: ${res.data.audit_scope}`,
        role: res.data.authorized_role,
      });
    } catch (err: any) {
      if (err.response && err.response.status === 403) {
        setRbacResult({
          status: 'FORBIDDEN (403)',
          detail: `User role '${role}' lacks Admin/Auditor privileges. Access denied by Gateway RBAC.`,
        });
      } else {
        setRbacResult({
          status: 'ERROR',
          detail: err.message || 'Unknown verification error',
        });
      }
    }
  };

  const handleS2sCall = async () => {
    try {
      const res = await axios.post(
        '/api/v1/service/echo',
        {
          service_name: s2sService,
          action: s2sAction,
          payload: { timestamp: new Date().toISOString(), status: 'healthy' },
        },
        {
          headers: { 'X-Service-Key': s2sKey },
        }
      );
      setS2sResponse(res.data);
      fetchHealthAndMetrics();
    } catch (err: any) {
      setS2sResponse({
        error: true,
        status: err.response?.status,
        detail: err.response?.data?.detail || err.message,
      });
    }
  };

  const handleRateLimitTrigger = async () => {
    const timestamp = new Date().toLocaleTimeString();
    try {
      const res = await axios.get('/api/v1/rate-limit-test');
      setRateLimitHits((prev) => [
        `[${timestamp}] Allowed (200 OK) - Remaining: ${res.data.remaining_requests}`,
        ...prev.slice(0, 5),
      ]);
      setRateLimitBlocked(false);
      setRetryAfterSeconds(null);
    } catch (err: any) {
      if (err.response && err.response.status === 429) {
        const retry = err.response.headers['retry-after'] || '60';
        setRateLimitHits((prev) => [
          `[${timestamp}] BLOCKED (429 Too Many Requests) - Retry-After: ${retry}s`,
          ...prev.slice(0, 5),
        ]);
        setRateLimitBlocked(true);
        setRetryAfterSeconds(parseInt(retry, 10));
      }
    }
    fetchHealthAndMetrics();
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedToken(true);
    setTimeout(() => setCopiedToken(false), 2000);
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-gray-200 dark:border-gray-800 gap-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-600 rounded-lg text-white">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                Enterprise API Gateway & Security Hub
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Phase 32 · Microservices Access Control, JWT Claims, RBAC, Multi-Tenancy & S2S Routing
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            Gateway Version: {health?.version?.toUpperCase() || 'V1'}
          </div>
          <button
            onClick={fetchHealthAndMetrics}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 dark:bg-gray-800 dark:text-gray-200 dark:border-gray-700 dark:hover:bg-gray-700"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="p-4 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="flex items-center justify-between text-gray-500 dark:text-gray-400 text-xs font-medium mb-1">
            <span>Total Requests</span>
            <Activity className="w-4 h-4 text-indigo-500" />
          </div>
          <div className="text-2xl font-bold text-gray-900 dark:text-white">
            {metrics?.total_requests ?? 0}
          </div>
          <span className="text-xs text-gray-400">/api/v1 gateway ingress</span>
        </div>

        <div className="p-4 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="flex items-center justify-between text-gray-500 dark:text-gray-400 text-xs font-medium mb-1">
            <span>Authenticated</span>
            <Key className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">
            {metrics?.authenticated_requests ?? 0}
          </div>
          <span className="text-xs text-emerald-600/80">JWT verified traffic</span>
        </div>

        <div className="p-4 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="flex items-center justify-between text-gray-500 dark:text-gray-400 text-xs font-medium mb-1">
            <span>S2S Invocations</span>
            <Server className="w-4 h-4 text-cyan-500" />
          </div>
          <div className="text-2xl font-bold text-cyan-600 dark:text-cyan-400">
            {metrics?.service_requests ?? 0}
          </div>
          <span className="text-xs text-gray-400">Machine-to-machine</span>
        </div>

        <div className="p-4 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="flex items-center justify-between text-gray-500 dark:text-gray-400 text-xs font-medium mb-1">
            <span>Active Tenants</span>
            <Users className="w-4 h-4 text-purple-500" />
          </div>
          <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
            {metrics?.active_tenants_count ?? 2}
          </div>
          <span className="text-xs text-purple-600/80">Isolated partitions</span>
        </div>

        <div className="p-4 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="flex items-center justify-between text-gray-500 dark:text-gray-400 text-xs font-medium mb-1">
            <span>Rate Drops</span>
            <AlertTriangle className="w-4 h-4 text-rose-500" />
          </div>
          <div className="text-2xl font-bold text-rose-600 dark:text-rose-400">
            {metrics?.rate_limited_requests ?? 0}
          </div>
          <span className="text-xs text-rose-500/80">429 Throttled</span>
        </div>
      </div>

      {/* Main Grid: JWT Workbench & Multi-Tenant Partitioning */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* JWT Issuer Workbench */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-gray-100 dark:border-gray-700 pb-3">
            <div className="flex items-center gap-2">
              <Key className="w-5 h-5 text-indigo-500" />
              <h2 className="text-base font-semibold text-gray-900 dark:text-white">
                JWT Identity & Token Issuer
              </h2>
            </div>
            <span className="text-xs px-2 py-0.5 rounded bg-indigo-50 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300 font-mono">
              RFC-7519 HS256
            </span>
          </div>

          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                User ID (sub)
              </label>
              <input
                type="text"
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
                className="w-full px-3 py-1.5 text-sm rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                Tenant Partition
              </label>
              <select
                value={tenantId}
                onChange={(e) => setTenantId(e.target.value)}
                className="w-full px-3 py-1.5 text-sm rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
              >
                <option value="tenant-alpha">tenant-alpha (Bank Alpha)</option>
                <option value="tenant-beta">tenant-beta (NeoBank Beta)</option>
                <option value="tenant-gamma">tenant-gamma (FinTech Gamma)</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                Assigned Role
              </label>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="w-full px-3 py-1.5 text-sm rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
              >
                <option value="Analyst">Analyst (Standard Read/Write)</option>
                <option value="Investigator">Investigator (Case Actions)</option>
                <option value="Admin">Admin (Privileged Operations)</option>
                <option value="Auditor">Auditor (Full Audit Access)</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                Token TTL (seconds)
              </label>
              <input
                type="number"
                value={expiresIn}
                onChange={(e) => setExpiresIn(parseInt(e.target.value, 10))}
                className="w-full px-3 py-1.5 text-sm rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
              />
            </div>
          </div>

          <div className="flex gap-2 pt-1">
            <button
              onClick={handleGenerateToken}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium rounded-lg shadow-sm transition"
            >
              Sign & Issue JWT Token
            </button>
            <button
              onClick={testRbacAudit}
              className="px-4 py-2 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-800 dark:text-gray-200 text-xs font-medium rounded-lg transition"
            >
              Test Admin Access (RBAC)
            </button>
          </div>

          {/* RBAC verification banner */}
          {rbacResult && (
            <div
              className={`p-3 rounded-lg text-xs flex items-start gap-2 ${
                rbacResult.status.includes('GRANTED')
                  ? 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800'
                  : 'bg-rose-50 dark:bg-rose-950/40 text-rose-800 dark:text-rose-300 border border-rose-200 dark:border-rose-800'
              }`}
            >
              {rbacResult.status.includes('GRANTED') ? (
                <Lock className="w-4 h-4 mt-0.5 text-emerald-600" />
              ) : (
                <AlertTriangle className="w-4 h-4 mt-0.5 text-rose-600" />
              )}
              <div>
                <p className="font-semibold">{rbacResult.status}</p>
                <p>{rbacResult.detail}</p>
              </div>
            </div>
          )}

          {/* Decoded Token Claims */}
          <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-3 border border-gray-200 dark:border-gray-800">
            <div className="flex items-center justify-between text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">
              <span>Decoded Identity Context</span>
              <button
                onClick={() => copyToClipboard(generatedToken)}
                className="flex items-center gap-1 text-indigo-600 hover:underline"
              >
                {copiedToken ? <CheckCircle className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                {copiedToken ? 'Copied' : 'Copy JWT'}
              </button>
            </div>
            <pre className="text-xs font-mono text-gray-700 dark:text-gray-300 overflow-x-auto p-2 bg-white dark:bg-black/30 rounded border border-gray-200 dark:border-gray-800">
              {JSON.stringify(decodedClaims, null, 2)}
            </pre>
          </div>
        </div>

        {/* Multi-Tenant Scoped Cases */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-gray-100 dark:border-gray-700 pb-3">
            <div className="flex items-center gap-2">
              <Layers className="w-5 h-5 text-purple-500" />
              <h2 className="text-base font-semibold text-gray-900 dark:text-white">
                Multi-Tenant Scoped Cases
              </h2>
            </div>
            <span className="text-xs px-2 py-0.5 rounded bg-purple-50 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300 font-mono">
              Tenant: {tenantId}
            </span>
          </div>

          <p className="text-xs text-gray-500 dark:text-gray-400">
            Cases are filtered strictly by verified JWT claims. A user from <code>tenant-alpha</code> will never see cases belonging to <code>tenant-beta</code>.
          </p>

          {/* Create new case for active tenant */}
          <form onSubmit={handleCreateCase} className="p-3 bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 space-y-2">
            <div className="text-xs font-semibold text-gray-700 dark:text-gray-300">
              Create Case under {tenantId}
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
              <input
                type="text"
                placeholder="Case Title / Summary"
                value={newCaseTitle}
                onChange={(e) => setNewCaseTitle(e.target.value)}
                className="px-2 py-1.5 text-xs rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                required
              />
              <select
                value={newCaseSeverity}
                onChange={(e) => setNewCaseSeverity(e.target.value)}
                className="px-2 py-1.5 text-xs rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
              >
                <option value="LOW">LOW</option>
                <option value="MEDIUM">MEDIUM</option>
                <option value="HIGH">HIGH</option>
                <option value="CRITICAL">CRITICAL</option>
              </select>
              <input
                type="number"
                placeholder="Amount (INR)"
                value={newCaseAmount}
                onChange={(e) => setNewCaseAmount(e.target.value)}
                className="px-2 py-1.5 text-xs rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
              />
            </div>
            <button
              type="submit"
              disabled={caseLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-purple-600 hover:bg-purple-700 text-white text-xs font-medium rounded shadow-sm transition"
            >
              <PlusCircle className="w-3.5 h-3.5" />
              Add Scoped Case
            </button>
          </form>

          {/* Cases List */}
          <div className="space-y-2 max-h-56 overflow-y-auto">
            {tenantCases.length === 0 ? (
              <div className="text-center py-6 text-gray-400 text-xs">
                No cases found for active tenant ({tenantId}).
              </div>
            ) : (
              tenantCases.map((c) => (
                <div
                  key={c.case_id}
                  className="p-3 bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 flex items-center justify-between"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-semibold text-gray-900 dark:text-white">
                        {c.case_id}
                      </span>
                      <span
                        className={`text-[10px] px-1.5 py-0.5 rounded font-semibold ${
                          c.severity === 'CRITICAL'
                            ? 'bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300'
                            : c.severity === 'HIGH'
                            ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300'
                            : 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300'
                        }`}
                      >
                        {c.severity}
                      </span>
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-purple-50 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300">
                        {c.tenant_id}
                      </span>
                    </div>
                    <div className="text-xs text-gray-700 dark:text-gray-300 mt-1">
                      {c.title}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-xs font-semibold text-gray-900 dark:text-white">
                      ₹{c.amount?.toLocaleString()}
                    </div>
                    <div className="text-[10px] text-gray-400 uppercase">{c.status}</div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* S2S Communication & Rate Limiter Stress Tester */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Service-to-Service Machine Auth */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-gray-100 dark:border-gray-700 pb-3">
            <div className="flex items-center gap-2">
              <Server className="w-5 h-5 text-cyan-500" />
              <h2 className="text-base font-semibold text-gray-900 dark:text-white">
                Service-to-Service (S2S) Machine Auth
              </h2>
            </div>
            <span className="text-xs px-2 py-0.5 rounded bg-cyan-50 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-300 font-mono">
              X-Service-Key Header
            </span>
          </div>

          <div className="space-y-3 text-xs">
            <div>
              <label className="block font-medium text-gray-500 dark:text-gray-400 mb-1">
                Internal Service Key
              </label>
              <input
                type="text"
                value={s2sKey}
                onChange={(e) => setS2sKey(e.target.value)}
                className="w-full px-3 py-1.5 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-gray-900 dark:text-white font-mono text-xs"
              />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block font-medium text-gray-500 dark:text-gray-400 mb-1">
                  Calling Service
                </label>
                <input
                  type="text"
                  value={s2sService}
                  onChange={(e) => setS2sService(e.target.value)}
                  className="w-full px-3 py-1.5 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-gray-900 dark:text-white text-xs"
                />
              </div>
              <div>
                <label className="block font-medium text-gray-500 dark:text-gray-400 mb-1">
                  Service Action
                </label>
                <input
                  type="text"
                  value={s2sAction}
                  onChange={(e) => setS2sAction(e.target.value)}
                  className="w-full px-3 py-1.5 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-gray-900 dark:text-white text-xs"
                />
              </div>
            </div>

            <button
              onClick={handleS2sCall}
              className="px-4 py-2 bg-cyan-600 hover:bg-cyan-700 text-white text-xs font-medium rounded-lg shadow-sm transition"
            >
              Trigger S2S Machine Request (/api/v1/service/echo)
            </button>

            {s2sResponse && (
              <div className="bg-gray-50 dark:bg-gray-900 p-3 rounded-lg border border-gray-200 dark:border-gray-800">
                <div className="text-[11px] font-semibold text-gray-500 mb-1">
                  S2S Gateway Response:
                </div>
                <pre className="text-xs font-mono text-gray-800 dark:text-gray-200 overflow-x-auto">
                  {JSON.stringify(s2sResponse, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </div>

        {/* Sliding-Window Rate Limiting */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-gray-100 dark:border-gray-700 pb-3">
            <div className="flex items-center gap-2">
              <Clock className="w-5 h-5 text-amber-500" />
              <h2 className="text-base font-semibold text-gray-900 dark:text-white">
                Sliding-Window Rate Limiter
              </h2>
            </div>
            <span className="text-xs px-2 py-0.5 rounded bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300 font-mono">
              Limit: 3 req / 60s
            </span>
          </div>

          <p className="text-xs text-gray-500 dark:text-gray-400">
            Protects downstream microservices from DDoS or rapid looping. Rapidly click below to exceed the threshold and trigger HTTP 429 back-off headers.
          </p>

          <div className="flex gap-2">
            <button
              onClick={handleRateLimitTrigger}
              className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white text-xs font-medium rounded-lg shadow-sm transition"
            >
              Send Request to Rate Limiter
            </button>
            <button
              onClick={() => {
                setRateLimitHits([]);
                setRateLimitBlocked(false);
              }}
              className="px-3 py-2 bg-gray-100 dark:bg-gray-700 text-xs font-medium rounded-lg text-gray-700 dark:text-gray-300"
            >
              Clear Log
            </button>
          </div>

          {rateLimitBlocked && (
            <div className="p-3 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 rounded-lg text-xs text-rose-800 dark:text-rose-300 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-600" />
              <div>
                <span className="font-semibold">HTTP 429 Too Many Requests</span>
                <p>Client throttled. Back off for {retryAfterSeconds || 60} seconds.</p>
              </div>
            </div>
          )}

          <div className="space-y-1.5 max-h-40 overflow-y-auto">
            {rateLimitHits.map((log, idx) => (
              <div
                key={idx}
                className={`text-xs font-mono p-2 rounded ${
                  log.includes('BLOCKED')
                    ? 'bg-rose-50 text-rose-800 dark:bg-rose-900/20 dark:text-rose-300'
                    : 'bg-emerald-50 text-emerald-800 dark:bg-emerald-900/20 dark:text-emerald-300'
                }`}
              >
                {log}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

