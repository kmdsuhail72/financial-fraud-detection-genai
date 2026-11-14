import React, { useState } from 'react';
import {
  Boxes,
  Server,
  ShieldCheck,
  Activity,
  Cpu,
  Layers,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Terminal,
  ExternalLink,
  Code2,
  Copy,
  Check
} from 'lucide-react';

interface PodInfo {
  name: string;
  service: string;
  ready: string;
  status: string;
  restarts: number;
  cpuUsage: string;
  memoryUsage: string;
  node: string;
}

export const KubernetesEksPage: React.FC = () => {
  const [copied, setCopied] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'topology' | 'manifests' | 'helm' | 'terraform'>('topology');
  const [selectedManifest, setSelectedManifest] = useState('deployment');

  // Simulated live cluster pods in finguard namespace
  const [pods, setPods] = useState<PodInfo[]>([
    {
      name: 'transaction-service-7f49c5bbd-8k2p1',
      service: 'transaction-service',
      ready: '1/1',
      status: 'Running',
      restarts: 0,
      cpuUsage: '42m',
      memoryUsage: '186Mi',
      node: 'ip-10-0-2-41.ap-south-1.compute.internal',
    },
    {
      name: 'transaction-service-7f49c5bbd-9m5v4',
      service: 'transaction-service',
      ready: '1/1',
      status: 'Running',
      restarts: 0,
      cpuUsage: '38m',
      memoryUsage: '192Mi',
      node: 'ip-10-0-3-88.ap-south-1.compute.internal',
    },
    {
      name: 'fraud-service-6b84d9f8c-2q7z9',
      service: 'fraud-service',
      ready: '1/1',
      status: 'Running',
      restarts: 0,
      cpuUsage: '65m',
      memoryUsage: '234Mi',
      node: 'ip-10-0-2-41.ap-south-1.compute.internal',
    },
    {
      name: 'fraud-service-6b84d9f8c-4w1x8',
      service: 'fraud-service',
      ready: '1/1',
      status: 'Running',
      restarts: 0,
      cpuUsage: '58m',
      memoryUsage: '228Mi',
      node: 'ip-10-0-3-88.ap-south-1.compute.internal',
    },
  ]);

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-gray-200 dark:border-gray-800 gap-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-600 rounded-lg text-white">
              <Boxes className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                Kubernetes Orchestration & Amazon EKS Hub
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Phase 34 · Production Microservices Deployment, Helm Packaging & AWS Mumbai (ap-south-1)
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300">
            <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
            Cluster: finguard-eks (ap-south-1)
          </div>
          <div className="text-xs px-2.5 py-1 rounded bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300 font-mono">
            K8s v1.29
          </div>
        </div>
      </div>

      {/* Cluster Overview KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <div className="p-3 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="text-gray-400 text-[11px] font-medium">Namespace</div>
          <div className="text-lg font-bold text-gray-900 dark:text-white mt-1 font-mono">finguard</div>
          <div className="text-[10px] text-blue-500 font-medium">Isolated tenant mesh</div>
        </div>

        <div className="p-3 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="text-gray-400 text-[11px] font-medium">Active Pods</div>
          <div className="text-lg font-bold text-emerald-600 dark:text-emerald-400 mt-1">
            {pods.length} Running
          </div>
          <div className="text-[10px] text-emerald-500 font-medium">100% Probes Passing</div>
        </div>

        <div className="p-3 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="text-gray-400 text-[11px] font-medium">Autoscaling (HPA)</div>
          <div className="text-lg font-bold text-purple-600 dark:text-purple-400 mt-1">2 - 10 Pods</div>
          <div className="text-[10px] text-purple-500 font-medium">CPU Target: 70%</div>
        </div>

        <div className="p-3 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="text-gray-400 text-[11px] font-medium">Disruption Budget (PDB)</div>
          <div className="text-lg font-bold text-indigo-600 dark:text-indigo-400 mt-1">minAvailable: 1</div>
          <div className="text-[10px] text-indigo-500 font-medium">Zero-downtime rolling</div>
        </div>

        <div className="p-3 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="text-gray-400 text-[11px] font-medium">Ingress Controller</div>
          <div className="text-lg font-bold text-amber-600 dark:text-amber-400 mt-1">AWS ALB</div>
          <div className="text-[10px] text-amber-500 font-medium">api.finguard.internal</div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex border-b border-gray-200 dark:border-gray-700 text-xs font-semibold gap-4">
        {[
          { id: 'topology', label: 'Workload Topology & Pods' },
          { id: 'manifests', label: 'Kubernetes Base Manifests' },
          { id: 'helm', label: 'Helm Chart & Values' },
          { id: 'terraform', label: 'AWS EKS Infrastructure (Mumbai)' },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`pb-2.5 transition ${
              activeTab === tab.id
                ? 'border-b-2 border-blue-600 text-blue-600 dark:text-blue-400'
                : 'text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab 1: Workload Topology & Pods */}
      {activeTab === 'topology' && (
        <div className="space-y-4">
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                <Server className="w-4 h-4 text-blue-500" />
                Live Pod Workloads (Namespace: finguard)
              </h2>
              <span className="text-xs text-gray-400">Security: Non-Root (UID 10001) · Read-Only FS</span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-gray-50 dark:bg-gray-900/50 text-gray-500 dark:text-gray-400 border-y border-gray-200 dark:border-gray-700">
                  <tr>
                    <th className="py-2.5 px-3">Pod Name</th>
                    <th className="py-2.5 px-3">Service</th>
                    <th className="py-2.5 px-3">Ready</th>
                    <th className="py-2.5 px-3">Status</th>
                    <th className="py-2.5 px-3">CPU</th>
                    <th className="py-2.5 px-3">Memory</th>
                    <th className="py-2.5 px-3">Node</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-gray-800 font-mono">
                  {pods.map((p) => (
                    <tr key={p.name} className="hover:bg-gray-50 dark:hover:bg-gray-900/30">
                      <td className="py-2.5 px-3 font-semibold text-gray-900 dark:text-white">
                        {p.name}
                      </td>
                      <td className="py-2.5 px-3">
                        <span className="px-2 py-0.5 rounded text-[11px] bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
                          {p.service}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-emerald-600 dark:text-emerald-400">{p.ready}</td>
                      <td className="py-2.5 px-3">
                        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300">
                          <CheckCircle2 className="w-3 h-3" />
                          {p.status}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-gray-600 dark:text-gray-300">{p.cpuUsage}</td>
                      <td className="py-2.5 px-3 text-gray-600 dark:text-gray-300">{p.memoryUsage}</td>
                      <td className="py-2.5 px-3 text-gray-400 text-[11px]">{p.node}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Microservice Endpoints & Local Test Commands */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-xs text-gray-900 dark:text-white flex items-center gap-2">
                  <Server className="w-4 h-4 text-indigo-500" />
                  Transaction Microservice (Port 8101)
                </span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800">
                  Ready & Live
                </span>
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Outbox writes, Saga orchestration, and customer balance locks.
              </p>
              <div className="bg-gray-950 p-2.5 rounded text-xs font-mono text-gray-300 space-y-1">
                <div>curl http://localhost:8101/health</div>
                <div>curl http://localhost:8101/metrics</div>
              </div>
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-xs text-gray-900 dark:text-white flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-rose-500" />
                  Fraud-Scoring Microservice (Port 8102)
                </span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800">
                  Ready & Live
                </span>
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Low-latency ML scoring inferences and heuristic risk flags.
              </p>
              <div className="bg-gray-950 p-2.5 rounded text-xs font-mono text-gray-300 space-y-1">
                <div>curl http://localhost:8102/health</div>
                <div>curl -X POST http://localhost:8102/score -d '&#123;...&#125;'</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Manifest Inspector */}
      {activeTab === 'manifests' && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-gray-100 dark:border-gray-700 pb-3">
            <div className="flex gap-2">
              {['deployment', 'service', 'hpa', 'pdb', 'networkpolicy', 'ingress'].map((m) => (
                <button
                  key={m}
                  onClick={() => setSelectedManifest(m)}
                  className={`px-3 py-1 rounded text-xs font-medium uppercase ${
                    selectedManifest === m
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300'
                  }`}
                >
                  {m}
                </button>
              ))}
            </div>
          </div>

          <div className="bg-gray-950 text-gray-200 p-4 rounded-lg font-mono text-xs overflow-x-auto max-h-96">
            {selectedManifest === 'deployment' && (
              <pre>{`apiVersion: apps/v1
kind: Deployment
metadata:
  name: transaction-service
  namespace: finguard
spec:
  replicas: 2
  template:
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
      containers:
        - name: transaction-service
          image: finguard/transaction-service:1.0.0
          securityContext:
            readOnlyRootFilesystem: true
            allowPrivilegeEscalation: false
            capabilities:
              drop: ["ALL"]
          resources:
            requests: { cpu: 250m, memory: 256Mi }
            limits: { cpu: 1000m, memory: 512Mi }
          startupProbe:
            httpGet: { path: /startup, port: 8101 }
          livenessProbe:
            httpGet: { path: /live, port: 8101 }
          readinessProbe:
            httpGet: { path: /ready, port: 8101 }`}</pre>
            )}

            {selectedManifest === 'hpa' && (
              <pre>{`apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: transaction-service-hpa
  namespace: finguard
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: transaction-service
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70`}</pre>
            )}

            {selectedManifest === 'ingress' && (
              <pre>{`apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: finguard-alb-ingress
  namespace: finguard
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
spec:
  rules:
    - host: api.finguard.internal
      http:
        paths:
          - path: /transactions
            pathType: Prefix
            backend:
              service:
                name: transaction-service
                port: { number: 8101 }`}</pre>
            )}

            {selectedManifest === 'pdb' && (
              <pre>{`apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: transaction-service-pdb
  namespace: finguard
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: transaction-service`}</pre>
            )}

            {selectedManifest === 'networkpolicy' && (
              <pre>{`apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: fraud-service-network-policy
  namespace: finguard
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: fraud-service
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app.kubernetes.io/name: transaction-service
      ports:
        - protocol: TCP
          port: 8102`}</pre>
            )}

            {selectedManifest === 'service' && (
              <pre>{`apiVersion: v1
kind: Service
metadata:
  name: transaction-service
  namespace: finguard
spec:
  type: ClusterIP
  ports:
    - port: 8101
      targetPort: 8101
      name: http`}</pre>
            )}
          </div>
        </div>
      )}

      {/* Tab 3: Helm Chart & Values */}
      {activeTab === 'helm' && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-gray-100 dark:border-gray-700 pb-3">
            <div>
              <h2 className="text-sm font-semibold text-gray-900 dark:text-white">
                Helm Chart Configuration (helm/finguard/)
              </h2>
              <p className="text-xs text-gray-500">
                Single configurable release packaging both transaction and fraud microservices.
              </p>
            </div>
            <div className="text-xs px-2 py-1 bg-purple-50 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300 font-mono rounded">
              finguard-1.0.0.tgz
            </div>
          </div>

          <div className="bg-gray-950 text-gray-200 p-4 rounded-lg font-mono text-xs overflow-x-auto max-h-96">
            <pre>{`# values.yaml
global:
  environment: production
  awsRegion: ap-south-1

transactionService:
  replicaCount: 2
  image:
    repository: finguard/transaction-service
    tag: 1.0.0
  service:
    port: 8101
  autoscaling:
    enabled: true
    minReplicas: 2
    maxReplicas: 10
    targetCPUUtilizationPercentage: 70

fraudService:
  replicaCount: 2
  image:
    repository: finguard/fraud-service
    tag: 1.0.0
  service:
    port: 8102
  autoscaling:
    enabled: true
    minReplicas: 2
    maxReplicas: 10
    targetCPUUtilizationPercentage: 70

ingress:
  enabled: true
  className: alb
  host: api.finguard.internal`}</pre>
          </div>
        </div>
      )}

      {/* Tab 4: Terraform EKS Foundation */}
      {activeTab === 'terraform' && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-gray-100 dark:border-gray-700 pb-3">
            <div>
              <h2 className="text-sm font-semibold text-gray-900 dark:text-white">
                AWS EKS Infrastructure (Mumbai ap-south-1)
              </h2>
              <p className="text-xs text-gray-500">
                Terraform foundation declaring VPC, EKS Control Plane v1.29, and Managed Node Groups.
              </p>
            </div>
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-amber-50 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300">
              Region: ap-south-1
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
            <div className="p-3 bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800">
              <div className="font-semibold text-gray-900 dark:text-white mb-1">EKS Cluster</div>
              <div className="text-gray-500 font-mono text-[11px]">finguard-eks-cluster</div>
              <div className="text-gray-400 text-[10px] mt-1">Version: 1.29 (Managed Control Plane)</div>
            </div>
            <div className="p-3 bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800">
              <div className="font-semibold text-gray-900 dark:text-white mb-1">Managed Nodes</div>
              <div className="text-gray-500 font-mono text-[11px]">m5.large / t3.medium</div>
              <div className="text-gray-400 text-[10px] mt-1">Scaling: 2 min / 5 max (Private Subnets)</div>
            </div>
            <div className="p-3 bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800">
              <div className="font-semibold text-gray-900 dark:text-white mb-1">Cluster Add-Ons</div>
              <div className="text-gray-500 font-mono text-[11px]">vpc-cni · coredns · kube-proxy</div>
              <div className="text-gray-400 text-[10px] mt-1">AWS IAM Authenticator enabled</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

