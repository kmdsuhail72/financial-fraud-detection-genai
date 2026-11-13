import React, { useState } from 'react';
import {
  Crosshair,
  ShieldAlert,
  Search,
  ExternalLink,
  RefreshCw,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Database,
  Layers,
  Filter,
  ArrowUpRight,
  Hash,
  Globe,
  Radio
} from 'lucide-react';

interface IOCItem {
  ioc_id: string;
  type: string;
  value: string;
  threat_types: string[];
  reputation_score: number;
  confidence: number;
  severity: string;
  status: string;
  mitre_attack: string[];
  source_feeds: string[];
  tags: string[];
}

const DEFAULT_IOCS: IOCItem[] = [
  {
    ioc_id: 'ioc-ipv4-1985110042',
    type: 'ipv4',
    value: '198.51.100.42',
    threat_types: ['c2', 'proxy'],
    reputation_score: 98.0,
    confidence: 0.95,
    severity: 'CRITICAL',
    status: 'ACTIVE',
    mitre_attack: ['T1071', 'T1090'],
    source_feeds: ['FinGuard-Global-Feed', 'AbuseIPDB-Sim', 'AlienVault-OTX-Sim'],
    tags: ['apt29', 'tor-exit', 'bulletproof-host']
  },
  {
    ioc_id: 'ioc-domain-evilbank',
    type: 'domain',
    value: 'evil-bank-login.com',
    threat_types: ['phishing', 'credential_theft'],
    reputation_score: 100.0,
    confidence: 0.98,
    severity: 'CRITICAL',
    status: 'ACTIVE',
    mitre_attack: ['T1566', 'T1078'],
    source_feeds: ['PhishTank-Sim', 'OpenPhish-Sim'],
    tags: ['credential-harvester', 'synthetic-kyc']
  },
  {
    ioc_id: 'ioc-url-secureupdate',
    type: 'url',
    value: 'https://secure-update-verify.net/auth',
    threat_types: ['phishing', 'account_takeover'],
    reputation_score: 90.0,
    confidence: 0.92,
    severity: 'CRITICAL',
    status: 'ACTIVE',
    mitre_attack: ['T1566', 'T1539'],
    source_feeds: ['FinGuard-URLhaus-Sim'],
    tags: ['mfa-bypass-kit', 'adversary-in-the-middle']
  },
  {
    ioc_id: 'ioc-md5-dridex',
    type: 'md5',
    value: '44d88612fea8a8f36de82e1278abb02f',
    threat_types: ['ransomware', 'c2'],
    reputation_score: 100.0,
    confidence: 0.99,
    severity: 'CRITICAL',
    status: 'ACTIVE',
    mitre_attack: ['T1059', 'T1486'],
    source_feeds: ['VirusTotal-Sim', 'MalwareBazaar-Sim'],
    tags: ['trojan.banker.dridex', 'stealer']
  }
];

const MITRE_CATALOG = [
  { id: 'T1078', name: 'Valid Accounts', tactic: 'Initial Access / Defense Evasion', desc: 'Abuse of stolen customer or employee credentials.' },
  { id: 'T1110', name: 'Brute Force', tactic: 'Credential Access', desc: 'Credential stuffing against banking login endpoints.' },
  { id: 'T1071', name: 'Application Layer Protocol', tactic: 'Command and Control', desc: 'Adversary communication via HTTP/HTTPS/DNS.' },
  { id: 'T1566', name: 'Phishing', tactic: 'Initial Access', desc: 'Deceptive messages and credential harvesting landing pages.' },
  { id: 'T1090', name: 'Proxy', tactic: 'Command and Control', desc: 'Traffic routing through open proxies and Tor exit nodes.' },
  { id: 'T1567', name: 'Exfiltration Over Web Service', tactic: 'Exfiltration', desc: 'Exfiltration of customer records to cloud storage.' }
];

