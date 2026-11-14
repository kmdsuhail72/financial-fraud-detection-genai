import React, { useState, useEffect } from 'react';
import {
  Layers,
  Building2,
  CreditCard,
  Webhook,
  ShieldCheck,
  AlertOctagon,
  RefreshCw,
  Search,
  Filter,
  CheckCircle2,
  XCircle,
  Copy,
  Clock,
  History,
  Send,
  PlusCircle,
  Info,
  ArrowRight,
  TrendingUp,
  FileCode,
  Terminal
} from 'lucide-react';

interface CanonicalEvent {
  event_id: string;
  idempotency_key: string;
  source: 'CORE_BANKING' | 'PAYMENT_GATEWAY' | 'EXTERNAL_KYC' | 'EXTERNAL_AML' | 'WEBHOOK' | 'GENERIC';
  event_type: string;
  customer_id?: string;
  account_id?: string;
  amount?: number;
  currency: string;
  status: 'PROCESSED' | 'DUPLICATE' | 'FAILED' | 'DEAD_LETTER';
  received_at: string;
  raw_payload: Record<string, any>;
  normalized_payload: Record<string, any>;
  retry_count: number;
}

interface DeadLetterEvent {
  dlq_id: string;
  original_event_id?: string;
  source: string;
  payload: Record<string, any>;
  failure_reason: string;
  retry_attempts: number;
  failed_at: string;
}

interface IntegrationAuditEntry {
  audit_id: string;
  event_id?: string;
  action: string;
  source: string;
  details: Record<string, any>;
  timestamp: string;
}

interface IntegrationMetrics {
  total_events_received: number;
  processed_count: number;
  duplicate_count: number;
  dead_letter_count: number;
  cbs_events_count: number;
  gateway_events_count: number;
  webhook_events_count: number;
  success_rate_percent: number;
}

const DEMO_EVENTS: CanonicalEvent[] = [
  {
    event_id: 'EVT-CBS-BENCHMARK-01',
    idempotency_key: 'cbs:TXN-CBS-992014',
    source: 'CORE_BANKING',
    event_type: 'TRANSACTION_POSTED',
    customer_id: 'CIF-990142',
    account_id: 'ACC-HDFC-991203',
    amount: 450000.0,
    currency: 'INR',
    status: 'PROCESSED',
    received_at: new Date(Date.now() - 1000 * 60 * 10).toISOString(),
    raw_payload: {
      cbs_txn_id: 'TXN-CBS-992014',
      account_number: 'ACC-HDFC-991203',
      customer_cif: 'CIF-990142',
      amount: 450000.0,
      txn_type: 'DEBIT',
      channel: 'NETBANKING'
    },
    normalized_payload: {
      cbs_transaction_id: 'TXN-CBS-992014',
      account_id: 'ACC-HDFC-991203',
      customer_id: 'CIF-990142',
      amount: 450000.0,
      currency: 'INR',
      transaction_type: 'DEBIT',
      channel: 'NETBANKING'
    },
    retry_count: 0
  },
  {
    event_id: 'EVT-GW-BENCHMARK-02',
    idempotency_key: 'gateway:razorpay:pay_rzp_990148',
    source: 'PAYMENT_GATEWAY',
    event_type: 'PAYMENT_CAPTURED',
    customer_id: 'customer.alex@example.com',
    account_id: 'order_990148',
    amount: 125000.0,
    currency: 'INR',
    status: 'PROCESSED',
    received_at: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
    raw_payload: {
      gateway_payment_id: 'pay_rzp_990148',
      order_id: 'order_990148',
      gateway_provider: 'RAZORPAY',
      event_name: 'payment.captured',
      amount: 125000.0
    },
    normalized_payload: {
      gateway_payment_id: 'pay_rzp_990148',
      order_id: 'order_990148',
      provider: 'RAZORPAY',
      amount: 125000.0
    },
    retry_count: 0
  }
];

