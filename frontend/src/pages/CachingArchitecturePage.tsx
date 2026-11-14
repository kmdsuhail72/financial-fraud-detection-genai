import React, { useState, useEffect } from 'react';
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  Boxes,
  CheckCircle2,
  Clock,
  Database,
  ExternalLink,
  Flame,
  Layers,
  Lock,
  Play,
  RefreshCw,
  Repeat,
  Server,
  ShieldAlert,
  ShieldCheck,
  Trash2,
  Zap,
} from 'lucide-react';
import axios from 'axios';

interface CachePolicy {
  data_type: string;
  ttl_seconds: number;
  ttl_display: string;
  invalidation_trigger: string;
  description: string;
}

interface CacheMetrics {
  hits: number;
  misses: number;
  hit_ratio: number;
  evictions: number;
  total_keys: number;
  backend_type: string;
}

interface CustomerProfile {
  customer_id: string;
  name: string;
  risk_tier: string;
  country: string;
  kyc_status: string;
  email: string;
  updated_at: string;
}

interface RateLimitResult {
  allowed: boolean;
  current_count: number;
  limit: number;
  remaining: number;
  reset_seconds: number;
  retry_after?: number | null;
}

interface IdempotencyRecord {
  tenant_id: string;
  key_hash: string;
  status: string;
  response_payload: any;
  created_at: string;
  expires_at: string;
  is_replayed: boolean;
}

