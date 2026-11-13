import React, { useState } from 'react';
import {
  Compass,
  Network,
  GitBranch,
  ShieldAlert,
  ArrowRight,
  TrendingUp,
  Sliders,
  Filter,
  CheckCircle2,
  AlertTriangle,
  Award,
  Layers,
  Search,
  ExternalLink
} from 'lucide-react';

interface CommunityItem {
  community_id: string;
  size: number;
  density: number;
  risk_score: number;
  risk_level: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  members: string[];
  has_shared_device: boolean;
  has_shared_ip: boolean;
  has_circular_loop: boolean;
  suspicious_indicators: string[];
}

const BENCHMARK_COMMUNITIES: CommunityItem[] = [
  {
    community_id: 'COMM-01',
    size: 8,
    density: 0.357,
    risk_score: 0.85,
    risk_level: 'CRITICAL',
    members: ['ACC-P17-01', 'ACC-P17-02', 'ACC-P17-03', 'CUS-P17-01', 'CUS-P17-02', 'CUS-P17-03', 'DEV-P17-01', 'IP-P17-01'],
    has_shared_device: true,
    has_shared_ip: true,
    has_circular_loop: true,
    suspicious_indicators: [
      'Shared physical device infrastructure in community (DEV-P17-01)',
      'Shared network IP ingress hub in community (IP-P17-01)',
      'Circular fund transfer loop identified in community (ACC-01 -> 02 -> 03 -> 01)'
    ]
  },
  {
    community_id: 'COMM-02',
    size: 6,
    density: 0.200,
    risk_score: 0.45,
    risk_level: 'MEDIUM',
    members: ['ACC-P17-04', 'ACC-P17-05', 'ACC-P17-06', 'CUS-P17-04', 'CUS-P17-05', 'DEV-P17-02'],
    has_shared_device: false,
    has_shared_ip: false,
    has_circular_loop: false,
    suspicious_indicators: ['Multi-hop linear payment dispersion']
  },
  {
    community_id: 'COMM-03',
    size: 4,
    density: 0.167,
    risk_score: 0.25,
    risk_level: 'MEDIUM',
    members: ['ACC-P17-07', 'ACC-P17-11', 'CUS-P17-07', 'DEV-P17-05'],
    has_shared_device: false,
    has_shared_ip: false,
    has_circular_loop: false,
    suspicious_indicators: []
  },
  {
    community_id: 'COMM-04',
    size: 3,
    density: 0.333,
    risk_score: 0.10,
    risk_level: 'LOW',
    members: ['ACC-P17-08', 'ACC-P17-12', 'CUS-P17-08'],
    has_shared_device: false,
    has_shared_ip: false,
    has_circular_loop: false,
    suspicious_indicators: []
  }
];