export const DataIntegrationsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'STREAM' | 'DLQ' | 'AUDIT'>('STREAM');
  const [events, setEvents] = useState<CanonicalEvent[]>(DEMO_EVENTS);
  const [selectedEvent, setSelectedEvent] = useState<CanonicalEvent>(DEMO_EVENTS[0]);
  const [deadLetters, setDeadLetters] = useState<DeadLetterEvent[]>([]);
  const [auditEntries, setAuditEntries] = useState<IntegrationAuditEntry[]>([]);
  const [metrics, setMetrics] = useState<IntegrationMetrics>({
    total_events_received: 2,
    processed_count: 2,
    duplicate_count: 0,
    dead_letter_count: 0,
    cbs_events_count: 1,
    gateway_events_count: 1,
    webhook_events_count: 0,
    success_rate_percent: 100.0
  });

  const [searchTerm, setSearchTerm] = useState('');
  const [sourceFilter, setSourceFilter] = useState('ALL');
  const [loading, setLoading] = useState(false);
  const [isSimulateModalOpen, setIsSimulateModalOpen] = useState(false);

  // Ingestion simulation state
  const [simType, setSimType] = useState<'CBS' | 'GATEWAY'>('CBS');
  const [cbsForm, setCbsForm] = useState({
    cbs_txn_id: `CBS-TXN-${Date.now().toString().slice(-6)}`,
    account_number: 'ACC-HDFC-991203',
    customer_cif: 'CIF-IND-40291',
    amount: 350000,
    currency: 'INR',
    txn_type: 'DEBIT',
    channel: 'NETBANKING'
  });

  const [gatewayForm, setGatewayForm] = useState({
    gateway_payment_id: `pay_rzp_${Date.now().toString().slice(-6)}`,
    order_id: `order_${Date.now().toString().slice(-6)}`,
    gateway_provider: 'RAZORPAY',
    amount: 285000,
    currency: 'INR',
    customer_email: 'jordan.cross@enterprise.internal',
    payment_method: 'upi'
  });

  const fetchData = async () => {
    try {
      setLoading(true);
      const evRes = await fetch('http://127.0.0.1:8011/integrations/events');
      if (evRes.ok) {
        const evData = await evRes.json();
        if (evData && evData.length > 0) {
          setEvents(evData);
          setSelectedEvent(evData[0]);
        }
      }

      const dlqRes = await fetch('http://127.0.0.1:8011/integrations/dead-letters');
      if (dlqRes.ok) {
        const dlqData = await dlqRes.json();
        setDeadLetters(dlqData);
      }

      const audRes = await fetch('http://127.0.0.1:8011/integrations/audit');
      if (audRes.ok) {
        const audData = await audRes.json();
        setAuditEntries(audData);
      }

      const metRes = await fetch('http://127.0.0.1:8011/integrations/metrics');
      if (metRes.ok) {
        const metData = await metRes.json();
        setMetrics(metData);
      }
    } catch {
      // Fallback to in-memory state
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleSimulateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      let endpoint = 'http://127.0.0.1:8011/integrations/core-banking/events';
      let payload: any = cbsForm;
      if (simType === 'GATEWAY') {
        endpoint = 'http://127.0.0.1:8011/integrations/payment-gateway/events';
        payload = gatewayForm;
      }

      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        const data = await res.json();
        setEvents((prev) => [data, ...prev]);
        setSelectedEvent(data);
        setIsSimulateModalOpen(false);
        fetchData();
      }
    } catch {
      // Local fallback simulation
      const fallbackEv: CanonicalEvent = {
        event_id: `EVT-${simType}-${Date.now().toString().slice(-6)}`,
        idempotency_key: `${simType.toLowerCase()}:${Date.now()}`,
        source: simType === 'CBS' ? 'CORE_BANKING' : 'PAYMENT_GATEWAY',
        event_type: simType === 'CBS' ? 'TRANSACTION_POSTED' : 'PAYMENT_CAPTURED',
        customer_id: simType === 'CBS' ? cbsForm.customer_cif : gatewayForm.customer_email,
        amount: simType === 'CBS' ? cbsForm.amount : gatewayForm.amount,
        currency: 'INR',
        status: 'PROCESSED',
        received_at: new Date().toISOString(),
        raw_payload: simType === 'CBS' ? cbsForm : gatewayForm,
        normalized_payload: simType === 'CBS' ? cbsForm : gatewayForm,
        retry_count: 0
      };
      setEvents((prev) => [fallbackEv, ...prev]);
      setSelectedEvent(fallbackEv);
      setIsSimulateModalOpen(false);
    }
  };

  const getSourceBadge = (source: string) => {
    switch (source) {
      case 'CORE_BANKING':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 flex items-center gap-1">
            <Building2 className="w-3 h-3" /> CBS
          </span>
        );
      case 'PAYMENT_GATEWAY':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
            <CreditCard className="w-3 h-3" /> GATEWAY
          </span>
        );
      case 'WEBHOOK':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30 flex items-center gap-1">
            <Webhook className="w-3 h-3" /> WEBHOOK
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-slate-300 border border-slate-700">
            {source}
          </span>
        );
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'PROCESSED':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
            PROCESSED
          </span>
        );
      case 'DUPLICATE':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30">
            DUPLICATE
          </span>
        );
      case 'DEAD_LETTER':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-red-500/20 text-red-300 border border-red-500/30">
            DEAD LETTER
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-slate-400">
            {status}
          </span>
        );
    }
  };

  const filteredEvents = events.filter((e) => {
    const matchesSearch =
      e.event_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      e.idempotency_key.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (e.customer_id && e.customer_id.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (e.account_id && e.account_id.toLowerCase().includes(searchTerm.toLowerCase()));
    const matchesSource = sourceFilter === 'ALL' || e.source === sourceFilter;
    return matchesSearch && matchesSource;
  });

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-emerald-600/20 border border-emerald-500/30 rounded-xl">
              <Layers className="w-6 h-6 text-emerald-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
                Enterprise Data Integration & Banking APIs
                <span className="text-xs font-medium px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                  Phase 31
                </span>
              </h1>
              <p className="text-sm text-slate-400">
                Core Banking (CBS), Payment Gateways, HMAC Webhooks, Canonical Normalization, Idempotency & Dead-Letter Queue
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => fetchData()}
            disabled={loading}
            className="px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-sm font-medium transition flex items-center gap-2 text-slate-300"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button
            onClick={() => setIsSimulateModalOpen(true)}
            className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-semibold transition flex items-center gap-2 shadow-lg shadow-emerald-600/20"
          >
            <PlusCircle className="w-4 h-4" />
            Simulate Ingestion
          </button>
        </div>
      </div>

      {/* Advisory Banner */}
      <div className="bg-slate-900/60 border border-emerald-900/40 rounded-xl p-4 flex items-start gap-3">
        <Info className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
        <div className="text-xs text-slate-300 leading-relaxed">
          <span className="font-semibold text-emerald-300">Enterprise Integration Architecture:</span> The ingestion layer guarantees deduplication via unique idempotency keys, validates HMAC-SHA256 signatures for external callbacks, executes bounded exponential retries, and captures irrecoverable payloads in a Dead-Letter Queue (DLQ).
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3.5">
          <div className="text-xs font-medium text-slate-400">Total Received</div>
          <div className="text-2xl font-bold text-white mt-1">{metrics.total_events_received}</div>
          <div className="text-[11px] text-slate-500 mt-1">Ingested events</div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3.5">
          <div className="text-xs font-medium text-emerald-400">Processed</div>
          <div className="text-2xl font-bold text-emerald-400 mt-1">{metrics.processed_count}</div>
          <div className="text-[11px] text-slate-500 mt-1">Canonical normalized</div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3.5">
          <div className="text-xs font-medium text-purple-400">Deduplicated</div>
          <div className="text-2xl font-bold text-purple-400 mt-1">{metrics.duplicate_count}</div>
          <div className="text-[11px] text-slate-500 mt-1">Idempotency hits</div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3.5">
          <div className="text-xs font-medium text-red-400">Dead Letters (DLQ)</div>
          <div className="text-2xl font-bold text-red-400 mt-1">{metrics.dead_letter_count}</div>
          <div className="text-[11px] text-slate-500 mt-1">Exhausted retries</div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3.5">
          <div className="text-xs font-medium text-indigo-400">CBS Connectors</div>
          <div className="text-2xl font-bold text-indigo-400 mt-1">{metrics.cbs_events_count}</div>
          <div className="text-[11px] text-slate-500 mt-1">Account postings</div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3.5">
          <div className="text-xs font-medium text-teal-400">Success Rate</div>
          <div className="text-2xl font-bold text-teal-400 mt-1">{metrics.success_rate_percent}%</div>
          <div className="text-[11px] text-slate-500 mt-1">Pipeline reliability</div>
        </div>
      </div>

      {/* View Tabs */}
      <div className="flex border-b border-slate-800 gap-6 text-sm font-semibold">
        <button
          onClick={() => setActiveTab('STREAM')}
          className={`pb-3 transition flex items-center gap-2 ${activeTab === 'STREAM'
              ? 'text-emerald-400 border-b-2 border-emerald-400'
              : 'text-slate-400 hover:text-slate-200'
            }`}
        >
          <Terminal className="w-4 h-4" />
          Canonical Event Stream ({events.length})
        </button>

        <button
          onClick={() => setActiveTab('DLQ')}
          className={`pb-3 transition flex items-center gap-2 ${activeTab === 'DLQ'
              ? 'text-red-400 border-b-2 border-red-400'
              : 'text-slate-400 hover:text-slate-200'
            }`}
        >
          <AlertOctagon className="w-4 h-4" />
          Dead-Letter Queue ({deadLetters.length})
        </button>

        <button
          onClick={() => setActiveTab('AUDIT')}
          className={`pb-3 transition flex items-center gap-2 ${activeTab === 'AUDIT'
              ? 'text-blue-400 border-b-2 border-blue-400'
              : 'text-slate-400 hover:text-slate-200'
            }`}
        >
          <History className="w-4 h-4" />
          Integration Audit Trail ({auditEntries.length})
        </button>
      </div>

      {/* Main Tab Content */}
      {activeTab === 'STREAM' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Stream List (7 cols) */}
          <div className="lg:col-span-7 space-y-4">
            {/* Filter Bar */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3 flex flex-wrap items-center justify-between gap-3">
              <div className="relative flex-1 min-w-[200px]">
                <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-500" />
                <input
                  type="text"
                  placeholder="Search by Event ID, Customer, Account, Key..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-9 pr-3 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                />
              </div>
              <div className="flex items-center gap-2">
                <select
                  value={sourceFilter}
                  onChange={(e) => setSourceFilter(e.target.value)}
                  className="bg-slate-950 border border-slate-800 text-xs text-slate-300 rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-emerald-500"
                >
                  <option value="ALL">All Sources</option>
                  <option value="CORE_BANKING">Core Banking</option>
                  <option value="PAYMENT_GATEWAY">Payment Gateway</option>
                  <option value="WEBHOOK">Webhook</option>
                  <option value="GENERIC">Generic</option>
                </select>
              </div>
            </div>

            {/* List */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
              <div className="px-4 py-3 border-b border-slate-800 flex items-center justify-between">
                <div className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                  Live Ingested Stream ({filteredEvents.length})
                </div>
                <div className="text-xs text-slate-500">Idempotency-verified canonical events</div>
              </div>

              <div className="divide-y divide-slate-800/60 max-h-[580px] overflow-y-auto">
                {filteredEvents.length === 0 ? (
                  <div className="p-8 text-center text-slate-500 text-sm">
                    No canonical events matched filters.
                  </div>
                ) : (
                  filteredEvents.map((ev) => {
                    const isSelected = selectedEvent?.event_id === ev.event_id;
                    return (
                      <div
                        key={ev.event_id}
                        onClick={() => setSelectedEvent(ev)}
                        className={`p-4 transition cursor-pointer flex items-center justify-between gap-4 hover:bg-slate-800/40 ${isSelected ? 'bg-emerald-950/30 border-l-4 border-emerald-500' : ''
                          }`}
                      >
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-sm font-bold text-white">
                              {ev.event_id}
                            </span>
                            {getSourceBadge(ev.source)}
                            {getStatusBadge(ev.status)}
                          </div>
                          <div className="text-xs text-slate-300">
                            Type: <span className="font-mono text-slate-200">{ev.event_type}</span>
                          </div>
                          <div className="text-[11px] text-slate-400 font-mono">
                            Key: {ev.idempotency_key}
                          </div>
                        </div>

                        <div className="text-right space-y-1">
                          {ev.amount !== undefined && ev.amount !== null && (
                            <div className="text-sm font-bold text-white">
                              ₹{ev.amount.toLocaleString()}
                            </div>
                          )}
                          <div className="text-[11px] text-slate-500">
                            {new Date(ev.received_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          </div>

          {/* Right Column: Event Inspection & Payload (5 cols) */}
          <div className="lg:col-span-5 space-y-4">
            {selectedEvent ? (
              <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-5">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <div>
                    <div className="text-xs uppercase tracking-wider text-slate-400 font-medium">
                      Canonical Event Details
                    </div>
                    <div className="text-lg font-bold text-white font-mono mt-0.5">
                      {selectedEvent.event_id}
                    </div>
                  </div>
                  {getStatusBadge(selectedEvent.status)}
                </div>

                {/* Event Properties */}
                <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-4 space-y-2 text-xs">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Event Source:</span>
                    <span className="font-semibold text-slate-200">{selectedEvent.source}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Event Type:</span>
                    <span className="font-mono text-slate-200">{selectedEvent.event_type}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Idempotency Key:</span>
                    <span className="font-mono text-emerald-400">{selectedEvent.idempotency_key}</span>
                  </div>
                  {selectedEvent.customer_id && (
                    <div className="flex justify-between">
                      <span className="text-slate-400">Customer ID:</span>
                      <span className="font-mono text-slate-300">{selectedEvent.customer_id}</span>
                    </div>
                  )}
                  {selectedEvent.amount !== undefined && selectedEvent.amount !== null && (
                    <div className="flex justify-between pt-1 border-t border-slate-800">
                      <span className="text-slate-400">Amount:</span>
                      <span className="font-bold text-emerald-400">
                        ₹{selectedEvent.amount.toLocaleString()} {selectedEvent.currency}
                      </span>
                    </div>
                  )}
                </div>

                {/* Normalized Payload JSON */}
                <div className="space-y-1.5">
                  <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                    <FileCode className="w-3.5 h-3.5 text-emerald-400" />
                    Normalized Canonical Payload
                  </div>
                  <pre className="p-3 bg-slate-950 border border-slate-800 rounded-lg text-[11px] font-mono text-emerald-300 max-h-48 overflow-y-auto leading-relaxed">
                    {JSON.stringify(selectedEvent.normalized_payload, null, 2)}
                  </pre>
                </div>

                {/* Raw Ingestion Payload JSON */}
                <div className="space-y-1.5">
                  <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                    <Terminal className="w-3.5 h-3.5 text-blue-400" />
                    Raw Ingestion Payload
                  </div>
                  <pre className="p-3 bg-slate-950 border border-slate-800 rounded-lg text-[11px] font-mono text-slate-300 max-h-36 overflow-y-auto leading-relaxed">
                    {JSON.stringify(selectedEvent.raw_payload, null, 2)}
                  </pre>
                </div>
              </div>
            ) : (
              <div className="p-8 text-center text-slate-500 bg-slate-900/40 rounded-xl border border-slate-800">
                Select an event to inspect canonical structure.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Dead Letter Queue (DLQ) Tab */}
      {activeTab === 'DLQ' && (
        <div className="space-y-4">
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
            <div className="px-4 py-3 border-b border-slate-800 flex items-center justify-between">
              <div className="text-xs font-semibold text-red-400 uppercase tracking-wider flex items-center gap-2">
                <AlertOctagon className="w-4 h-4" />
                Dead-Letter Queue (DLQ) Register ({deadLetters.length})
              </div>
              <div className="text-xs text-slate-500">Failed payloads isolated for inspection</div>
            </div>

            <div className="divide-y divide-slate-800/60">
              {deadLetters.length === 0 ? (
                <div className="p-12 text-center text-slate-500 text-sm">
                  <ShieldCheck className="w-8 h-8 text-emerald-500 mx-auto mb-2 opacity-60" />
                  No failed events in Dead-Letter Queue. Pipeline operating normally.
                </div>
              ) : (
                deadLetters.map((dlq) => (
                  <div key={dlq.dlq_id} className="p-4 space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-sm font-bold text-red-400">{dlq.dlq_id}</span>
                        <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                          Source: {dlq.source}
                        </span>
                        <span className="text-xs px-2 py-0.5 rounded bg-red-950/60 text-red-300 border border-red-800/60">
                          Attempts: {dlq.retry_attempts}
                        </span>
                      </div>
                      <span className="text-xs text-slate-500">
                        {new Date(dlq.failed_at).toLocaleTimeString()}
                      </span>
                    </div>

                    <div className="text-xs text-slate-300">
                      Reason: <span className="font-semibold text-rose-300">{dlq.failure_reason}</span>
                    </div>

                    <pre className="p-3 bg-slate-950 border border-slate-800 rounded-lg text-[11px] font-mono text-slate-400 max-h-32 overflow-y-auto">
                      {JSON.stringify(dlq.payload, null, 2)}
                    </pre>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* Integration Audit Trail Tab */}
      {activeTab === 'AUDIT' && (
        <div className="space-y-4">
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
            <div className="px-4 py-3 border-b border-slate-800 flex items-center justify-between">
              <div className="text-xs font-semibold text-blue-400 uppercase tracking-wider flex items-center gap-2">
                <History className="w-4 h-4" />
                Integration Audit Ledger ({auditEntries.length})
              </div>
              <div className="text-xs text-slate-500">Immutable trace of connector operations</div>
            </div>

            <div className="divide-y divide-slate-800/60">
              {auditEntries.map((a) => (
                <div key={a.audit_id} className="p-4 flex items-center justify-between gap-4">
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-semibold text-slate-400">{a.audit_id}</span>
                      <span className="font-bold text-xs text-white">{a.action}</span>
                      <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                        {a.source}
                      </span>
                    </div>
                    {a.event_id && (
                      <div className="text-xs font-mono text-slate-400">
                        Event: <span className="text-slate-300">{a.event_id}</span>
                      </div>
                    )}
                  </div>
                  <div className="text-xs text-slate-500 font-mono">
                    {new Date(a.timestamp).toLocaleTimeString()}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Ingestion Simulation Modal */}
      {isSimulateModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <Layers className="w-5 h-5 text-emerald-400" />
                Simulate Data Ingestion
              </h2>
              <button
                onClick={() => setIsSimulateModalOpen(false)}
                className="text-slate-400 hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            {/* Ingestion Type Selection */}
            <div className="grid grid-cols-2 gap-2 text-xs">
              <button
                type="button"
                onClick={() => setSimType('CBS')}
                className={`py-2 px-3 rounded-lg font-semibold flex items-center justify-center gap-2 border transition ${simType === 'CBS'
                    ? 'bg-indigo-600 text-white border-indigo-500'
                    : 'bg-slate-950 text-slate-400 border-slate-800 hover:text-white'
                  }`}
              >
                <Building2 className="w-3.5 h-3.5" /> Core Banking (CBS)
              </button>

              <button
                type="button"
                onClick={() => setSimType('GATEWAY')}
                className={`py-2 px-3 rounded-lg font-semibold flex items-center justify-center gap-2 border transition ${simType === 'GATEWAY'
                    ? 'bg-emerald-600 text-white border-emerald-500'
                    : 'bg-slate-950 text-slate-400 border-slate-800 hover:text-white'
                  }`}
              >
                <CreditCard className="w-3.5 h-3.5" /> Payment Gateway
              </button>
            </div>

            <form onSubmit={handleSimulateSubmit} className="space-y-3 text-xs">
              {simType === 'CBS' ? (
                <>
                  <div>
                    <label className="text-slate-400 block mb-1">CBS Transaction ID</label>
                    <input
                      type="text"
                      required
                      value={cbsForm.cbs_txn_id}
                      onChange={(e) => setCbsForm({ ...cbsForm, cbs_txn_id: e.target.value })}
                      className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 font-mono"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-slate-400 block mb-1">Customer CIF</label>
                      <input
                        type="text"
                        required
                        value={cbsForm.customer_cif}
                        onChange={(e) => setCbsForm({ ...cbsForm, customer_cif: e.target.value })}
                        className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200"
                      />
                    </div>
                    <div>
                      <label className="text-slate-400 block mb-1">Account Number</label>
                      <input
                        type="text"
                        required
                        value={cbsForm.account_number}
                        onChange={(e) => setCbsForm({ ...cbsForm, account_number: e.target.value })}
                        className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 font-mono"
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-slate-400 block mb-1">Amount (₹)</label>
                      <input
                        type="number"
                        min="1"
                        required
                        value={cbsForm.amount}
                        onChange={(e) => setCbsForm({ ...cbsForm, amount: Number(e.target.value) })}
                        className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 font-mono"
                      />
                    </div>
                    <div>
                      <label className="text-slate-400 block mb-1">Channel</label>
                      <select
                        value={cbsForm.channel}
                        onChange={(e) => setCbsForm({ ...cbsForm, channel: e.target.value })}
                        className="w-full px-2 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200"
                      >
                        <option value="NETBANKING">NETBANKING</option>
                        <option value="UPI">UPI</option>
                        <option value="ATM">ATM</option>
                        <option value="BRANCH">BRANCH</option>
                      </select>
                    </div>
                  </div>
                </>
              ) : (
                <>
                  <div>
                    <label className="text-slate-400 block mb-1">Gateway Payment ID</label>
                    <input
                      type="text"
                      required
                      value={gatewayForm.gateway_payment_id}
                      onChange={(e) => setGatewayForm({ ...gatewayForm, gateway_payment_id: e.target.value })}
                      className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 font-mono"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-slate-400 block mb-1">Order ID</label>
                      <input
                        type="text"
                        required
                        value={gatewayForm.order_id}
                        onChange={(e) => setGatewayForm({ ...gatewayForm, order_id: e.target.value })}
                        className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 font-mono"
                      />
                    </div>
                    <div>
                      <label className="text-slate-400 block mb-1">Customer Email</label>
                      <input
                        type="email"
                        required
                        value={gatewayForm.customer_email}
                        onChange={(e) => setGatewayForm({ ...gatewayForm, customer_email: e.target.value })}
                        className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200"
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-slate-400 block mb-1">Amount (₹)</label>
                      <input
                        type="number"
                        min="1"
                        required
                        value={gatewayForm.amount}
                        onChange={(e) => setGatewayForm({ ...gatewayForm, amount: Number(e.target.value) })}
                        className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 font-mono"
                      />
                    </div>
                    <div>
                      <label className="text-slate-400 block mb-1">Payment Method</label>
                      <select
                        value={gatewayForm.payment_method}
                        onChange={(e) => setGatewayForm({ ...gatewayForm, payment_method: e.target.value })}
                        className="w-full px-2 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200"
                      >
                        <option value="upi">UPI</option>
                        <option value="card">Card</option>
                        <option value="netbanking">Net Banking</option>
                      </select>
                    </div>
                  </div>
                </>
              )}

              <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsSimulateModalOpen(false)}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 font-semibold text-white shadow-lg shadow-emerald-600/20"
                >
                  Ingest Event
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default DataIntegrationsPage;