export const CachingArchitecturePage: React.FC = () => {
  const [loading, setLoading] = useState<boolean>(true);
  const [backendType, setBackendType] = useState<string>('memory');
  const [redisConnected, setRedisConnected] = useState<boolean>(false);
  const [metrics, setMetrics] = useState<CacheMetrics>({
    hits: 0,
    misses: 0,
    hit_ratio: 0,
    evictions: 0,
    total_keys: 0,
    backend_type: 'memory',
  });
  const [policies, setPolicies] = useState<CachePolicy[]>([]);

  // Cache-Aside State
  const [selectedCustomerId, setSelectedCustomerId] = useState<string>('CUST-1001');
  const [activeProfile, setActiveProfile] = useState<CustomerProfile | null>(null);
  const [profileFetchSource, setProfileFetchSource] = useState<string | null>(null);
  const [newRiskTier, setNewRiskTier] = useState<string>('HIGH');
  const [profileActionLoading, setProfileActionLoading] = useState<boolean>(false);

  // Rate Limiting State
  const [rateLimitClient, setRateLimitClient] = useState<string>('portal-analyst-session');
  const [rateLimitMax, setRateLimitMax] = useState<number>(5);
  const [rateLimitWindow, setRateLimitWindow] = useState<number>(60);
  const [lastRateLimitResult, setLastRateLimitResult] = useState<RateLimitResult | null>(null);
  const [rateLimitLog, setRateLimitLog] = useState<{ id: number; timestamp: string; allowed: boolean; count: number }[]>([]);

  // Idempotency State
  const [idemTenantId, setIdemTenantId] = useState<string>('tenant-hdfc-bank');
  const [idemKey, setIdemKey] = useState<string>('tx-settle-88019');
  const [idemAmount, setIdemAmount] = useState<number>(25000);
  const [idemResult, setIdemResult] = useState<IdempotencyRecord | null>(null);
  const [idemLoading, setIdemLoading] = useState<boolean>(false);

  // Fetch base health and policies
  const fetchHealthAndMetrics = async () => {
    try {
      setLoading(true);
      const res = await axios.get('/api/v1/caching/health');
      setBackendType(res.data.backend || 'memory');
      setRedisConnected(res.data.redis_connected || false);
      if (res.data.metrics) setMetrics(res.data.metrics);
      if (res.data.policies) setPolicies(res.data.policies);
    } catch (err) {
      console.error('Failed to load caching health:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealthAndMetrics();
    const interval = setInterval(fetchHealthAndMetrics, 10000);
    return () => clearInterval(interval);
  }, []);

  // Fetch Customer Profile via Cache-Aside
  const handleFetchProfile = async () => {
    setProfileActionLoading(true);
    const startTime = performance.now();
    try {
      const res = await axios.get(`/api/v1/caching/profile/${selectedCustomerId}`);
      const duration = performance.now() - startTime;
      setActiveProfile(res.data);
      // Fast response indicates cache hit
      setProfileFetchSource(duration < 15 ? 'CACHE_HIT (Sub-millisecond)' : 'CACHE_MISS (Read-Through DB)');
      fetchHealthAndMetrics();
    } catch (err: any) {
      console.error('Error fetching profile:', err);
      alert(err.response?.data?.detail || 'Failed to fetch customer profile');
    } finally {
      setProfileActionLoading(false);
    }
  };

  // Update Profile & Invalidate Cache
  const handleUpdateAndInvalidate = async () => {
    setProfileActionLoading(true);
    try {
      const res = await axios.put(`/api/v1/caching/profile/${selectedCustomerId}`, {
        risk_tier: newRiskTier,
      });
      setActiveProfile(res.data);
      setProfileFetchSource('INVALIDATED & SYNCED');
      fetchHealthAndMetrics();
    } catch (err: any) {
      console.error('Error updating profile:', err);
      alert(err.response?.data?.detail || 'Failed to update profile');
    } finally {
      setProfileActionLoading(false);
    }
  };

  // Test Rate Limiter
  const handleSendRateLimitRequest = async () => {
    try {
      const res = await axios.post('/api/v1/caching/rate-limit/check', {
        identifier: rateLimitClient,
        limit: Number(rateLimitMax),
        window_seconds: Number(rateLimitWindow),
        cost: 1,
      });
      const result: RateLimitResult = res.data;
      setLastRateLimitResult(result);
      setRateLimitLog((prev) => [
        {
          id: Date.now(),
          timestamp: new Date().toLocaleTimeString(),
          allowed: result.allowed,
          count: result.current_count,
        },
        ...prev.slice(0, 9),
      ]);
    } catch (err) {
      console.error('Rate limit test error:', err);
    }
  };

  // Execute Idempotent Operation
  const handleExecuteIdempotentTx = async () => {
    setIdemLoading(true);
    try {
      const res = await axios.post('/api/v1/caching/idempotency/execute', {
        tenant_id: idemTenantId,
        idempotency_key: idemKey,
        request_payload: {
          transaction_id: `TX-${idemKey.toUpperCase()}`,
          amount: Number(idemAmount),
          currency: 'INR',
        },
      });
      setIdemResult(res.data);
      fetchHealthAndMetrics();
    } catch (err: any) {
      console.error('Idempotency error:', err);
      alert('Failed to execute idempotent request');
    } finally {
      setIdemLoading(false);
    }
  };

  // Flush Cache
  const handleFlushCache = async () => {
    if (!window.confirm('Are you sure you want to flush all entries from the active cache?')) return;
    try {
      await axios.post('/api/v1/caching/flush');
      setActiveProfile(null);
      setProfileFetchSource(null);
      fetchHealthAndMetrics();
      alert('Cache flushed successfully');
    } catch (err) {
      console.error('Flush error:', err);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 p-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-slate-800 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-3 bg-red-600/20 text-red-400 rounded-xl border border-red-500/30">
              <Database className="w-8 h-8" />
            </div>
            <div>
              <h1 className="text-3xl font-extrabold tracking-tight">
                Enterprise Caching Architecture & Rate Limiting
              </h1>
              <p className="text-slate-400 text-sm mt-1">
                Sub-millisecond data access, cache-aside read-through, atomic Lua rate limiting & tenant idempotency
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700 text-xs font-medium">
            <span
              className={`w-2.5 h-2.5 rounded-full ${redisConnected ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`}
            />
            <span>Backend: {backendType.toUpperCase()}</span>
          </div>
          <button
            onClick={handleFlushCache}
            className="flex items-center gap-2 px-3.5 py-1.5 bg-rose-900/40 hover:bg-rose-800/60 text-rose-300 border border-rose-700/50 rounded-lg text-sm font-semibold transition-all"
          >
            <Trash2 className="w-4 h-4" />
            Flush Cache
          </button>
          <button
            onClick={fetchHealthAndMetrics}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-semibold transition-all shadow-lg shadow-indigo-600/20"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-5 shadow-lg relative overflow-hidden">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-slate-400 text-xs uppercase font-bold tracking-wider">Cache Hit Ratio</p>
              <h2 className="text-3xl font-black mt-2 text-white">{(metrics.hit_ratio * 100).toFixed(1)}%</h2>
            </div>
            <div className="p-3 bg-emerald-500/10 text-emerald-400 rounded-xl border border-emerald-500/20">
              <Zap className="w-6 h-6" />
            </div>
          </div>
          <div className="w-full bg-slate-700/60 rounded-full h-2 mt-4 overflow-hidden">
            <div
              className="bg-emerald-400 h-2 rounded-full transition-all duration-500"
              style={{ width: `${Math.min(100, metrics.hit_ratio * 100)}%` }}
            />
          </div>
          <p className="text-slate-500 text-xs mt-2">Target SLO: &gt; 85% in production</p>
        </div>

        <div className="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-5 shadow-lg">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-slate-400 text-xs uppercase font-bold tracking-wider">Total Cache Hits</p>
              <h2 className="text-3xl font-black mt-2 text-emerald-400">{metrics.hits.toLocaleString()}</h2>
            </div>
            <div className="p-3 bg-indigo-500/10 text-indigo-400 rounded-xl border border-indigo-500/20">
              <CheckCircle2 className="w-6 h-6" />
            </div>
          </div>
          <p className="text-slate-400 text-xs mt-4">Direct memory &amp; Redis hits</p>
        </div>

        <div className="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-5 shadow-lg">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-slate-400 text-xs uppercase font-bold tracking-wider">Cache Misses</p>
              <h2 className="text-3xl font-black mt-2 text-amber-400">{metrics.misses.toLocaleString()}</h2>
            </div>
            <div className="p-3 bg-amber-500/10 text-amber-400 rounded-xl border border-amber-500/20">
              <AlertCircle className="w-6 h-6" />
            </div>
          </div>
          <p className="text-slate-400 text-xs mt-4">Database read-through lookups</p>
        </div>

        <div className="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-5 shadow-lg">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-slate-400 text-xs uppercase font-bold tracking-wider">Cached Keys</p>
              <h2 className="text-3xl font-black mt-2 text-cyan-400">{metrics.total_keys}</h2>
            </div>
            <div className="p-3 bg-cyan-500/10 text-cyan-400 rounded-xl border border-cyan-500/20">
              <Layers className="w-6 h-6" />
            </div>
          </div>
          <p className="text-slate-400 text-xs mt-4">Active unexpired keys</p>
        </div>
      </div>

      {/* Main Grid: Cache-Aside & Rate Limiter */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Card 1: Cache-Aside Customer Profile Simulator */}
        <div className="bg-slate-800/50 border border-slate-700/70 rounded-2xl p-6 shadow-xl space-y-6">
          <div className="flex items-center justify-between border-b border-slate-700/70 pb-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-indigo-500/20 text-indigo-400 rounded-lg">
                <Server className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-lg font-bold">Cache-Aside &amp; Invalidation Simulator</h2>
                <p className="text-slate-400 text-xs">Read-through profile lookup and explicit eviction on update</p>
              </div>
            </div>
            {profileFetchSource && (
              <span
                className={`text-xs px-2.5 py-1 rounded-full font-semibold border ${
                  profileFetchSource.includes('HIT')
                    ? 'bg-emerald-950/60 border-emerald-500 text-emerald-300'
                    : profileFetchSource.includes('INVALIDATED')
                    ? 'bg-rose-950/60 border-rose-500 text-rose-300'
                    : 'bg-amber-950/60 border-amber-500 text-amber-300'
                }`}
              >
                {profileFetchSource}
              </span>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-semibold text-slate-400 block mb-1">Target Customer ID</label>
              <select
                value={selectedCustomerId}
                onChange={(e) => setSelectedCustomerId(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
              >
                <option value="CUST-1001">CUST-1001 (Aarav Sharma)</option>
                <option value="CUST-1002">CUST-1002 (Priya Patel)</option>
                <option value="CUST-1003">CUST-1003 (Vikram Mehta)</option>
              </select>
            </div>
            <div className="flex items-end">
              <button
                onClick={handleFetchProfile}
                disabled={profileActionLoading}
                className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-semibold transition-all"
              >
                <RefreshCw className={`w-4 h-4 ${profileActionLoading ? 'animate-spin' : ''}`} />
                Fetch Profile (Read-Through)
              </button>
            </div>
          </div>

          {activeProfile && (
            <div className="bg-slate-900/80 border border-slate-700/80 rounded-xl p-4 space-y-3">
              <div className="flex justify-between items-center border-b border-slate-800 pb-2">
                <span className="text-xs font-bold text-slate-400">Customer Details</span>
                <span className="text-xs text-slate-500">Updated: {new Date(activeProfile.updated_at).toLocaleTimeString()}</span>
              </div>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <span className="text-xs text-slate-500 block">Name</span>
                  <span className="font-semibold text-slate-200">{activeProfile.name}</span>
                </div>
                <div>
                  <span className="text-xs text-slate-500 block">Risk Tier</span>
                  <span
                    className={`font-bold px-2 py-0.5 rounded text-xs ${
                      activeProfile.risk_tier === 'CRITICAL'
                        ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                        : activeProfile.risk_tier === 'HIGH'
                        ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                        : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    }`}
                  >
                    {activeProfile.risk_tier}
                  </span>
                </div>
                <div>
                  <span className="text-xs text-slate-500 block">KYC Status</span>
                  <span className="text-slate-300">{activeProfile.kyc_status}</span>
                </div>
                <div>
                  <span className="text-xs text-slate-500 block">Country</span>
                  <span className="text-slate-300">{activeProfile.country}</span>
                </div>
              </div>

              {/* Invalidation Trigger */}
              <div className="pt-3 border-t border-slate-800 flex items-center gap-3">
                <div className="flex-1">
                  <label className="text-xs font-semibold text-slate-400 block mb-1">Set New Risk Tier</label>
                  <select
                    value={newRiskTier}
                    onChange={(e) => setNewRiskTier(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200"
                  >
                    <option value="LOW">LOW</option>
                    <option value="MEDIUM">MEDIUM</option>
                    <option value="HIGH">HIGH</option>
                    <option value="CRITICAL">CRITICAL</option>
                  </select>
                </div>
                <div className="flex items-end">
                  <button
                    onClick={handleUpdateAndInvalidate}
                    disabled={profileActionLoading}
                    className="flex items-center gap-2 px-3 py-1.5 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-xs font-semibold transition-all mt-4"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    Update &amp; Invalidate Cache
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Card 2: Distributed Atomic Rate Limiter */}
        <div className="bg-slate-800/50 border border-slate-700/70 rounded-2xl p-6 shadow-xl space-y-6">
          <div className="flex items-center justify-between border-b border-slate-700/70 pb-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-amber-500/20 text-amber-400 rounded-lg">
                <Clock className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-lg font-bold">Distributed Rate Limiter (Lua Script)</h2>
                <p className="text-slate-400 text-xs">Atomic fixed-window rate limiter with Redis &amp; local memory fallback</p>
              </div>
            </div>
            {lastRateLimitResult && (
              <span
                className={`text-xs px-2.5 py-1 rounded-full font-bold border ${
                  lastRateLimitResult.allowed
                    ? 'bg-emerald-950/60 border-emerald-500 text-emerald-300'
                    : 'bg-rose-950/60 border-rose-500 text-rose-300 animate-pulse'
                }`}
              >
                {lastRateLimitResult.allowed ? 'ALLOWED (200 OK)' : 'THROTTLED (429)'}
              </span>
            )}
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="text-xs font-semibold text-slate-400 block mb-1">Client ID</label>
              <input
                type="text"
                value={rateLimitClient}
                onChange={(e) => setRateLimitClient(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-400 block mb-1">Max Quota</label>
              <input
                type="number"
                value={rateLimitMax}
                onChange={(e) => setRateLimitMax(Number(e.target.value))}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-400 block mb-1">Window (sec)</label>
              <input
                type="number"
                value={rateLimitWindow}
                onChange={(e) => setRateLimitWindow(Number(e.target.value))}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200"
              />
            </div>
          </div>

          <button
            onClick={handleSendRateLimitRequest}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-amber-600 to-amber-500 hover:from-amber-500 hover:to-amber-400 text-white rounded-lg text-sm font-bold shadow-lg shadow-amber-600/20 transition-all"
          >
            <Play className="w-4 h-4" />
            Send Test API Request
          </button>

          {lastRateLimitResult && (
            <div className="bg-slate-900/80 border border-slate-700/80 rounded-xl p-4 space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-400">Usage in Window:</span>
                <span className="font-bold text-slate-200">
                  {lastRateLimitResult.current_count} / {lastRateLimitResult.limit} requests
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Remaining Allowance:</span>
                <span className="font-bold text-emerald-400">{lastRateLimitResult.remaining} requests</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Window Reset In:</span>
                <span className="font-bold text-cyan-400">{lastRateLimitResult.reset_seconds}s</span>
              </div>
              {!lastRateLimitResult.allowed && (
                <div className="mt-2 p-2 bg-rose-500/10 border border-rose-500/30 rounded text-rose-300">
                  ⚠️ Request blocked. HTTP 429 Too Many Requests. Retry after {lastRateLimitResult.retry_after}s.
                </div>
              )}
            </div>
          )}

          {rateLimitLog.length > 0 && (
            <div className="space-y-1">
              <span className="text-xs font-bold text-slate-400">Recent Request Stream</span>
              <div className="space-y-1 max-h-32 overflow-y-auto">
                {rateLimitLog.map((log) => (
                  <div
                    key={log.id}
                    className="flex justify-between items-center px-3 py-1 bg-slate-900/60 rounded border border-slate-800 text-xs"
                  >
                    <span className="text-slate-500">{log.timestamp}</span>
                    <span className="text-slate-300">Req #{log.count}</span>
                    <span className={log.allowed ? 'text-emerald-400 font-semibold' : 'text-rose-400 font-bold'}>
                      {log.allowed ? '200 OK' : '429 Throttled'}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Row 2: Tenant-Scoped Idempotency & Enterprise Policies */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Card 3: Idempotency Replay Simulator */}
        <div className="bg-slate-800/50 border border-slate-700/70 rounded-2xl p-6 shadow-xl space-y-6">
          <div className="flex items-center justify-between border-b border-slate-700/70 pb-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-emerald-500/20 text-emerald-400 rounded-lg">
                <Repeat className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-lg font-bold">Tenant-Scoped Idempotency Layer</h2>
                <p className="text-slate-400 text-xs">SHA-256 hashed keys preventing duplicate payment settlements</p>
              </div>
            </div>
            {idemResult && (
              <span
                className={`text-xs px-2.5 py-1 rounded-full font-bold border ${
                  idemResult.is_replayed
                    ? 'bg-amber-950/60 border-amber-500 text-amber-300'
                    : 'bg-emerald-950/60 border-emerald-500 text-emerald-300'
                }`}
              >
                {idemResult.is_replayed ? 'REPLAYED FROM CACHE' : 'NEW OPERATION (COMPUTED)'}
              </span>
            )}
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="text-xs font-semibold text-slate-400 block mb-1">Tenant ID</label>
              <input
                type="text"
                value={idemTenantId}
                onChange={(e) => setIdemTenantId(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-400 block mb-1">Idempotency Key</label>
              <input
                type="text"
                value={idemKey}
                onChange={(e) => setIdemKey(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-400 block mb-1">Amount (INR)</label>
              <input
                type="number"
                value={idemAmount}
                onChange={(e) => setIdemAmount(Number(e.target.value))}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200"
              />
            </div>
          </div>

          <button
            onClick={handleExecuteIdempotentTx}
            disabled={idemLoading}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-emerald-600 to-emerald-500 hover:from-emerald-500 hover:to-emerald-400 text-white rounded-lg text-sm font-bold shadow-lg shadow-emerald-600/20 transition-all"
          >
            <Repeat className={`w-4 h-4 ${idemLoading ? 'animate-spin' : ''}`} />
            Submit Transaction with Idempotency Key
          </button>

          {idemResult && (
            <div className="bg-slate-900/80 border border-slate-700/80 rounded-xl p-4 space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-400">Key Hash (SHA-256):</span>
                <span className="font-mono text-cyan-300 text-[10px] truncate max-w-xs">{idemResult.key_hash}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Execution Status:</span>
                <span className="font-bold text-emerald-400">{idemResult.status}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Cached Decision:</span>
                <span className="font-bold text-slate-200">{idemResult.response_payload?.decision}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Risk Score:</span>
                <span className="font-bold text-slate-200">{idemResult.response_payload?.risk_score}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Expires At:</span>
                <span className="text-slate-400">{new Date(idemResult.expires_at).toLocaleTimeString()}</span>
              </div>
            </div>
          )}
        </div>

        {/* Card 4: Enterprise Cache Policies Table */}
        <div className="bg-slate-800/50 border border-slate-700/70 rounded-2xl p-6 shadow-xl space-y-4">
          <div className="flex items-center gap-3 border-b border-slate-700/70 pb-4">
            <div className="p-2 bg-cyan-500/20 text-cyan-400 rounded-lg">
              <Layers className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold">Standard Enterprise Cache Policies</h2>
              <p className="text-slate-400 text-xs">TTL policies and invalidation triggers configured across FinGuard AI</p>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-900/70 text-slate-400 uppercase font-semibold">
                <tr>
                  <th className="py-2.5 px-3">Data Classification</th>
                  <th className="py-2.5 px-3">TTL</th>
                  <th className="py-2.5 px-3">Invalidation Trigger</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {policies.map((p, idx) => (
                  <tr key={idx} className="hover:bg-slate-800/60">
                    <td className="py-2.5 px-3 font-semibold text-slate-200">{p.data_type}</td>
                    <td className="py-2.5 px-3">
                      <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-cyan-300 font-mono">
                        {p.ttl_display}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-slate-400">{p.invalidation_trigger}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CachingArchitecturePage;