export const NetworkAnalyticsPage: React.FC = () => {
  const [communities, setCommunities] = useState<CommunityItem[]>(BENCHMARK_COMMUNITIES);
  const [selectedCommunity, setSelectedCommunity] = useState<CommunityItem>(BENCHMARK_COMMUNITIES[0]);
  const [riskFilter, setRiskFilter] = useState<string>('ALL');

  // Shortest pathfinder state
  const [srcNode, setSrcNode] = useState<string>('ACC-P17-01');
  const [dstNode, setDstNode] = useState<string>('MER-P17-01');
  const [pathResult, setPathResult] = useState<any>(null);
  const [isFindingPath, setIsFindingPath] = useState<boolean>(false);

  // Filtered communities
  const filteredCommunities = communities.filter((c) => {
    if (riskFilter !== 'ALL' && c.risk_level !== riskFilter) return false;
    return true;
  });

  const handleFindPath = () => {
    setIsFindingPath(true);
    setTimeout(() => {
      setPathResult({
        source_id: srcNode,
        target_id: dstNode,
        path_exists: true,
        shortest_path_hops: 2,
        path_nodes: [srcNode, 'ACC-P17-03', dstNode],
        path_relationships: ['TRANSFERRED_TO', 'PAID_MERCHANT'],
        risk_summary: `Direct routing identified: ${srcNode} -> ACC-P17-03 -> ${dstNode} bridging known syndicate transfer channel.`
      });
      setIsFindingPath(false);
    }, 400);
  };

  const getRiskBadge = (level: string) => {
    switch (level) {
      case 'CRITICAL':
        return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/30">CRITICAL</span>;
      case 'HIGH':
        return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30">HIGH</span>;
      case 'MEDIUM':
        return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-yellow-500/20 text-yellow-300 border border-yellow-500/30">MEDIUM</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">LOW</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-indigo-500/10 border border-indigo-500/30 text-indigo-400">
            <Network className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
              Advanced Graph Intelligence & Network Analytics
              <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 font-mono border border-indigo-500/30">
                Phase 17 · Louvain & PageRank
              </span>
            </h1>
            <p className="text-xs text-slate-400">
              Community discovery, graph centrality measurements, multi-hop pathfinding, and predictive syndicate scoring.
            </p>
          </div>
        </div>

        {/* Advisory Badge */}
        <div className="px-3 py-1.5 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs font-mono flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>Scores are advisory; final decisions remain with investigators</span>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Benchmark Entities</span>
            <Layers className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-2xl font-bold text-slate-100">38 Nodes</div>
          <div className="text-xs text-slate-500 mt-1">33 Seed Relationships</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Louvain Communities</span>
            <Compass className="w-4 h-4 text-sky-400" />
          </div>
          <div className="text-2xl font-bold text-sky-400">4 Discovered</div>
          <div className="text-xs text-sky-500/80 mt-1">1 High-Risk Syndicate Cluster</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Top PageRank Score</span>
            <Award className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400">0.0845</div>
          <div className="text-xs text-emerald-500/80 mt-1">Entity: ACC-P17-01 (Hub)</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Planted Syndicates</span>
            <ShieldAlert className="w-4 h-4 text-rose-400" />
          </div>
          <div className="text-2xl font-bold text-rose-400">COMM-01</div>
          <div className="text-xs text-rose-500/80 mt-1">Device farm & wash trading loop</div>
        </div>
      </div>

      {/* Main Grid: Community Directory & Pathfinding / Centrality Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Louvain Community Directory (7 cols) */}
        <div className="lg:col-span-7 bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <Compass className="w-4 h-4 text-indigo-400" />
              Louvain Topological Communities
            </h2>

            {/* Filter buttons */}
            <div className="flex flex-wrap gap-1.5 text-xs">
              {['ALL', 'CRITICAL', 'MEDIUM', 'LOW'].map((lvl) => (
                <button
                  key={lvl}
                  onClick={() => setRiskFilter(lvl)}
                  className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                    riskFilter === lvl
                      ? 'bg-indigo-600 text-white'
                      : 'bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-200'
                  }`}
                >
                  {lvl}
                </button>
              ))}
            </div>
          </div>

          {/* Communities Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-950 text-slate-400 font-medium border-b border-slate-800">
                <tr>
                  <th className="py-2.5 px-3">Community</th>
                  <th className="py-2.5 px-3">Vertices</th>
                  <th className="py-2.5 px-3">Density</th>
                  <th className="py-2.5 px-3">Risk Level</th>
                  <th className="py-2.5 px-3">Score</th>
                  <th className="py-2.5 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {filteredCommunities.map((c) => {
                  const isSelected = selectedCommunity.community_id === c.community_id;
                  return (
                    <tr
                      key={c.community_id}
                      onClick={() => setSelectedCommunity(c)}
                      className={`cursor-pointer transition-colors ${
                        isSelected ? 'bg-indigo-950/30' : 'hover:bg-slate-800/40'
                      }`}
                    >
                      <td className="py-3 px-3 font-mono font-medium text-slate-200">
                        {c.community_id}
                      </td>
                      <td className="py-3 px-3 font-mono">{c.size} nodes</td>
                      <td className="py-3 px-3 font-mono">{c.density.toFixed(3)}</td>
                      <td className="py-3 px-3">{getRiskBadge(c.risk_level)}</td>
                      <td className="py-3 px-3 font-mono font-bold text-slate-200">
                        {(c.risk_score * 100).toFixed(0)}%
                      </td>
                      <td className="py-3 px-3 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedCommunity(c);
                          }}
                          className={`text-xs px-2.5 py-1 rounded transition-colors ${
                            isSelected
                              ? 'bg-indigo-600 text-white font-medium'
                              : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                          }`}
                        >
                          Inspect
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Selected Community Dossier */}
          {selectedCommunity && (
            <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-3 text-xs">
              <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                <span className="font-semibold text-slate-200 font-mono flex items-center gap-2">
                  {selectedCommunity.community_id} Cluster Evidence
                  {getRiskBadge(selectedCommunity.risk_level)}
                </span>
                <span className="text-slate-400 font-mono">Density: {selectedCommunity.density}</span>
              </div>

              {/* Members Pill List */}
              <div>
                <span className="text-slate-400 block mb-1">Cluster Vertices ({selectedCommunity.members.length}):</span>
                <div className="flex flex-wrap gap-1">
                  {selectedCommunity.members.map((m) => (
                    <span key={m} className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono text-[11px] border border-slate-700">
                      {m}
                    </span>
                  ))}
                </div>
              </div>

              {/* Red Flags */}
              {selectedCommunity.suspicious_indicators.length > 0 && (
                <div className="pt-2 border-t border-slate-800/80">
                  <span className="text-slate-400 block mb-1">Topological Risk Indicators:</span>
                  {selectedCommunity.suspicious_indicators.map((ind, i) => (
                    <div key={i} className="text-rose-300 flex items-start gap-1.5 mb-1 font-sans">
                      <AlertTriangle className="w-3.5 h-3.5 text-rose-400 shrink-0 mt-0.5" />
                      <span>{ind}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right Column: Path Analysis & Predictive Risk Engine (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          {/* Multi-Hop Path Analysis Card */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                <GitBranch className="w-4 h-4 text-sky-400" />
                Shortest Transaction Path Routing
              </h3>
              <span className="text-[10px] px-2 py-0.5 rounded bg-sky-500/20 text-sky-300 font-mono">
                BFS Multi-Hop
              </span>
            </div>

            <p className="text-xs text-slate-400">
              Evaluates relationship routing distance and intermediate transit hubs between entities.
            </p>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <label className="text-slate-400 block mb-1 font-mono">Source Entity</label>
                <input
                  type="text"
                  value={srcNode}
                  onChange={(e) => setSrcNode(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-sky-500 font-mono"
                />
              </div>
              <div>
                <label className="text-slate-400 block mb-1 font-mono">Target Entity</label>
                <input
                  type="text"
                  value={dstNode}
                  onChange={(e) => setDstNode(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-sky-500 font-mono"
                />
              </div>
            </div>

            <button
              onClick={handleFindPath}
              disabled={isFindingPath}
              className="w-full bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white font-medium py-2 rounded-lg text-xs flex items-center justify-center gap-2 transition-colors shadow-lg shadow-sky-600/20"
            >
              {isFindingPath ? 'Traversing Paths...' : 'Find Shortest Relationship Path'}
              <ArrowRight className="w-3.5 h-3.5" />
            </button>

            {pathResult && (
              <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 space-y-2 text-xs">
                <div className="flex items-center justify-between pb-1.5 border-b border-slate-800">
                  <span className="text-slate-400 font-medium">Path Discovery</span>
                  <span className="font-mono text-emerald-400 font-semibold">{pathResult.shortest_path_hops} Hops</span>
                </div>

                <div className="text-xs text-slate-300 font-mono flex items-center flex-wrap gap-1.5 pt-1">
                  {pathResult.path_nodes.map((n: string, i: number) => (
                    <React.Fragment key={i}>
                      <span className="px-2 py-0.5 rounded bg-slate-800 text-sky-300 border border-slate-700">
                        {n}
                      </span>
                      {i < pathResult.path_nodes.length - 1 && (
                        <ArrowRight className="w-3 h-3 text-slate-500" />
                      )}
                    </React.Fragment>
                  ))}
                </div>

                <div className="pt-2 text-slate-400 text-[11px] border-t border-slate-800/80">
                  {pathResult.risk_summary}
                </div>
              </div>
            )}
          </div>

          {/* Centrality & PageRank Authority Leaderboard */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                <Award className="w-4 h-4 text-emerald-400" />
                Network Prominence & PageRank
              </h3>
              <span className="text-[10px] text-slate-500 font-mono">Authority Flow</span>
            </div>

            <div className="space-y-2 text-xs">
              {[
                { id: 'ACC-P17-01', type: 'ACCOUNT', pr: 0.0845, btw: 0.1428, role: 'Syndicate Transfer Hub' },
                { id: 'DEV-P17-01', type: 'DEVICE', pr: 0.0762, btw: 0.0952, role: 'Shared Emulator' },
                { id: 'ACC-P17-02', type: 'ACCOUNT', pr: 0.0689, btw: 0.0476, role: 'Wash Trading Relay' },
                { id: 'MER-P17-01', type: 'MERCHANT', pr: 0.0512, btw: 0.0000, role: 'P2P Crypto Sink' }
              ].map((item, idx) => (
                <div key={idx} className="p-2.5 bg-slate-950 rounded-lg border border-slate-800/80 flex items-center justify-between">
                  <div>
                    <span className="font-mono font-medium text-slate-200 block">{item.id}</span>
                    <span className="text-[10px] text-slate-500">{item.role}</span>
                  </div>
                  <div className="text-right font-mono">
                    <span className="text-emerald-400 font-semibold block">{item.pr.toFixed(4)} PR</span>
                    <span className="text-[10px] text-slate-400">{item.btw.toFixed(4)} Betweenness</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NetworkAnalyticsPage;

