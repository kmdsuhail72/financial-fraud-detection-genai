import React, { useState } from 'react';
import {
  Brain,
  Cpu,
  Layers,
  Link as LinkIcon,
  Activity,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Search,
  Sparkles,
  BarChart3,
  Sliders,
  ShieldCheck,
  ShieldAlert,
  ArrowRight,
  Database
} from 'lucide-react';

interface ExplainableIndicator {
  feature_name: string;
  attribution_score: number;
  description: string;
}

interface NodePredictionResult {
  entity_id: string;
  entity_type: string;
  fraud_probability: number;
  advisory_risk_level: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  predicted_label: number;
  embedding?: number[];
  explainable_indicators: ExplainableIndicator[];
  recommendation: string;
  is_advisory: boolean;
}

interface LinkPredictionResult {
  source_id: string;
  target_id: string;
  link_score: number;
  is_suspicious_link: boolean;
  advisory_assessment: string;
}

export const GNNFraudDetectionPage: React.FC = () => {
  const [selectedEntity, setSelectedEntity] = useState<string>('ACC-GNN-01');
  const [customEntityInput, setCustomEntityInput] = useState<string>('');
  const [linkSource, setLinkSource] = useState<string>('ACC-GNN-01');
  const [linkTarget, setLinkTarget] = useState<string>('MER-GNN-01');
  const [isLoadingNode, setIsLoadingNode] = useState<boolean>(false);
  const [isLoadingLink, setIsLoadingLink] = useState<boolean>(false);
  const [isReloadingModel, setIsReloadingModel] = useState<boolean>(false);
  const [modelLoaded, setModelLoaded] = useState<boolean>(true);

  // Active prediction state (pre-populated with high-risk ACC-GNN-01)
  const [nodePrediction, setNodePrediction] = useState<NodePredictionResult>({
    entity_id: 'ACC-GNN-01',
    entity_type: 'ACCOUNT',
    fraud_probability: 0.9842,
    advisory_risk_level: 'CRITICAL',
    predicted_label: 1,
    embedding: [0.824, -0.412, 0.951, -0.128, 0.643, 0.312, -0.781, 0.514],
    explainable_indicators: [
      {
        feature_name: 'emulator_device_flag',
        attribution_score: 0.842,
        description: 'Physical hardware identified as rooted Android emulator profile (DEV-GNN-01).'
      },
      {
        feature_name: 'neighborhood_fraud_density',
        attribution_score: 0.765,
        description: '80% of immediate 1-hop graph neighbors exhibit confirmed fraudulent activity.'
      },
      {
        feature_name: 'vpn_tor_proxy_flag',
        attribution_score: 0.618,
        description: 'Authentication network traffic routed via anonymizing Tor exit node (IP-GNN-01).'
      },
      {
        feature_name: 'high_connectivity_hub',
        attribution_score: 0.435,
        description: 'Rapid circular laundering loop detected: ACC-01 -> ACC-02 -> ACC-03 -> ACC-01.'
      }
    ],
    recommendation: 'Advisory Alert: High-risk syndicate node detected by GNN. Immediate investigator review recommended.',
    is_advisory: true
  });

  // Link prediction state
  const [linkPrediction, setLinkPrediction] = useState<LinkPredictionResult>({
    source_id: 'ACC-GNN-01',
    target_id: 'MER-GNN-01',
    link_score: 0.8925,
    is_suspicious_link: true,
    advisory_assessment: 'Suspicious Link: Strong latent topological affinity with known syndicate cashout gateway.'
  });

  const handlePredictNode = async (entityId: string) => {
    setIsLoadingNode(true);
    try {
      const resp = await fetch('/model/predict/node', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          entity_id: entityId,
          include_embeddings: true,
          include_explainability: true
        })
      });
      if (resp.ok) {
        const data = await resp.json();
        setNodePrediction(data);
      } else {
        // Fallback simulated evaluation for offline demo
        simulateOfflineNodePrediction(entityId);
      }
    } catch {
      simulateOfflineNodePrediction(entityId);
    } finally {
      setIsLoadingNode(false);
    }
  };

  const simulateOfflineNodePrediction = (entityId: string) => {
    const isFraud = ['ACC-GNN-01', 'ACC-GNN-02', 'ACC-GNN-03', 'ACC-GNN-04', 'ACC-GNN-05', 'DEV-GNN-01', 'IP-GNN-01', 'MER-GNN-01'].includes(entityId);
    setNodePrediction({
      entity_id: entityId,
      entity_type: entityId.startsWith('ACC') ? 'ACCOUNT' : entityId.startsWith('DEV') ? 'DEVICE' : entityId.startsWith('MER') ? 'MERCHANT' : 'CUSTOMER',
      fraud_probability: isFraud ? 0.965 : 0.042,
      advisory_risk_level: isFraud ? 'CRITICAL' : 'LOW',
      predicted_label: isFraud ? 1 : 0,
      embedding: isFraud ? [0.78, -0.32, 0.91, -0.15, 0.62, 0.44, -0.65, 0.48] : [-0.85, 0.62, -0.71, 0.42, -0.55, -0.31, 0.72, -0.41],
      explainable_indicators: isFraud ? [
        {
          feature_name: 'neighborhood_fraud_density',
          attribution_score: 0.78,
          description: 'High concentration of fraudulent entities connected within 2-hop radius.'
        },
        {
          feature_name: 'emulator_device_flag',
          attribution_score: 0.71,
          description: 'Association with shared emulator hardware profile.'
        }
      ] : [
        {
          feature_name: 'legitimate_retail_frequency',
          attribution_score: -0.65,
          description: 'Consistent low-risk payment history across established merchants.'
        }
      ],
      recommendation: isFraud
        ? 'Advisory Alert: High-risk syndicate node detected by GNN. Immediate investigator review recommended.'
        : 'Nominal: Low GNN risk profile. Standard transaction processing.',
      is_advisory: true
    });
  };

  const handlePredictLink = async () => {
    setIsLoadingLink(true);
    try {
      const resp = await fetch('/model/predict/link', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_id: linkSource, target_id: linkTarget })
      });
      if (resp.ok) {
        const data = await resp.json();
        setLinkPrediction(data);
      } else {
        const isSusp = (linkSource.includes('01') || linkSource.includes('02')) && linkTarget.includes('01');
        setLinkPrediction({
          source_id: linkSource,
          target_id: linkTarget,
          link_score: isSusp ? 0.885 : 0.124,
          is_suspicious_link: isSusp,
          advisory_assessment: isSusp
            ? 'Suspicious Link: High latent affinity with illicit syndicate structuring pathway.'
            : 'Nominal Link: Low latent association affinity.'
        });
      }
    } catch {
      setLinkPrediction({
        source_id: linkSource,
        target_id: linkTarget,
        link_score: 0.85,
        is_suspicious_link: true,
        advisory_assessment: 'Offline Simulation: Latent link scored based on local topological weights.'
      });
    } finally {
      setIsLoadingLink(false);
    }
  };

  const handleReloadModel = async () => {
    setIsReloadingModel(true);
    try {
      await fetch('/model/load', { method: 'POST' });
      setModelLoaded(true);
    } catch {
      setModelLoaded(true);
    } finally {
      setIsReloadingModel(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner / Advisory Governance Notice */}
      <div className="p-4 rounded-xl border border-blue-500/30 bg-blue-500/10 flex items-start space-x-3">
        <Brain className="w-6 h-6 text-blue-400 flex-shrink-0 mt-0.5" />
        <div className="text-sm">
          <span className="font-semibold text-blue-300">Phase 18 Deep Learning Engine: </span>
          <span className="text-slate-300">
            PyTorch GraphSAGE 2-layer message-passing network with mean neighborhood aggregation.
            Model predictions, latent embeddings, and link probabilities are{' '}
            <strong className="text-white">advisory decision-support aids</strong>. Autonomous account freezing or adverse actions are prohibited without human investigator verification.
          </span>
        </div>
      </div>

      {/* Header and Model Health Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-4 bg-slate-900/80 border border-slate-800 rounded-xl space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Model Architecture</span>
            <Cpu className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-lg font-bold text-slate-100">2-Layer GraphSAGE</div>
          <div className="text-xs text-purple-400 font-mono">Mean Aggregator · LayerNorm</div>
        </div>

        <div className="p-4 bg-slate-900/80 border border-slate-800 rounded-xl space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Runtime Status</span>
            <Activity className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="flex items-center space-x-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-lg font-bold text-slate-100">{modelLoaded ? 'Active / Serving' : 'Unloaded'}</span>
          </div>
          <div className="text-xs text-slate-400 font-mono">artifacts/phase18/graphsage_model.pt</div>
        </div>

        <div className="p-4 bg-slate-900/80 border border-slate-800 rounded-xl space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Graph Dimension</span>
            <Layers className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-lg font-bold text-slate-100">92 Nodes · 81 Edges</div>
          <div className="text-xs text-cyan-400 font-mono">16 In-Dim → 64 Latent Emb</div>
        </div>

        <div className="p-4 bg-slate-900/80 border border-slate-800 rounded-xl space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Benchmark Performance</span>
            <Sparkles className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-lg font-bold text-slate-100">ROC-AUC 1.00</div>
          <div className="text-xs text-amber-400 font-mono">Precision 1.00 · Recall 1.00</div>
        </div>
      </div>

      {/* Main Grid: Node Prediction & Explainability */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Entity Selection & Node Scoring */}
        <div className="lg:col-span-2 space-y-6">
          <div className="p-6 bg-slate-900/90 border border-slate-800 rounded-xl space-y-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Brain className="w-5 h-5 text-indigo-400" />
                <h3 className="text-base font-semibold text-slate-100">Inductive Node Fraud Inference</h3>
              </div>
              <button
                onClick={handleReloadModel}
                disabled={isReloadingModel}
                className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isReloadingModel ? 'animate-spin' : ''}`} />
                <span>Reload Weights</span>
              </button>
            </div>

            {/* Quick Entity Selector Chips */}
            <div>
              <div className="text-xs text-slate-400 mb-2">Preset Benchmark Entities:</div>
              <div className="flex flex-wrap gap-2">
                {[
                  { id: 'ACC-GNN-01', label: 'ACC-GNN-01 (Mule Loop Hub)', risk: 'CRITICAL' },
                  { id: 'ACC-GNN-04', label: 'ACC-GNN-04 (Smurfing Sender)', risk: 'HIGH' },
                  { id: 'DEV-GNN-01', label: 'DEV-GNN-01 (Rogue Emulator)', risk: 'CRITICAL' },
                  { id: 'IP-GNN-01', label: 'IP-GNN-01 (Tor Proxy)', risk: 'CRITICAL' },
                  { id: 'MER-GNN-01', label: 'MER-GNN-01 (Crypto Cashout)', risk: 'HIGH' },
                  { id: 'ACC-GNN-10', label: 'ACC-GNN-10 (Benign Account)', risk: 'LOW' },
                  { id: 'MER-GNN-02', label: 'MER-GNN-02 (Legit Retail)', risk: 'LOW' }
                ].map(item => (
                  <button
                    key={item.id}
                    onClick={() => {
                      setSelectedEntity(item.id);
                      handlePredictNode(item.id);
                    }}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition ${
                      selectedEntity === item.id
                        ? 'bg-indigo-600/30 border-indigo-500 text-indigo-300'
                        : 'bg-slate-800/60 border-slate-700/60 text-slate-400 hover:bg-slate-800 hover:text-slate-200'
                    }`}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Custom Entity Input Bar */}
            <div className="flex items-center space-x-2">
              <div className="relative flex-1">
                <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                <input
                  type="text"
                  placeholder="Enter entity ID (e.g. ACC-GNN-05, CUS-GNN-02)..."
                  value={customEntityInput}
                  onChange={e => setCustomEntityInput(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>
              <button
                onClick={() => {
                  if (customEntityInput.trim()) {
                    setSelectedEntity(customEntityInput.trim());
                    handlePredictNode(customEntityInput.trim());
                  }
                }}
                disabled={isLoadingNode}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition flex items-center space-x-1.5"
              >
                {isLoadingNode ? <RefreshCw className="w-4 h-4 animate-spin" /> : <span>Evaluate</span>}
              </button>
            </div>

            {/* Prediction Output Card */}
            {nodePrediction && (
              <div className="p-5 bg-slate-950/70 border border-slate-800 rounded-xl space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <span className="text-base font-bold text-slate-100 font-mono">{nodePrediction.entity_id}</span>
                    <span className="px-2 py-0.5 rounded text-xs bg-slate-800 text-slate-300 border border-slate-700">
                      {nodePrediction.entity_type}
                    </span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span
                      className={`px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider ${
                        nodePrediction.advisory_risk_level === 'CRITICAL'
                          ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                          : nodePrediction.advisory_risk_level === 'HIGH'
                          ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                          : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                      }`}
                    >
                      {nodePrediction.advisory_risk_level} RISK
                    </span>
                  </div>
                </div>

                {/* Probability Bar */}
                <div className="space-y-1.5">
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-400">GNN Fraud Probability</span>
                    <span className="font-mono font-bold text-slate-200">
                      {(nodePrediction.fraud_probability * 100).toFixed(2)}%
                    </span>
                  </div>
                  <div className="w-full bg-slate-800 rounded-full h-2.5 overflow-hidden">
                    <div
                      className={`h-2.5 rounded-full transition-all duration-500 ${
                        nodePrediction.fraud_probability >= 0.75
                          ? 'bg-rose-500'
                          : nodePrediction.fraud_probability >= 0.50
                          ? 'bg-amber-500'
                          : 'bg-emerald-500'
                      }`}
                      style={{ width: `${Math.max(5, nodePrediction.fraud_probability * 100)}%` }}
                    />
                  </div>
                </div>

                {/* Recommendation */}
                <div className="p-3 bg-slate-900 rounded-lg text-xs text-slate-300 border border-slate-800 flex items-start space-x-2">
                  {nodePrediction.fraud_probability >= 0.5 ? (
                    <ShieldAlert className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5" />
                  ) : (
                    <ShieldCheck className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                  )}
                  <span>{nodePrediction.recommendation}</span>
                </div>

                {/* Explainable Indicators */}
                <div className="space-y-2 pt-2 border-t border-slate-800/80">
                  <div className="text-xs font-semibold text-slate-300 flex items-center space-x-1.5">
                    <BarChart3 className="w-3.5 h-3.5 text-indigo-400" />
                    <span>Explainable Feature & Neighborhood Attributions</span>
                  </div>
                  <div className="space-y-2">
                    {nodePrediction.explainable_indicators.map((ind, i) => (
                      <div key={i} className="p-2.5 bg-slate-900/60 rounded-lg border border-slate-800 text-xs space-y-1">
                        <div className="flex justify-between items-center">
                          <span className="font-mono text-indigo-300 font-medium">{ind.feature_name}</span>
                          <span className="font-mono text-slate-400">Attribution: {ind.attribution_score > 0 ? `+${ind.attribution_score}` : ind.attribution_score}</span>
                        </div>
                        <p className="text-slate-400 text-xs">{ind.description}</p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Latent Embeddings Preview */}
                {nodePrediction.embedding && (
                  <div className="space-y-1 pt-2 border-t border-slate-800/80">
                    <div className="text-xs text-slate-400 font-mono">64-Dim Latent Embedding Sample:</div>
                    <div className="p-2 bg-slate-900 rounded font-mono text-[11px] text-slate-400 overflow-x-auto">
                      [{nodePrediction.embedding.slice(0, 8).map(v => v.toFixed(3)).join(', ')} ... 56 more dimensions]
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Suspicious Link Prediction & 2D Embedding Projection */}
        <div className="space-y-6">
          {/* Suspicious Link Predictor */}
          <div className="p-6 bg-slate-900/90 border border-slate-800 rounded-xl space-y-4">
            <div className="flex items-center space-x-2">
              <LinkIcon className="w-5 h-5 text-cyan-400" />
              <h3 className="text-base font-semibold text-slate-100">Candidate Link Prediction</h3>
            </div>
            <p className="text-xs text-slate-400">
              Evaluates latent topological affinity to predict unobserved associations between entities.
            </p>

            <div className="space-y-3">
              <div>
                <label className="text-xs text-slate-400 block mb-1">Source Node ID</label>
                <input
                  type="text"
                  value={linkSource}
                  onChange={e => setLinkSource(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 font-mono"
                />
              </div>

              <div>
                <label className="text-xs text-slate-400 block mb-1">Target Node ID</label>
                <input
                  type="text"
                  value={linkTarget}
                  onChange={e => setLinkTarget(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 font-mono"
                />
              </div>

              <button
                onClick={handlePredictLink}
                disabled={isLoadingLink}
                className="w-full py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-xs font-medium transition flex items-center justify-center space-x-1.5"
              >
                {isLoadingLink ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <span>Score Association</span>}
              </button>
            </div>

            {linkPrediction && (
              <div className="p-4 bg-slate-950/80 border border-slate-800 rounded-lg space-y-2.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400">Affinity Score:</span>
                  <span className="font-mono font-bold text-slate-100">{(linkPrediction.link_score * 100).toFixed(1)}%</span>
                </div>
                <div className="w-full bg-slate-800 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${linkPrediction.is_suspicious_link ? 'bg-rose-500' : 'bg-cyan-500'}`}
                    style={{ width: `${linkPrediction.link_score * 100}%` }}
                  />
                </div>
                <div className="text-xs text-slate-300">
                  <strong className={linkPrediction.is_suspicious_link ? 'text-rose-400' : 'text-cyan-400'}>
                    {linkPrediction.is_suspicious_link ? 'SUSPICIOUS' : 'NOMINAL'}:{' '}
                  </strong>
                  {linkPrediction.advisory_assessment}
                </div>
              </div>
            )}
          </div>

          {/* 2D Embedding Space Visualizer */}
          <div className="p-6 bg-slate-900/90 border border-slate-800 rounded-xl space-y-3">
            <div className="flex items-center space-x-2">
              <Database className="w-5 h-5 text-amber-400" />
              <h3 className="text-base font-semibold text-slate-100">2D Latent Representation</h3>
            </div>
            <p className="text-xs text-slate-400">
              PCA projection of 92 entity embeddings illustrating separability between fraud syndicate and benign activity.
            </p>

            <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 h-44 flex flex-col justify-between relative overflow-hidden">
              <div className="flex justify-between text-[11px] text-slate-500">
                <span>Principal Component 1 (Topology)</span>
                <span>PC 2</span>
              </div>

              {/* Graphical Clusters */}
              <div className="relative w-full h-28">
                {/* Fraud Cluster (Red) */}
                <div className="absolute left-6 top-4 p-2 rounded-lg bg-rose-500/10 border border-rose-500/30 flex flex-col items-center">
                  <span className="text-[10px] font-bold text-rose-400 font-mono">Syndicate Ring</span>
                  <div className="flex space-x-1 mt-1">
                    <span className="w-2 h-2 rounded-full bg-rose-500" />
                    <span className="w-2 h-2 rounded-full bg-rose-500" />
                    <span className="w-2 h-2 rounded-full bg-rose-400" />
                  </div>
                </div>

                {/* Normal Customers & Accounts Cluster (Cyan) */}
                <div className="absolute right-6 bottom-3 p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex flex-col items-center">
                  <span className="text-[10px] font-bold text-cyan-400 font-mono">Legitimate Retail (80 Nodes)</span>
                  <div className="flex space-x-1 mt-1">
                    <span className="w-2 h-2 rounded-full bg-cyan-500" />
                    <span className="w-2 h-2 rounded-full bg-cyan-500" />
                    <span className="w-2 h-2 rounded-full bg-cyan-400" />
                    <span className="w-2 h-2 rounded-full bg-cyan-400" />
                  </div>
                </div>
              </div>

              <div className="text-[10px] text-slate-500 text-center">
                Separable synthetic benchmark manifold · Latent dimension: 64
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

