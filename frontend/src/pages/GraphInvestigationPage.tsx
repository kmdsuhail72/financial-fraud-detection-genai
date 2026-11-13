import React, { useState, useEffect } from 'react';
import {
  Share2,
  Search,
  RefreshCw,
  ShieldAlert,
  Layers,
  Smartphone,
  Globe,
  CreditCard,
  User,
  ShoppingBag,
  ExternalLink,
  Zap,
  Activity,
  Sliders,
  CheckCircle2,
  AlertTriangle,
  ArrowRight
} from 'lucide-react';

interface NetworkNode {
  id: string;
  type: 'CUSTOMER' | 'ACCOUNT' | 'DEVICE' | 'IP_ADDRESS' | 'MERCHANT';
  label: string;
  x: number;
  y: number;
  riskScore: number;
}

interface NetworkLink {
  source: string;
  target: string;
  type: string;
  weight?: number;
}

const SEED_NODES: NetworkNode[] = [
  // Syndicate Ring 1 - Device Farming
  { id: 'CUS-RING1-001', type: 'CUSTOMER', label: 'Customer 1', x: 180, y: 120, riskScore: 0.88 },
  { id: 'CUS-RING1-002', type: 'CUSTOMER', label: 'Customer 2', x: 260, y: 80, riskScore: 0.85 },
  { id: 'CUS-RING1-003', type: 'CUSTOMER', label: 'Customer 3', x: 340, y: 120, riskScore: 0.82 },
  { id: 'ACC-RING1-001', type: 'ACCOUNT', label: 'Acc #1', x: 200, y: 220, riskScore: 0.86 },
  { id: 'ACC-RING1-002', type: 'ACCOUNT', label: 'Acc #2', x: 260, y: 200, riskScore: 0.84 },
  { id: 'ACC-RING1-003', type: 'ACCOUNT', label: 'Acc #3', x: 320, y: 220, riskScore: 0.80 },
  { id: 'DEV-ROGUE-EMULATOR-88', type: 'DEVICE', label: 'Rogue Emulator 88', x: 260, y: 320, riskScore: 0.95 },
  { id: 'IP-198.51.100.77', type: 'IP_ADDRESS', label: '198.51.100.77', x: 150, y: 350, riskScore: 0.75 },

  // Circular Mule Loop
  { id: 'ACC-LOOP-A', type: 'ACCOUNT', label: 'Loop Acc A', x: 500, y: 120, riskScore: 0.78 },
  { id: 'ACC-LOOP-B', type: 'ACCOUNT', label: 'Loop Acc B', x: 620, y: 120, riskScore: 0.76 },
  { id: 'ACC-LOOP-C', type: 'ACCOUNT', label: 'Loop Acc C', x: 560, y: 230, riskScore: 0.79 },
  { id: 'CUS-MULE-1', type: 'CUSTOMER', label: 'Mule Lead A', x: 480, y: 40, riskScore: 0.70 },

  // Fan-In Mule Collector
  { id: 'ACC-COLLECTOR-999', type: 'ACCOUNT', label: 'Collector Mule 999', x: 550, y: 380, riskScore: 0.89 },
  { id: 'ACC-SMURF-1', type: 'ACCOUNT', label: 'Smurf 1', x: 420, y: 340, riskScore: 0.65 },
  { id: 'ACC-SMURF-2', type: 'ACCOUNT', label: 'Smurf 2', x: 440, y: 420, riskScore: 0.62 },
  { id: 'MER-CRYPTO-DESK', type: 'MERCHANT', label: 'P2P Crypto Desk', x: 670, y: 380, riskScore: 0.80 },
];

