import React, { useState, useEffect } from 'react';
import {
  Server,
  Activity,
  Layers,
  ArrowRight,
  RotateCcw,
  AlertOctagon,
  CheckCircle2,
  Clock,
  Play,
  RefreshCw,
  Send,
  ShieldCheck,
  Check,
  XCircle,
  FileText
} from 'lucide-react';
import axios from 'axios';

interface ArchitectureHealth {
  status: string;
  service: string;
  phase: string;
  architecture: {
    services: string[];
    event_bus: string;
    patterns: string[];
  };
}

interface MicroserviceMetrics {
  total_events_published: number;
  total_events_consumed: number;
  pending_outbox_count: number;
  dead_letter_queue_count: number;
  sagas_completed: number;
  sagas_compensated: number;
  idempotent_deduplications: number;
  service_health: Record<string, string>;
}

interface SagaStep {
  step_name: string;
  service_name: string;
  status: string;
  forward_action: string;
  compensation_action: string;
  error?: string;
}

interface SagaInstance {
  saga_id: string;
  transaction_id: string;
  correlation_id: string;
  status: string;
  current_step: number;
  steps: SagaStep[];
  compensation_log: string[];
  error?: string;
}

interface OutboxRecord {
  outbox_id: string;
  aggregate_type: string;
  aggregate_id: string;
  status: string;
  retry_count: number;
  event: {
    event_id: string;
    event_type: string;
    correlation_id: string;
  };
  created_at: string;
  published_at?: string;
}

interface DeadLetterRecord {
  dlq_id: string;
  failure_reason: string;
  retry_attempts: number;
  captured_at: string;
  replayed: boolean;
  original_event: {
    event_id: string;
    event_type: string;
    source: string;
    correlation_id: string;
  };
}

interface EventContract {
  event_id: string;
  event_type: string;
  source: string;
  timestamp: string;
  correlation_id: string;
  causation_id?: string;
  payload: any;
}