export const ThreatIntelPage: React.FC = () => {
  const [iocs, setIocs] = useState<IOCItem[]>(DEFAULT_IOCS);
  const [activeTab, setActiveTab] = useState<'iocs' | 'hunting' | 'mitre'>('iocs');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedType, setSelectedType] = useState('ALL');
  const [newIndicator, setNewIndicator] = useState('');
  const [huntRunning, setHuntRunning] = useState(false);
  const [huntResults, setHuntResults] = useState<any[] | null>(null);

  const filteredIocs = iocs.filter((ioc) => {
    const matchesSearch = ioc.value.toLowerCase().includes(searchTerm.toLowerCase()) ||
      ioc.tags.some((t) => t.toLowerCase().includes(searchTerm.toLowerCase()));
    const matchesType = selectedType === 'ALL' || ioc.type === selectedType.toLowerCase();
    return matchesSearch && matchesType;
  });

  const handleQuickEnrich = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newIndicator.trim()) return;

    const val = newIndicator.trim();
    const isIp = /^[0-9.]+$/.test(val);
    const isUrl = val.startsWith('http');
    const isHash = val.length === 32 || val.length === 64;
    const type = isHash ? 'sha256' : isUrl ? 'url' : isIp ? 'ipv4' : 'domain';

    const newItem: IOCItem = {
      ioc_id: `ioc-${type}-${Date.now()}`,
      type,
      value: val,
      threat_types: ['investigation-lead'],
      reputation_score: 75.0,
      confidence: 0.85,
      severity: 'HIGH',
      status: 'ACTIVE',
      mitre_attack: ['T1071'],
      source_feeds: ['Analyst-Submitted-Feed'],
      tags: ['manual-enrichment']
    };

    setIocs([newItem, ...iocs]);
    setNewIndicator('');
  };

  const handleVerdict = (iocId: string, verdict: 'TP' | 'FP') => {
    setIocs((prev) =>
      prev.map((item) => {
        if (item.ioc_id !== iocId) return item;
        if (verdict === 'FP') {
          return { ...item, reputation_score: 0.0, severity: 'INFO', status: 'REVOKED' };
        } else {
          return { ...item, reputation_score: 100.0, severity: 'CRITICAL', status: 'ACTIVE' };
        }
      })
    );
  };

  const handleRunHunt = () => {
    setHuntRunning(true);
    setTimeout(() => {
      setHuntResults([
        {
          rule_id: 'HUNT-RULE-001',
          rule_name: 'C2 Traffic to Known Proxy and Anonymizer Nodes',
          mitre: 'T1071',
          matched_events: 1,
          ioc: '198.51.100.42',
          summary: 'Matched outbound session to Tor/VPN exit node on event evt-c2-001'
        },
        {
          rule_id: 'HUNT-RULE-002',
          rule_name: 'Anomalous Credential Access and Brute Force',
          mitre: 'T1110',
          matched_events: 1,
          ioc: '192.0.2.77',
          summary: 'Detected brute-force credential stuffing against payment role on event evt-iam-002'
        }
      ]);
      setHuntRunning(false);
    }, 600);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950/60 to-slate-900 border border-slate-800 rounded-xl p-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2 text-indigo-400 font-mono text-xs font-semibold mb-1">
              <Crosshair className="w-4 h-4 text-indigo-400" />
              <span>PHASE 13 THREAT INTELLIGENCE & HUNTING PLATFORM</span>
            </div>
            <h1 className="text-2xl font-bold text-white tracking-tight">
              Threat Intelligence & MITRE ATT&CK Matrix
            </h1>
            <p className="text-sm text-slate-300 mt-1 max-w-2xl">
              Real-time indicator normalization, multi-provider reputation scoring, hypothesis-driven threat hunting, and automated ATT&CK technique mapping.
            </p>
          </div>

          {/* Quick Enrich Form */}
          <form onSubmit={handleQuickEnrich} className="flex items-center gap-2">
            <input
              type="text"
              placeholder="Enrich IP, Domain, Hash..."
              value={newIndicator}
              onChange={(e) => setNewIndicator(e.target.value)}
              className="bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-100 placeholder-slate-500 w-56 focus:outline-none focus:border-indigo-500"
            />
            <button
              type="submit"
              className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-4 py-2 rounded-lg flex items-center gap-1.5 transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Enrich</span>
            </button>
          </form>
        </div>

        {/* Navigation Tabs */}
        <div className="flex items-center gap-2 mt-6 border-b border-slate-800">
          <button
            onClick={() => setActiveTab('iocs')}
            className={`px-4 py-2 text-xs font-semibold rounded-t-lg transition-colors border-b-2 ${
              activeTab === 'iocs'
                ? 'border-indigo-400 text-indigo-300 bg-indigo-950/40'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            IOC Catalog ({iocs.length})
          </button>
          <button
            onClick={() => setActiveTab('hunting')}
            className={`px-4 py-2 text-xs font-semibold rounded-t-lg transition-colors border-b-2 ${
              activeTab === 'hunting'
                ? 'border-indigo-400 text-indigo-300 bg-indigo-950/40'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            Threat Hunting Workspace
          </button>
          <button
            onClick={() => setActiveTab('mitre')}
            className={`px-4 py-2 text-xs font-semibold rounded-t-lg transition-colors border-b-2 ${
              activeTab === 'mitre'
                ? 'border-indigo-400 text-indigo-300 bg-indigo-950/40'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            MITRE ATT&CK Matrix
          </button>
        </div>
      </div>

      {/* TAB 1: IOC CATALOG */}
      {activeTab === 'iocs' && (
        <div className="space-y-4">
          {/* Filter Bar */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 bg-slate-900 border border-slate-800 rounded-lg p-3">
            <div className="flex items-center gap-2">
              <Search className="w-4 h-4 text-slate-400" />
              <input
                type="text"
                placeholder="Filter by indicator value or tag..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="bg-transparent text-xs text-slate-100 placeholder-slate-500 focus:outline-none w-64"
              />
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400 font-mono">TYPE:</span>
              {['ALL', 'IPV4', 'DOMAIN', 'URL', 'MD5'].map((t) => (
                <button
                  key={t}
                  onClick={() => setSelectedType(t)}
                  className={`text-xs px-2.5 py-1 rounded font-mono transition-colors ${
                    selectedType === t
                      ? 'bg-indigo-600 text-white font-semibold'
                      : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          {/* IOC Table */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950 text-slate-400 font-mono uppercase text-[10px] border-b border-slate-800">
                  <tr>
                    <th className="py-3 px-4">Type</th>
                    <th className="py-3 px-4">Indicator</th>
                    <th className="py-3 px-4">Reputation</th>
                    <th className="py-3 px-4">Severity</th>
                    <th className="py-3 px-4">MITRE ATT&CK</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4 text-right">Analyst Verdict</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800 text-slate-200">
                  {filteredIocs.map((item) => (
                    <tr key={item.ioc_id} className="hover:bg-slate-800/50 transition-colors">
                      <td className="py-3 px-4 font-mono uppercase text-sky-400">
                        {item.type}
                      </td>
                      <td className="py-3 px-4 font-mono font-medium max-w-xs truncate text-slate-100">
                        {item.value}
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <div className="w-16 bg-slate-800 h-2 rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full ${
                                item.reputation_score >= 80
                                  ? 'bg-rose-500'
                                  : item.reputation_score >= 50
                                  ? 'bg-amber-500'
                                  : 'bg-emerald-500'
                              }`}
                              style={{ width: `${item.reputation_score}%` }}
                            />
                          </div>
                          <span className="font-mono text-xs">{item.reputation_score.toFixed(0)}</span>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold ${
                            item.severity === 'CRITICAL'
                              ? 'bg-rose-950/80 text-rose-300 border border-rose-800'
                              : item.severity === 'HIGH'
                              ? 'bg-orange-950/80 text-orange-300 border border-orange-800'
                              : 'bg-slate-800 text-slate-300'
                          }`}
                        >
                          {item.severity}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex flex-wrap gap-1">
                          {item.mitre_attack.map((tid) => (
                            <span key={tid} className="bg-indigo-950/80 text-indigo-300 border border-indigo-800 px-1.5 py-0.5 rounded text-[10px] font-mono">
                              {tid}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`text-[10px] font-mono px-2 py-0.5 rounded ${
                            item.status === 'ACTIVE'
                              ? 'text-emerald-300 bg-emerald-950/60'
                              : 'text-slate-400 bg-slate-800'
                          }`}
                        >
                          {item.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={() => handleVerdict(item.ioc_id, 'TP')}
                            title="Confirm True Positive"
                            className="p-1 hover:bg-rose-950/50 rounded text-rose-400 hover:text-rose-300 transition-colors"
                          >
                            <CheckCircle className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleVerdict(item.ioc_id, 'FP')}
                            title="Mark False Positive"
                            className="p-1 hover:bg-slate-800 rounded text-slate-400 hover:text-slate-200 transition-colors"
                          >
                            <XCircle className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: THREAT HUNTING WORKSPACE */}
      {activeTab === 'hunting' && (
        <div className="space-y-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col md:flex-row items-center justify-between gap-4">
            <div>
              <h3 className="text-base font-semibold text-white">Hypothesis-Driven Threat Hunting</h3>
              <p className="text-xs text-slate-300 mt-1">
                Scan normalized security events (CloudTrail, VPC Flow, GuardDuty) against active hunting rules and indicator feeds.
              </p>
            </div>
            <button
              onClick={handleRunHunt}
              disabled={huntRunning}
              className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-semibold px-4 py-2 rounded-lg flex items-center gap-2 transition-colors"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${huntRunning ? 'animate-spin' : ''}`} />
              <span>{huntRunning ? 'Hunting in progress...' : 'Execute Threat Hunt'}</span>
            </button>
          </div>

          {huntResults && (
            <div className="space-y-3">
              <h4 className="text-xs font-mono font-semibold text-slate-400 uppercase">
                Active Hunt Campaign Matches ({huntResults.length})
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {huntResults.map((res) => (
                  <div key={res.rule_id} className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-[11px] text-amber-400 font-semibold">{res.rule_id}</span>
                      <span className="bg-indigo-950 text-indigo-300 font-mono text-[10px] px-2 py-0.5 rounded border border-indigo-800">
                        {res.mitre}
                      </span>
                    </div>
                    <h4 className="text-sm font-semibold text-white">{res.rule_name}</h4>
                    <p className="text-xs text-slate-300">{res.summary}</p>
                    <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400 font-mono">
                      <span>Correlated IOC: <span className="text-sky-400">{res.ioc}</span></span>
                      <span>Matches: <span className="text-emerald-400">{res.matched_events}</span></span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: MITRE ATT&CK MATRIX */}
      {activeTab === 'mitre' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {MITRE_CATALOG.map((tech) => (
            <div key={tech.id} className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-bold text-sky-400">{tech.id}</span>
                <span className="text-[10px] font-mono text-slate-400 bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
                  {tech.tactic}
                </span>
              </div>
              <h4 className="text-sm font-semibold text-white">{tech.name}</h4>
              <p className="text-xs text-slate-300">{tech.desc}</p>
              <a
                href={`https://attack.mitre.org/techniques/${tech.id}/`}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-[11px] text-indigo-400 hover:text-indigo-300 pt-2"
              >
                <span>View MITRE Documentation</span>
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