const SEED_LINKS: NetworkLink[] = [
  // Syndicate Links
  { source: 'CUS-RING1-001', target: 'ACC-RING1-001', type: 'OWNS_ACCOUNT' },
  { source: 'CUS-RING1-002', target: 'ACC-RING1-002', type: 'OWNS_ACCOUNT' },
  { source: 'CUS-RING1-003', target: 'ACC-RING1-003', type: 'OWNS_ACCOUNT' },
  { source: 'ACC-RING1-001', target: 'DEV-ROGUE-EMULATOR-88', type: 'USES_DEVICE' },
  { source: 'ACC-RING1-002', target: 'DEV-ROGUE-EMULATOR-88', type: 'USES_DEVICE' },
  { source: 'ACC-RING1-003', target: 'DEV-ROGUE-EMULATOR-88', type: 'USES_DEVICE' },
  { source: 'ACC-RING1-001', target: 'IP-198.51.100.77', type: 'ASSOCIATED_IP' },
  { source: 'ACC-RING1-002', target: 'IP-198.51.100.77', type: 'ASSOCIATED_IP' },

  // Circular Mule Loop Links
  { source: 'CUS-MULE-1', target: 'ACC-LOOP-A', type: 'OWNS_ACCOUNT' },
  { source: 'ACC-LOOP-A', target: 'ACC-LOOP-B', type: 'TRANSFERRED_TO', weight: 9800 },
  { source: 'ACC-LOOP-B', target: 'ACC-LOOP-C', type: 'TRANSFERRED_TO', weight: 9800 },
  { source: 'ACC-LOOP-C', target: 'ACC-LOOP-A', type: 'TRANSFERRED_TO', weight: 9800 },

  // Fan-in Links
  { source: 'ACC-SMURF-1', target: 'ACC-COLLECTOR-999', type: 'TRANSFERRED_TO', weight: 2950 },
  { source: 'ACC-SMURF-2', target: 'ACC-COLLECTOR-999', type: 'TRANSFERRED_TO', weight: 3100 },
  { source: 'ACC-COLLECTOR-999', target: 'MER-CRYPTO-DESK', type: 'PAID_MERCHANT', weight: 6000 },
];