export const EventDrivenMicroservicesPage: React.FC = () => {
  const [health, setHealth] = useState<ArchitectureHealth | null>(null);
  const [metrics, setMetrics] = useState<MicroserviceMetrics | null>(null);
  const [loading, setLoading] = useState(false);

  // Transaction & Saga execution form
  const [txnId, setTxnId] = useState(`TXN-${Math.floor(100000 + Math.random() * 900000)}`);
  const [customerId, setCustomerId] = useState('CUST-4912');
  const [amount, setAmount] = useState('45000');
  const [rail, setRail] = useState('UPI');
  const [forceFailStep, setForceFailStep] = useState<string>('none');
  const [lastSaga, setLastSaga] = useState<SagaInstance | null>(null);
  const [isExecuting, setIsExecuting] = useState(false);

  // Outbox & DLQ state
  const [outboxRecords, setOutboxRecords] = useState<OutboxRecord[]>([]);
  const [dlqRecords, setDlqRecords] = useState<DeadLetterRecord[]>([]);
  const [events, setEvents] = useState<EventContract[]>([]);
  const [selectedCorrelationId, setSelectedCorrelationId] = useState<string>('');

  const fetchData = async () => {
    try {
      setLoading(true);
      const [hRes, mRes, obRes, dlqRes, evtRes] = await Promise.all([
        axios.get('/microservices/health'),
        axios.get('/microservices/metrics'),
        axios.get('/microservices/outbox'),
        axios.get('/microservices/dlq'),
        axios.get('/microservices/events'),
      ]);
      setHealth(hRes.data);
      setMetrics(mRes.data);
      setOutboxRecords(obRes.data);
      setDlqRecords(dlqRes.data);
      setEvents(evtRes.data);
    } catch (err) {
      console.error('Failed to load microservice data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleInitiateTransaction = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setIsExecuting(true);
      const payload: any = {
        transaction_id: txnId,
        customer_id: customerId,
        amount: parseFloat(amount) || 0,
        currency: 'INR',
        rail: rail,
      };
      if (forceFailStep !== 'none') {
        payload.force_failure_at_step = forceFailStep;
      }

      const res = await axios.post('/microservices/transactions', payload, {
        headers: { 'Idempotency-Key': `idem-${txnId}` },
      });

      const sagaId = res.data.data.saga_id;
      const sagaRes = await axios.get(`/microservices/saga/${sagaId}`);
      setLastSaga(sagaRes.data);
      setSelectedCorrelationId(res.data.data.correlation_id);

      // Generate a new random txnId for next run
      setTxnId(`TXN-${Math.floor(100000 + Math.random() * 900000)}`);
      fetchData();
    } catch (err: any) {
      console.error('Failed to initiate transaction:', err);
    } finally {
      setIsExecuting(false);
    }
  };

  const handleFlushOutbox = async () => {
    try {
      await axios.post('/microservices/outbox/flush');
      fetchData();
    } catch (err) {
      console.error('Failed to flush outbox:', err);
    }
  };

  const handleReplayDlq = async (dlqId: string) => {
    try {
      await axios.post(`/microservices/dlq/replay/${dlqId}`);
      fetchData();
    } catch (err) {
      console.error('Failed to replay DLQ message:', err);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-gray-200 dark:border-gray-800 gap-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-600 rounded-lg text-white">
              <Layers className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                Enterprise Microservices & Event Bus Architecture
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Phase 33 · Event-Driven Saga Orchestration, Transactional Outbox, Bounded Retries & DLQ
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            Status: {health?.status?.toUpperCase() || 'HEALTHY'}
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

      {/* Microservice Boundaries Map */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 shadow-sm">
        <h2 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">
          Active Microservices Mesh
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { name: 'Transaction Service', desc: 'Ingress & Outbox', icon: Server, color: 'text-indigo-500' },
            { name: 'Fraud-Scoring Service', desc: 'Real-Time Inference', icon: ShieldCheck, color: 'text-rose-500' },
            { name: 'Ledger Service', desc: 'Account Settlement', icon: Activity, color: 'text-emerald-500' },
            { name: 'Notification Service', desc: 'Customer Alerts & SNS', icon: Send, color: 'text-amber-500' },
          ].map((svc, i) => {
            const Icon = svc.icon;
            return (
              <div
                key={i}
                className="p-3 bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 flex items-center gap-3"
              >
                <div className="p-2 rounded-lg bg-white dark:bg-gray-800 shadow-xs">
                  <Icon className={`w-5 h-5 ${svc.color}`} />
                </div>
                <div>
                  <div className="text-xs font-semibold text-gray-900 dark:text-white">
                    {svc.name}
                  </div>
                  <div className="text-[11px] text-gray-400">{svc.desc}</div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
        <div className="p-3 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="text-gray-400 text-[11px] font-medium">Events Published</div>
          <div className="text-xl font-bold text-gray-900 dark:text-white mt-1">
            {metrics?.total_events_published ?? 0}
          </div>
          <div className="text-[10px] text-indigo-500 font-medium">EventBridge bus</div>
        </div>

        <div className="p-3 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="text-gray-400 text-[11px] font-medium">Events Consumed</div>
          <div className="text-xl font-bold text-emerald-600 dark:text-emerald-400 mt-1">
            {metrics?.total_events_consumed ?? 0}
          </div>
          <div className="text-[10px] text-emerald-500 font-medium">At-least-once delivery</div>
        </div>

        <div className="p-3 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="text-gray-400 text-[11px] font-medium">Sagas Completed</div>
          <div className="text-xl font-bold text-blue-600 dark:text-blue-400 mt-1">
            {metrics?.sagas_completed ?? 0}
          </div>
          <div className="text-[10px] text-blue-500 font-medium">Forward executed</div>
        </div>

        <div className="p-3 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="text-gray-400 text-[11px] font-medium">Sagas Compensated</div>
          <div className="text-xl font-bold text-amber-600 dark:text-amber-400 mt-1">
            {metrics?.sagas_compensated ?? 0}
          </div>
          <div className="text-[10px] text-amber-500 font-medium">Reverse rolled back</div>
        </div>

        <div className="p-3 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="text-gray-400 text-[11px] font-medium">Pending Outbox</div>
          <div className="text-xl font-bold text-purple-600 dark:text-purple-400 mt-1">
            {metrics?.pending_outbox_count ?? 0}
          </div>
          <div className="text-[10px] text-purple-500 font-medium">Dual-write safe</div>
        </div>

        <div className="p-3 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="text-gray-400 text-[11px] font-medium">DLQ Messages</div>
          <div className="text-xl font-bold text-rose-600 dark:text-rose-400 mt-1">
            {metrics?.dead_letter_queue_count ?? 0}
          </div>
          <div className="text-[10px] text-rose-500 font-medium">Exhausted retries</div>
        </div>
      </div>

      {/* Main Workbench: Trigger & Saga Execution */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Transaction Dispatcher Form */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 shadow-sm space-y-4">
          <div className="flex items-center gap-2 border-b border-gray-100 dark:border-gray-700 pb-3">
            <Play className="w-5 h-5 text-indigo-500" />
            <h2 className="text-sm font-semibold text-gray-900 dark:text-white">
              Initiate Outbox-Backed Transaction
            </h2>
          </div>

          <form onSubmit={handleInitiateTransaction} className="space-y-3 text-xs">
            <div>
              <label className="block font-medium text-gray-600 dark:text-gray-300 mb-1">
                Transaction ID
              </label>
              <input
                type="text"
                value={txnId}
                onChange={(e) => setTxnId(e.target.value)}
                className="w-full px-3 py-1.5 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 font-mono text-gray-900 dark:text-white"
                required
              />
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block font-medium text-gray-600 dark:text-gray-300 mb-1">
                  Customer ID
                </label>
                <input
                  type="text"
                  value={customerId}
                  onChange={(e) => setCustomerId(e.target.value)}
                  className="w-full px-3 py-1.5 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
                  required
                />
              </div>
              <div>
                <label className="block font-medium text-gray-600 dark:text-gray-300 mb-1">
                  Amount (INR)
                </label>
                <input
                  type="number"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  className="w-full px-3 py-1.5 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block font-medium text-gray-600 dark:text-gray-300 mb-1">
                Payment Rail
              </label>
              <select
                value={rail}
                onChange={(e) => setRail(e.target.value)}
                className="w-full px-3 py-1.5 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
              >
                <option value="UPI">UPI (Instant)</option>
                <option value="IMPS">IMPS</option>
                <option value="NEFT">NEFT</option>
                <option value="RTGS">RTGS</option>
              </select>
            </div>

            {/* Test Saga Compensation Failure Injection */}
            <div className="p-3 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 rounded-lg">
              <label className="block font-semibold text-amber-800 dark:text-amber-300 mb-1">
                Simulate Step Failure (Test Compensation)
              </label>
              <select
                value={forceFailStep}
                onChange={(e) => setForceFailStep(e.target.value)}
                className="w-full px-2 py-1 text-xs rounded border border-amber-300 dark:border-amber-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
              >
                <option value="none">None (Happy Path - Success)</option>
                <option value="EvaluateFraudRisk">Step 2: EvaluateFraudRisk (Simulate High Risk)</option>
                <option value="SettleTransaction">Step 3: SettleTransaction (Simulate Insufficient Bal)</option>
                <option value="SendNotification">Step 4: SendNotification (Simulate SNS Timeout)</option>
              </select>
            </div>

            <button
              type="submit"
              disabled={isExecuting}
              className="w-full py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded font-medium shadow-sm transition flex items-center justify-center gap-1.5"
            >
              <Play className="w-4 h-4" />
              {isExecuting ? 'Orchestrating Saga...' : 'Dispatch Transaction'}
            </button>
          </form>
        </div>

        {/* Distributed Saga Execution Inspector */}
        <div className="lg:col-span-2 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-gray-100 dark:border-gray-700 pb-3">
            <div className="flex items-center gap-2">
              <RotateCcw className="w-5 h-5 text-purple-500" />
              <h2 className="text-sm font-semibold text-gray-900 dark:text-white">
                Distributed Saga Orchestration Workflow
              </h2>
            </div>
            {lastSaga && (
              <span
                className={`text-xs px-2.5 py-0.5 rounded-full font-semibold ${
                  lastSaga.status === 'COMPLETED'
                    ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300'
                    : 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300'
                }`}
              >
                Saga: {lastSaga.status}
              </span>
            )}
          </div>

          {!lastSaga ? (
            <div className="text-center py-12 text-gray-400 text-xs">
              Dispatch a transaction on the left to observe forward execution or reverse-order compensation in real time.
            </div>
          ) : (
            <div className="space-y-4">
              {/* Step Sequence Diagram */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-2">
                {lastSaga.steps.map((step, idx) => (
                  <div
                    key={idx}
                    className={`p-3 rounded-lg border text-xs flex flex-col justify-between ${
                      step.status === 'EXECUTED'
                        ? 'bg-emerald-50 dark:bg-emerald-950/30 border-emerald-300 dark:border-emerald-800 text-emerald-900 dark:text-emerald-200'
                        : step.status === 'COMPENSATED'
                        ? 'bg-amber-50 dark:bg-amber-950/30 border-amber-300 dark:border-amber-800 text-amber-900 dark:text-amber-200'
                        : step.status === 'FAILED'
                        ? 'bg-rose-50 dark:bg-rose-950/30 border-rose-300 dark:border-rose-800 text-rose-900 dark:text-rose-200'
                        : 'bg-gray-50 dark:bg-gray-900 border-gray-200 dark:border-gray-800 text-gray-400'
                    }`}
                  >
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-bold text-[10px]">STEP {idx + 1}</span>
                        {step.status === 'EXECUTED' ? (
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                        ) : step.status === 'COMPENSATED' ? (
                          <RotateCcw className="w-3.5 h-3.5 text-amber-600" />
                        ) : step.status === 'FAILED' ? (
                          <XCircle className="w-3.5 h-3.5 text-rose-600" />
                        ) : (
                          <Clock className="w-3.5 h-3.5 text-gray-400" />
                        )}
                      </div>
                      <div className="font-semibold">{step.step_name}</div>
                      <div className="text-[10px] opacity-75">{step.service_name}</div>
                    </div>

                    <div className="mt-2 pt-2 border-t border-black/10 dark:border-white/10 text-[10px]">
                      {step.status === 'COMPENSATED' ? (
                        <span className="font-mono text-amber-700 dark:text-amber-300">
                          ↩ {step.compensation_action}
                        </span>
                      ) : (
                        <span className="font-mono">➔ {step.forward_action}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {/* Compensation Log if any */}
              {lastSaga.compensation_log.length > 0 && (
                <div className="p-3 bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800 rounded-lg text-xs space-y-1">
                  <div className="font-semibold text-amber-800 dark:text-amber-300 flex items-center gap-1.5">
                    <RotateCcw className="w-3.5 h-3.5" />
                    Reverse Compensation Sequence:
                  </div>
                  {lastSaga.compensation_log.map((log, i) => (
                    <div key={i} className="font-mono text-[11px] text-amber-900 dark:text-amber-200">
                      {log}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Outbox & DLQ Sections */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Transactional Outbox Table */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 shadow-sm space-y-3">
          <div className="flex items-center justify-between border-b border-gray-100 dark:border-gray-700 pb-2">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-purple-500" />
              <h3 className="text-xs font-semibold text-gray-900 dark:text-white uppercase tracking-wider">
                Transactional Outbox Monitor
              </h3>
            </div>
            <button
              onClick={handleFlushOutbox}
              className="text-[11px] px-2.5 py-1 bg-purple-50 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300 rounded font-medium hover:bg-purple-100 transition"
            >
              Flush Outbox
            </button>
          </div>

          <div className="space-y-2 max-h-52 overflow-y-auto">
            {outboxRecords.length === 0 ? (
              <div className="text-center py-6 text-gray-400 text-xs">Outbox is empty.</div>
            ) : (
              outboxRecords.map((ob) => (
                <div
                  key={ob.outbox_id}
                  className="p-2.5 bg-gray-50 dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-800 flex items-center justify-between text-xs"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-semibold">{ob.aggregate_id}</span>
                      <span
                        className={`text-[10px] px-1.5 py-0.2 rounded font-semibold ${
                          ob.status === 'PUBLISHED'
                            ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300'
                            : 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300'
                        }`}
                      >
                        {ob.status}
                      </span>
                    </div>
                    <div className="text-[10px] text-gray-400 mt-0.5">{ob.event.event_type}</div>
                  </div>
                  <div className="text-right text-[10px] text-gray-400 font-mono">
                    {ob.outbox_id}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Dead-Letter Queue (DLQ) Inspector */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 shadow-sm space-y-3">
          <div className="flex items-center justify-between border-b border-gray-100 dark:border-gray-700 pb-2">
            <div className="flex items-center gap-2">
              <AlertOctagon className="w-4 h-4 text-rose-500" />
              <h3 className="text-xs font-semibold text-gray-900 dark:text-white uppercase tracking-wider">
                Dead-Letter Queue (DLQ)
              </h3>
            </div>
            <span className="text-[11px] text-gray-400">Bounded Retries: 3</span>
          </div>

          <div className="space-y-2 max-h-52 overflow-y-auto">
            {dlqRecords.length === 0 ? (
              <div className="text-center py-6 text-emerald-600 dark:text-emerald-400 text-xs">
                Zero dead letters. All consumer handlers healthy.
              </div>
            ) : (
              dlqRecords.map((dlq) => (
                <div
                  key={dlq.dlq_id}
                  className="p-2.5 bg-rose-50/50 dark:bg-rose-950/20 rounded border border-rose-200 dark:border-rose-900/40 flex items-center justify-between text-xs"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-rose-900 dark:text-rose-200 font-semibold">
                        {dlq.original_event.event_type}
                      </span>
                      <span className="text-[10px] px-1.5 py-0.2 rounded bg-rose-200 text-rose-900 dark:bg-rose-900 dark:text-rose-100">
                        {dlq.retry_attempts} retries
                      </span>
                    </div>
                    <div className="text-[10px] text-rose-700 dark:text-rose-300 mt-0.5">
                      {dlq.failure_reason}
                    </div>
                  </div>
                  <button
                    onClick={() => handleReplayDlq(dlq.dlq_id)}
                    disabled={dlq.replayed}
                    className="text-[10px] px-2 py-1 bg-rose-600 text-white rounded hover:bg-rose-700 transition disabled:opacity-50"
                  >
                    {dlq.replayed ? 'Replayed' : 'Replay'}
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Distributed Event Log & Correlation Tracing */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 shadow-sm space-y-3">
        <div className="flex items-center justify-between border-b border-gray-100 dark:border-gray-700 pb-2">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-indigo-500" />
            <h3 className="text-xs font-semibold text-gray-900 dark:text-white uppercase tracking-wider">
              Distributed Event Log & Correlation Tracing
            </h3>
          </div>
          {selectedCorrelationId && (
            <button
              onClick={() => setSelectedCorrelationId('')}
              className="text-[11px] text-indigo-600 hover:underline"
            >
              Clear filter ({selectedCorrelationId})
            </button>
          )}
        </div>

        <div className="space-y-1.5 max-h-60 overflow-y-auto">
          {events
            .filter((e) => !selectedCorrelationId || e.correlation_id === selectedCorrelationId)
            .slice(0, 15)
            .map((evt) => (
              <div
                key={evt.event_id}
                onClick={() => setSelectedCorrelationId(evt.correlation_id)}
                className="p-2 bg-gray-50 dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-800 flex items-center justify-between text-xs font-mono cursor-pointer hover:border-indigo-500 transition"
              >
                <div className="flex items-center gap-3">
                  <span className="text-indigo-600 dark:text-indigo-400 font-semibold">
                    {evt.event_type}
                  </span>
                  <span className="text-[10px] text-gray-400">[{evt.source}]</span>
                </div>
                <div className="flex items-center gap-3 text-[10px] text-gray-400">
                  <span>corr: {evt.correlation_id}</span>
                  <span>{new Date(evt.timestamp).toLocaleTimeString()}</span>
                </div>
              </div>
            ))}
        </div>
      </div>
    </div>
  );
};
