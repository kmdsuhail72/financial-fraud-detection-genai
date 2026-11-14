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
  GitBranch,
  Layers,
  ListRestart,
  MessageSquare,
  Play,
  Radio,
  RefreshCw,
  Repeat,
  Send,
  Server,
  ShieldAlert,
  Trash2,
  Zap,
} from 'lucide-react';
import axios from 'axios';

interface DeadLetterMessage {
  message_id: string;
  original_queue: string;
  payload: any;
  failure_reason: string;
  receive_count: number;
  quarantined_at: string;
}

interface MessagingMetrics {
  total_published: number;
  total_processed: number;
  total_retried: number;
  dlq_count: number;
  queues: Record<string, { pending: number; in_flight: number; is_fifo: boolean }>;
  sns: { topic_name: string; subscribers: number; published_count: number };
  eventbridge: { bus_name: string; rules_count: number; routed_count: number };
  kafka: {
    topic: string;
    num_partitions: number;
    total_records: number;
    partition_sizes: Record<string, number>;
  };
}

export const EventStreamingPage: React.FC = () => {
  const [loading, setLoading] = useState<boolean>(true);
  const [metrics, setMetrics] = useState<MessagingMetrics | null>(null);
  const [dlqMessages, setDlqMessages] = useState<DeadLetterMessage[]>([]);

  // Publisher State
  const [txId, setTxId] = useState<string>(`TX-${Math.floor(100000 + Math.random() * 900000)}`);
  const [amount, setAmount] = useState<number>(125000);
  const [rail, setRail] = useState<string>('UPI');
  const [publishResult, setPublishResult] = useState<any | null>(null);
  const [publishing, setPublishing] = useState<boolean>(false);

  // Consumer Simulator State
  const [selectedQueue, setSelectedQueue] = useState<string>('fraud');
  const [simulateFailure, setSimulateFailure] = useState<boolean>(false);
  const [consumerResult, setConsumerResult] = useState<any | null>(null);
  const [consuming, setConsuming] = useState<boolean>(false);

  const fetchMetricsAndDLQ = async () => {
    try {
      setLoading(true);
      const [mRes, dlqRes] = await Promise.all([
        axios.get('/api/v1/messaging/metrics'),
        axios.get('/api/v1/messaging/dlq/messages'),
      ]);
      setMetrics(mRes.data);
      setDlqMessages(dlqRes.data || []);
    } catch (err) {
      console.error('Failed to load messaging metrics:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetricsAndDLQ();
    const interval = setInterval(fetchMetricsAndDLQ, 6000);
    return () => clearInterval(interval);
  }, []);

  // Handle Event Publish
  const handlePublishEvent = async () => {
    setPublishing(true);
    try {
      const res = await axios.post('/api/v1/messaging/publish/transaction', {
        transaction_id: txId,
        tenant_id: 'tenant-hdfc-01',
        customer_id: 'CUST-1001',
        amount: Number(amount),
        currency: 'INR',
        payment_rail: rail,
        risk_score: amount >= 100000 ? 0.82 : 0.15,
      });
      setPublishResult(res.data);
      setTxId(`TX-${Math.floor(100000 + Math.random() * 900000)}`);
      fetchMetricsAndDLQ();
    } catch (err: any) {
      console.error('Publish error:', err);
      alert('Failed to publish event');
    } finally {
      setPublishing(false);
    }
  };

  // Handle Queue Processing
  const handleProcessQueueMessage = async () => {
    setConsuming(true);
    try {
      const res = await axios.post(`/api/v1/messaging/queues/${selectedQueue}/process?simulate_failure=${simulateFailure}`);
      setConsumerResult(res.data);
      fetchMetricsAndDLQ();
    } catch (err: any) {
      console.error('Process error:', err);
    } finally {
      setConsuming(false);
    }
  };

  // Handle DLQ Replay
  const handleReplayDLQ = async (messageId: string, targetQueue: string) => {
    try {
      await axios.post('/api/v1/messaging/dlq/replay', {
        message_id: messageId,
        target_queue_key: targetQueue,
      });
      fetchMetricsAndDLQ();
      alert(`Message ${messageId} replayed back to queue '${targetQueue}'`);
    } catch (err: any) {
      console.error('Replay error:', err);
      alert('Failed to replay DLQ message');
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 p-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-slate-800 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-3 bg-purple-600/20 text-purple-400 rounded-xl border border-purple-500/30">
              <Radio className="w-8 h-8" />
            </div>
            <div>
              <h1 className="text-3xl font-extrabold tracking-tight">
                Enterprise Message Queues &amp; Event Streaming
              </h1>
              <p className="text-slate-400 text-sm mt-1">
                Amazon SQS Standard/FIFO, SNS 1-to-N Fan-Out, EventBridge Content Routing, Kafka Streams &amp; DLQ Replay
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700 text-xs font-medium">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
            <span>Delivery: AT-LEAST-ONCE (Idempotent)</span>
          </div>
          <button
            onClick={fetchMetricsAndDLQ}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-semibold transition-all shadow-lg shadow-indigo-600/20"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Metrics Row */}
      {metrics && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-5 shadow-lg">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-slate-400 text-xs uppercase font-bold tracking-wider">Total Published</p>
                <h2 className="text-3xl font-black mt-2 text-white">{metrics.total_published}</h2>
              </div>
              <div className="p-3 bg-indigo-500/10 text-indigo-400 rounded-xl border border-indigo-500/20">
                <Send className="w-6 h-6" />
              </div>
            </div>
            <p className="text-slate-500 text-xs mt-4">SNS &amp; EventBridge Events</p>
          </div>

          <div className="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-5 shadow-lg">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-slate-400 text-xs uppercase font-bold tracking-wider">Processed Messages</p>
                <h2 className="text-3xl font-black mt-2 text-emerald-400">{metrics.total_processed}</h2>
              </div>
              <div className="p-3 bg-emerald-500/10 text-emerald-400 rounded-xl border border-emerald-500/20">
                <CheckCircle2 className="w-6 h-6" />
              </div>
            </div>
            <p className="text-slate-500 text-xs mt-4">Acknowledged across queues</p>
          </div>

          <div className="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-5 shadow-lg">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-slate-400 text-xs uppercase font-bold tracking-wider">Retried / NACKed</p>
                <h2 className="text-3xl font-black mt-2 text-amber-400">{metrics.total_retried}</h2>
              </div>
              <div className="p-3 bg-amber-500/10 text-amber-400 rounded-xl border border-amber-500/20">
                <Repeat className="w-6 h-6" />
              </div>
            </div>
            <p className="text-slate-500 text-xs mt-4">Simulated/Transient retries</p>
          </div>

          <div
            className={`border rounded-2xl p-5 shadow-lg ${
              metrics.dlq_count > 0
                ? 'bg-rose-950/40 border-rose-600/60'
                : 'bg-slate-800/60 border-slate-700/60'
            }`}
          >
            <div className="flex justify-between items-start">
              <div>
                <p className="text-slate-400 text-xs uppercase font-bold tracking-wider">Dead-Letter Queue (DLQ)</p>
                <h2 className={`text-3xl font-black mt-2 ${metrics.dlq_count > 0 ? 'text-rose-400 animate-pulse' : 'text-slate-300'}`}>
                  {metrics.dlq_count}
                </h2>
              </div>
              <div className="p-3 bg-rose-500/10 text-rose-400 rounded-xl border border-rose-500/20">
                <ShieldAlert className="w-6 h-6" />
              </div>
            </div>
            <p className="text-slate-500 text-xs mt-4">Quarantined after 3 attempts</p>
          </div>
        </div>
      )}

      {/* Row 2: Event Publisher & Queue Consumer */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Card 1: Event Ingestion & Fanout Publisher */}
        <div className="bg-slate-800/50 border border-slate-700/70 rounded-2xl p-6 shadow-xl space-y-6">
          <div className="flex items-center justify-between border-b border-slate-700/70 pb-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-indigo-500/20 text-indigo-400 rounded-lg">
                <Send className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-lg font-bold">Transaction Event Ingestion</h2>
                <p className="text-slate-400 text-xs">Publish to SNS Fanout, EventBridge Content Router &amp; Kafka</p>
              </div>
            </div>
            {publishResult && (
              <span
                className={`text-xs px-2.5 py-1 rounded-full font-bold border ${
                  publishResult.status === 'SUCCESS'
                    ? 'bg-emerald-950/60 border-emerald-500 text-emerald-300'
                    : 'bg-amber-950/60 border-amber-500 text-amber-300'
                }`}
              >
                {publishResult.status}
              </span>
            )}
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="text-xs font-semibold text-slate-400 block mb-1">Transaction ID</label>
              <input
                type="text"
                value={txId}
                onChange={(e) => setTxId(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-400 block mb-1">Amount (INR)</label>
              <input
                type="number"
                value={amount}
                onChange={(e) => setAmount(Number(e.target.value))}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-400 block mb-1">Payment Rail</label>
              <select
                value={rail}
                onChange={(e) => setRail(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200"
              >
                <option value="UPI">UPI</option>
                <option value="IMPS">IMPS</option>
                <option value="RTGS">RTGS</option>
                <option value="CARD">CARD</option>
              </select>
            </div>
          </div>

          <button
            onClick={handlePublishEvent}
            disabled={publishing}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 text-white rounded-lg text-sm font-bold shadow-lg shadow-indigo-600/20 transition-all"
          >
            <Play className={`w-4 h-4 ${publishing ? 'animate-spin' : ''}`} />
            Publish Transaction Event
          </button>

          {publishResult && (
            <div className="bg-slate-900/80 border border-slate-700/80 rounded-xl p-4 space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-400">SNS Deliveries:</span>
                <span className="font-bold text-emerald-400">{publishResult.sns?.deliveries} Subscriber Queues</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">EventBridge Content Match:</span>
                <span className="font-bold text-cyan-400">
                  {publishResult.eventbridge?.MatchedRulesCount > 0
                    ? `Matched HighValueRule (${publishResult.eventbridge?.MatchedRulesCount})`
                    : 'Standard Routing (No High-Value Rule)'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Kafka Partition Assigned:</span>
                <span className="font-mono text-purple-300">
                  Partition #{publishResult.kafka?.partition} (Offset #{publishResult.kafka?.offset})
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Card 2: Consumer Simulator & Poison Pill to DLQ */}
        <div className="bg-slate-800/50 border border-slate-700/70 rounded-2xl p-6 shadow-xl space-y-6">
          <div className="flex items-center justify-between border-b border-slate-700/70 pb-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-purple-500/20 text-purple-400 rounded-lg">
                <Server className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-lg font-bold">Queue Consumer &amp; DLQ Simulator</h2>
                <p className="text-slate-400 text-xs">Consume SQS messages and simulate worker failures triggering DLQ redrive</p>
              </div>
            </div>
            {consumerResult && (
              <span
                className={`text-xs px-2.5 py-1 rounded-full font-bold border ${
                  consumerResult.status === 'PROCESSED'
                    ? 'bg-emerald-950/60 border-emerald-500 text-emerald-300'
                    : consumerResult.status === 'FAILED_AND_NACKED'
                    ? 'bg-rose-950/60 border-rose-500 text-rose-300'
                    : 'bg-slate-800 border-slate-700 text-slate-400'
                }`}
              >
                {consumerResult.status}
              </span>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-semibold text-slate-400 block mb-1">Select Target Queue</label>
              <select
                value={selectedQueue}
                onChange={(e) => setSelectedQueue(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200"
              >
                <option value="fraud">Fraud Scoring Queue ({metrics?.queues?.fraud?.pending || 0} pending)</option>
                <option value="notifications">Notifications Queue ({metrics?.queues?.notifications?.pending || 0} pending)</option>
                <option value="compliance">High-Value Compliance ({metrics?.queues?.compliance?.pending || 0} pending)</option>
                <option value="audit_fifo">Audit FIFO Queue ({metrics?.queues?.audit_fifo?.pending || 0} pending)</option>
              </select>
            </div>
            <div className="flex items-center pt-6">
              <label className="flex items-center gap-2 cursor-pointer text-xs font-semibold text-rose-400">
                <input
                  type="checkbox"
                  checked={simulateFailure}
                  onChange={(e) => setSimulateFailure(e.target.checked)}
                  className="rounded border-slate-700 bg-slate-900 text-rose-600 focus:ring-0"
                />
                Simulate Worker Failure (Poison Pill)
              </label>
            </div>
          </div>

          <button
            onClick={handleProcessQueueMessage}
            disabled={consuming}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-purple-600 to-purple-500 hover:from-purple-500 hover:to-purple-400 text-white rounded-lg text-sm font-bold shadow-lg shadow-purple-600/20 transition-all"
          >
            <Play className={`w-4 h-4 ${consuming ? 'animate-spin' : ''}`} />
            Consume Next Message
          </button>

          {consumerResult && (
            <div className="bg-slate-900/80 border border-slate-700/80 rounded-xl p-4 space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-400">Result Status:</span>
                <span className="font-bold text-slate-200">{consumerResult.status}</span>
              </div>
              {consumerResult.receive_count && (
                <div className="flex justify-between">
                  <span className="text-slate-400">Receive Attempt Count:</span>
                  <span className="font-bold text-amber-400">{consumerResult.receive_count} / {consumerResult.max_retries || 3}</span>
                </div>
              )}
              {consumerResult.quarantined_to_dlq && (
                <div className="p-2 bg-rose-500/10 border border-rose-500/30 rounded text-rose-300 font-semibold">
                  ⚠️ Max retries exceeded. Poison message quarantined into Dead-Letter Queue (DLQ)!
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Row 3: DLQ Quarantine & Kafka Partitions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Card 3: Dead-Letter Queue Quarantine & Replay */}
        <div className="bg-slate-800/50 border border-slate-700/70 rounded-2xl p-6 shadow-xl space-y-4">
          <div className="flex items-center justify-between border-b border-slate-700/70 pb-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-rose-500/20 text-rose-400 rounded-lg">
                <ShieldAlert className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-lg font-bold">Dead-Letter Queue (DLQ) Quarantine</h2>
                <p className="text-slate-400 text-xs">Quarantined poisoned messages and controlled replay</p>
              </div>
            </div>
            <span className="text-xs px-2.5 py-1 rounded-full bg-slate-800 border border-slate-700 text-slate-300 font-mono">
              {dlqMessages.length} Messages
            </span>
          </div>

          {dlqMessages.length === 0 ? (
            <div className="text-center py-8 text-slate-500 text-sm">
              <CheckCircle2 className="w-8 h-8 mx-auto text-emerald-500/40 mb-2" />
              No poisoned messages in Dead-Letter Queue. All consumer queues healthy.
            </div>
          ) : (
            <div className="space-y-3 max-h-64 overflow-y-auto pr-1">
              {dlqMessages.map((msg) => (
                <div
                  key={msg.message_id}
                  className="bg-slate-900/80 border border-slate-800 rounded-xl p-3 space-y-2 text-xs"
                >
                  <div className="flex justify-between items-center">
                    <span className="font-mono text-rose-400 font-bold">{msg.message_id}</span>
                    <span className="text-slate-500">From: {msg.original_queue}</span>
                  </div>
                  <p className="text-slate-300">
                    <span className="text-slate-500">Reason:</span> {msg.failure_reason}
                  </p>
                  <div className="flex justify-between items-center pt-2 border-t border-slate-800">
                    <span className="text-slate-500">Attempts: {msg.receive_count}</span>
                    <button
                      onClick={() => handleReplayDLQ(msg.message_id, 'fraud')}
                      className="flex items-center gap-1.5 px-3 py-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-xs font-semibold transition-all"
                    >
                      <ListRestart className="w-3.5 h-3.5" />
                      Replay to Queue
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Card 4: Kafka Stream Partitions */}
        <div className="bg-slate-800/50 border border-slate-700/70 rounded-2xl p-6 shadow-xl space-y-4">
          <div className="flex items-center gap-3 border-b border-slate-700/70 pb-4">
            <div className="p-2 bg-purple-500/20 text-purple-400 rounded-lg">
              <Layers className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold">Kafka / Amazon MSK Stream Partitions</h2>
              <p className="text-slate-400 text-xs">Topic: finguard.transactions.stream (Keyed by Customer/Tenant)</p>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3">
            {[0, 1, 2].map((pId) => {
              const count = metrics?.kafka?.partition_sizes?.[`partition_${pId}`] || 0;
              return (
                <div key={pId} className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 text-center">
                  <span className="text-xs text-slate-500 uppercase font-bold block">Partition #{pId}</span>
                  <span className="text-2xl font-black text-purple-400 mt-1 block">{count}</span>
                  <span className="text-[10px] text-slate-500 mt-1 block">Committed Offset</span>
                </div>
              );
            })}
          </div>

          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 space-y-2 text-xs">
            <div className="flex justify-between">
              <span className="text-slate-400">Total Stream Records:</span>
              <span className="font-bold text-white">{metrics?.kafka?.total_records || 0} records</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Active Consumer Groups:</span>
              <span className="font-mono text-purple-300">fraud-scoring-group, audit-group</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Replay Capability:</span>
              <span className="text-emerald-400 font-semibold">Offset Rewind Supported</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EventStreamingPage;