export const GraphInvestigationPage: React.FC = () => {
  const [nodes, setNodes] = useState<NetworkNode[]>(SEED_NODES);
  const [links, setLinks] = useState<NetworkLink[]>(SEED_LINKS);
  const [selectedNode, setSelectedNode] = useState<NetworkNode>(SEED_NODES[6]); // DEV-ROGUE-EMULATOR-88
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [depthHops, setDepthHops] = useState<number>(2);
  const [typeFilter, setTypeFilter] = useState<string>('ALL');
  const [isEnriching, setIsEnriching] = useState<boolean>(false);
  const [enrichmentResult, setEnrichmentResult] = useState<any>(null);

  // Filtered nodes
  const filteredNodes = nodes.filter((n) => {
    if (typeFilter !== 'ALL' && n.type !== typeFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return n.id.toLowerCase().includes(q) || n.label.toLowerCase().includes(q);
    }
    return true;
  });

  const getNodeColor = (type: string) => {
    switch (type) {
      case 'CUSTOMER':
        return '#38bdf8'; // Sky 400
      case 'ACCOUNT':
        return '#34d399'; // Emerald 400
      case 'DEVICE':
        return '#c084fc'; // Purple 400
      case 'IP_ADDRESS':
        return '#fbbf24'; // Amber 400
      case 'MERCHANT':
        return '#fb7185'; // Rose 400
      default:
        return '#94a3b8'; // Slate 400
    }
  };

  const handleEnrich = () => {
    setIsEnriching(true);
    setTimeout(() => {
      const isSyndicate = selectedNode.id.includes('EMULATOR') || selectedNode.id.includes('RING');
      const isLoop = selectedNode.id.includes('LOOP');
      const isCollector = selectedNode.id.includes('COLLECTOR');

      const riskScore = isSyndicate ? 0.92 : isLoop ? 0.84 : isCollector ? 0.88 : 0.12;
      const riskLevel = riskScore >= 0.80 ? 'CRITICAL' : riskScore >= 0.50 ? 'HIGH' : 'LOW';

      const factors: string[] = [];
      if (isSyndicate) factors.push('Device shared across 3 distinct accounts (Device Farming)');
      if (isLoop) factors.push('Account participates in 3-hop circular wash transfer cycle');
      if (isCollector) factors.push('High fan-in mule consolidation: inbound velocity ratio 5.0x');
      if (!isSyndicate && !isLoop && !isCollector) factors.push('Nominal standalone graph topology');

      setEnrichmentResult({
        transaction_id: `TXN-ENRICH-${selectedNode.id.replace(/[^a-zA-Z0-9]/g, '')}`,
        graph_risk_score: riskScore,
        risk_level: riskLevel,
        features: {
          graph_degree_centrality: isCollector ? 6.0 : 3.0,
          graph_shared_device_count: isSyndicate ? 3.0 : 1.0,
          graph_circular_flow_flag: isLoop ? 1.0 : 0.0,
          graph_network_risk_score: riskScore
        },
        factors,
        phase7_ready: true
      });
      setIsEnriching(false);
    }, 450);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-sky-500/10 border border-sky-500/30 text-sky-400">
            <Share2 className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
              Enterprise Graph Network Intelligence
              <span className="text-xs px-2 py-0.5 rounded-full bg-sky-500/20 text-sky-300 font-mono border border-sky-500/30">
                Phase 16 · Amazon Neptune
              </span>
            </h1>
            <p className="text-xs text-slate-400">
              Persistent Gremlin traversals, real-time Kinesis relationship streaming, and Phase 7 fraud risk enrichment.
            </p>
          </div>
        </div>

        {/* Live Cluster Status Pill */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          <span className="text-slate-300 font-medium font-mono">Neptune Cluster: Active</span>
          <span className="text-slate-500">|</span>
          <span className="text-slate-400 font-mono">Port 8182</span>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Graph Vertices</span>
            <Layers className="w-4 h-4 text-sky-400" />
          </div>
          <div className="text-2xl font-bold text-slate-100">{nodes.length}</div>
          <div className="text-xs text-slate-500 mt-1">Customers, Accounts, Devices, IPs</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Relationship Edges</span>
            <Share2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400">{links.length}</div>
          <div className="text-xs text-emerald-500/80 mt-1">OWNS, USES_DEVICE, TRANSFERS</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Detected Fraud Rings</span>
            <ShieldAlert className="w-4 h-4 text-rose-400" />
          </div>
          <div className="text-2xl font-bold text-rose-400">3 Syndicates</div>
          <div className="text-xs text-rose-500/80 mt-1">Device farm, mule loop, fan-in</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Stream Ingestion</span>
            <Activity className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-amber-400">Kinesis Active</div>
          <div className="text-xs text-amber-500/80 mt-1">Idempotent Lambda Sync</div>
        </div>
      </div>

      {/* Main Graph Canvas & Investigation Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Interactive Graph Canvas (8 cols) */}
        <div className="lg:col-span-8 bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
          {/* Controls Bar */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div className="relative flex-1 sm:w-64">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-500" />
              <input
                type="text"
                placeholder="Search entity (e.g. EMULATOR, CUS-RING1)..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-sky-500 font-mono"
              />
            </div>

            {/* Filter buttons */}
            <div className="flex flex-wrap items-center gap-1.5 text-xs">
              {['ALL', 'CUSTOMER', 'ACCOUNT', 'DEVICE', 'IP_ADDRESS'].map((t) => (
                <button
                  key={t}
                  onClick={() => setTypeFilter(t)}
                  className={`px-2 py-1 rounded-md text-xs font-medium transition-colors ${
                    typeFilter === t
                      ? 'bg-sky-600 text-white'
                      : 'bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-200'
                  }`}
                >
                  {t.replace('_', ' ')}
                </button>
              ))}
            </div>
          </div>

          {/* SVG Visualizer Canvas */}
          <div className="relative w-full h-[480px] bg-slate-950 rounded-xl border border-slate-800/80 overflow-hidden shadow-inner">
            <svg className="w-full h-full">
              <defs>
                <marker
                  id="arrow"
                  viewBox="0 0 10 10"
                  refX="18"
                  refY="5"
                  markerWidth="5"
                  markerHeight="5"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#64748b" />
                </marker>
              </defs>

              {/* Render Relationship Edges */}
              {links.map((link, idx) => {
                const src = nodes.find((n) => n.id === link.source);
                const tgt = nodes.find((n) => n.id === link.target);
                if (!src || !tgt) return null;

                const isHighlighted =
                  selectedNode.id === link.source || selectedNode.id === link.target;

                return (
                  <g key={`link-${idx}`}>
                    <line
                      x1={src.x}
                      y1={src.y}
                      x2={tgt.x}
                      y2={tgt.y}
                      stroke={isHighlighted ? '#38bdf8' : '#334155'}
                      strokeWidth={isHighlighted ? 2.5 : 1.2}
                      strokeDasharray={link.type === 'TRANSFERRED_TO' ? '4 2' : undefined}
                      markerEnd="url(#arrow)"
                    />
                  </g>
                );
              })}

              {/* Render Entity Nodes */}
              {filteredNodes.map((node) => {
                const isSelected = selectedNode.id === node.id;
                const color = getNodeColor(node.type);

                return (
                  <g
                    key={node.id}
                    onClick={() => setSelectedNode(node)}
                    className="cursor-pointer transition-transform hover:scale-110"
                  >
                    {/* Selection halo */}
                    {isSelected && (
                      <circle
                        cx={node.x}
                        cy={node.y}
                        r="22"
                        fill="none"
                        stroke="#38bdf8"
                        strokeWidth="2.5"
                        strokeDasharray="4 2"
                        className="animate-spin-slow"
                      />
                    )}

                    <circle
                      cx={node.x}
                      cy={node.y}
                      r="14"
                      fill="#0f172a"
                      stroke={color}
                      strokeWidth={isSelected ? 3 : 2}
                    />

                    {/* Node Text Label */}
                    <text
                      x={node.x}
                      y={node.y + 24}
                      fill="#94a3b8"
                      fontSize="10"
                      textAnchor="middle"
                      className="font-mono select-none"
                    >
                      {node.label}
                    </text>
                  </g>
                );
              })}
            </svg>

            {/* Canvas Legend */}
            <div className="absolute bottom-3 left-3 bg-slate-900/90 border border-slate-800 rounded-lg p-2 text-[10px] flex items-center gap-3 backdrop-blur-sm">
              <span className="flex items-center gap-1 text-slate-300">
                <span className="w-2.5 h-2.5 rounded-full bg-sky-400"></span> Customer
              </span>
              <span className="flex items-center gap-1 text-slate-300">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400"></span> Account
              </span>
              <span className="flex items-center gap-1 text-slate-300">
                <span className="w-2.5 h-2.5 rounded-full bg-purple-400"></span> Device
              </span>
              <span className="flex items-center gap-1 text-slate-300">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-400"></span> IP
              </span>
              <span className="flex items-center gap-1 text-slate-300">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-400"></span> Merchant
              </span>
            </div>
          </div>
        </div>

        {/* Right Column: Entity Dossier & Phase 7 Risk Enrichment (4 cols) */}
        <div className="lg:col-span-4 space-y-5">
          {/* Node Details Card */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div>
                <span className="text-[10px] font-mono text-sky-400 block uppercase tracking-wider">
                  {selectedNode.type} VERTEX
                </span>
                <h3 className="text-base font-bold text-slate-100 font-mono">
                  {selectedNode.id}
                </h3>
              </div>
              <div className="text-right">
                <span className="text-[10px] text-slate-400 block">Threat Score</span>
                <span
                  className={`text-lg font-bold font-mono ${
                    selectedNode.riskScore >= 0.8
                      ? 'text-rose-400'
                      : selectedNode.riskScore >= 0.5
                      ? 'text-amber-400'
                      : 'text-emerald-400'
                  }`}
                >
                  {(selectedNode.riskScore * 100).toFixed(0)}/100
                </span>
              </div>
            </div>

            {/* Entity Attributes */}
            <div className="space-y-2 text-xs">
              <div className="flex justify-between py-1 border-b border-slate-800/60">
                <span className="text-slate-400">Label</span>
                <span className="text-slate-200 font-medium">{selectedNode.label}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800/60">
                <span className="text-slate-400">Classification</span>
                <span className="text-slate-200 font-mono">{selectedNode.type}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800/60">
                <span className="text-slate-400">Active Connections</span>
                <span className="text-slate-200 font-mono">
                  {
                    links.filter(
                      (l) => l.source === selectedNode.id || l.target === selectedNode.id
                    ).length
                  }{' '}
                  edges
                </span>
              </div>
            </div>

            {/* Connected Neighbors Pill List */}
            <div className="space-y-1.5 text-xs">
              <span className="text-slate-400 font-medium">Adjacent Vertices</span>
              <div className="flex flex-wrap gap-1">
                {links
                  .filter((l) => l.source === selectedNode.id || l.target === selectedNode.id)
                  .map((l, i) => {
                    const otherId = l.source === selectedNode.id ? l.target : l.source;
                    return (
                      <span
                        key={i}
                        onClick={() => {
                          const targetNode = nodes.find((n) => n.id === otherId);
                          if (targetNode) setSelectedNode(targetNode);
                        }}
                        className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 font-mono text-[10px] border border-slate-700 cursor-pointer transition-colors"
                      >
                        {otherId}
                      </span>
                    );
                  })}
              </div>
            </div>
          </div>

          {/* Phase 7 Real-Time Fraud Scoring Enrichment Card */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                <Zap className="w-4 h-4 text-amber-400" />
                Phase 7 Fraud Scoring Integration
              </h3>
              <span className="text-[10px] px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 font-mono">
                Real-Time
              </span>
            </div>

            <p className="text-xs text-slate-400">
              Extracts graph relationship features from Neptune to enrich the real-time SageMaker fraud inference pipeline.
            </p>

            <button
              onClick={handleEnrich}
              disabled={isEnriching}
              className="w-full bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white font-medium py-2 rounded-lg text-xs flex items-center justify-center gap-2 transition-colors shadow-lg shadow-sky-600/20"
            >
              {isEnriching ? 'Querying Neptune Graph...' : 'Generate Graph Risk Features'}
              <ArrowRight className="w-3.5 h-3.5" />
            </button>

            {enrichmentResult && (
              <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 space-y-2 text-xs">
                <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                  <span className="text-slate-400 font-medium">Network Risk Assessment</span>
                  <span
                    className={`font-mono font-bold px-2 py-0.5 rounded text-[11px] ${
                      enrichmentResult.risk_level === 'CRITICAL'
                        ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                        : enrichmentResult.risk_level === 'HIGH'
                        ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                        : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                    }`}
                  >
                    {enrichmentResult.risk_level} ({(enrichmentResult.graph_risk_score * 100).toFixed(0)}%)
                  </span>
                </div>

                {/* Extracted ML Feature Vector */}
                <div className="grid grid-cols-2 gap-2 text-[11px] font-mono text-slate-400 pt-1">
                  <div>Degree Centrality: <span className="text-sky-300 font-semibold">{enrichmentResult.features.graph_degree_centrality}</span></div>
                  <div>Shared Devices: <span className="text-sky-300 font-semibold">{enrichmentResult.features.graph_shared_device_count}</span></div>
                  <div>Circular Loop: <span className={enrichmentResult.features.graph_circular_flow_flag ? 'text-rose-400' : 'text-emerald-400'}>{enrichmentResult.features.graph_circular_flow_flag ? 'TRUE' : 'FALSE'}</span></div>
                  <div>Composite Score: <span className="text-amber-300 font-semibold">{enrichmentResult.features.graph_network_risk_score}</span></div>
                </div>

                {/* Risk Indicators */}
                <div className="pt-1.5 border-t border-slate-800/80">
                  <span className="text-[10px] text-slate-500 block mb-1">Graph Evidence Indicators:</span>
                  {enrichmentResult.factors.map((f: string, i: number) => (
                    <div key={i} className="text-[11px] text-rose-300 flex items-start gap-1.5 mb-1 font-sans">
                      <AlertTriangle className="w-3.5 h-3.5 text-rose-400 shrink-0 mt-0.5" />
                      <span>{f}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default GraphInvestigationPage;

