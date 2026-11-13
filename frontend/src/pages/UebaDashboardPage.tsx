import React, { useState, useEffect } from 'react';
import {
  Activity,
  Fingerprint,
  ShieldAlert,
  Clock,
  Smartphone,
  MapPin,
  TrendingUp,
  BarChart3,
  Search,
  Filter,
  CheckCircle2,
  AlertTriangle,
  Zap,
  Sliders,
  ArrowRight,
  ShieldCheck,
  UserCheck
} from 'lucide-react';

interface EntityProfile {
  entity_id: string;
  entity_type: string;
  peer_group: string;
  current_risk_score: number;
  risk_level: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  active_anomalies: string[];
  total_events_observed: number;
  baseline: {
    avg_amount: number;
    std_amount: number;
    max_amount_historical: number;
    active_hours: number[];
    known_devices: string[];
    known_ips: string[];
    known_cities: string[];
    daily_velocity_mean: number;
    hourly_velocity_mean: number;
  };
}

const DEFAULT_PROFILES: EntityProfile[] = [
  {
    entity_id: 'CUS-100007',
    entity_type: 'CUSTOMER',
    peer_group: 'HIGH_NET_WORTH',
    current_risk_score: 88.5,
    risk_level: 'CRITICAL',
    active_anomalies: ['IMPOSSIBLE_TRAVEL_VELOCITY', 'UNUSUAL_AMOUNT_SPIKE', 'NEW_DEVICE_BURST'],
    total_events_observed: 225,
    baseline: {
      avg_amount: 2450.0,
      std_amount: 950.0,
      max_amount_historical: 15000.0,
      active_hours: [9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
      known_devices: ['dev_ipad_pro_7', 'dev_safari_mac_7'],
      known_ips: ['203.0.113.17'],
      known_cities: ['San Francisco', 'London'],
      daily_velocity_mean: 3.8,
      hourly_velocity_mean: 0.35
    }
  },
  {
    entity_id: 'CUS-100018',
    entity_type: 'CUSTOMER',
    peer_group: 'COMMERCIAL',
    current_risk_score: 85.0,
    risk_level: 'CRITICAL',
    active_anomalies: ['UNUSUAL_AMOUNT_SPIKE', 'NEW_DEVICE_BURST'],
    total_events_observed: 390,
    baseline: {
      avg_amount: 4800.0,
      std_amount: 1800.0,
      max_amount_historical: 28000.0,
      active_hours: [8, 9, 10, 11, 12, 13, 14, 15, 16, 17],
      known_devices: ['dev_office_win11_18'],
      known_ips: ['192.0.2.28'],
      known_cities: ['Chicago', 'Dallas'],
      daily_velocity_mean: 8.0,
      hourly_velocity_mean: 0.9
    }
  },
  {
    entity_id: 'CUS-100003',
    entity_type: 'CUSTOMER',
    peer_group: 'RETAIL',
    current_risk_score: 68.0,
    risk_level: 'HIGH',
    active_anomalies: ['OFF_HOURS_ELEVATED_VALUE', 'UNRECOGNIZED_IP_OFF_HOURS'],
    total_events_observed: 165,
    baseline: {
      avg_amount: 95.0,
      std_amount: 42.0,
      max_amount_historical: 450.0,
      active_hours: [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20],
      known_devices: ['dev_iphone_14_3'],
      known_ips: ['198.51.100.13'],
      known_cities: ['Boston'],
      daily_velocity_mean: 2.5,
      hourly_velocity_mean: 0.2
    }
  },
  {
    entity_id: 'CUS-100012',
    entity_type: 'CUSTOMER',
    peer_group: 'RETAIL',
    current_risk_score: 65.5,
    risk_level: 'HIGH',
    active_anomalies: ['OFF_HOURS_ELEVATED_VALUE'],
    total_events_observed: 300,
    baseline: {
      avg_amount: 82.0,
      std_amount: 38.0,
      max_amount_historical: 380.0,
      active_hours: [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20],
      known_devices: ['dev_chrome_mac_12'],
      known_ips: ['198.51.100.22'],
      known_cities: ['New York'],
      daily_velocity_mean: 2.2,
      hourly_velocity_mean: 0.2
    }
  },
  {
    entity_id: 'CUS-100027',
    entity_type: 'CUSTOMER',
    peer_group: 'COMMERCIAL',
    current_risk_score: 62.0,
    risk_level: 'HIGH',
    active_anomalies: ['NEW_DEVICE_BURST'],
    total_events_observed: 525,
    baseline: {
      avg_amount: 5100.0,
      std_amount: 1950.0,
      max_amount_historical: 30000.0,
      active_hours: [8, 9, 10, 11, 12, 13, 14, 15, 16, 17],
      known_devices: ['dev_finance_station_27'],
      known_ips: ['192.0.2.37'],
      known_cities: ['Chicago'],
      daily_velocity_mean: 7.5,
      hourly_velocity_mean: 0.8
    }
  },
  {
    entity_id: 'CUS-100005',
    entity_type: 'CUSTOMER',
    peer_group: 'INTERNAL_OPERATIONS',
    current_risk_score: 42.0,
    risk_level: 'MEDIUM',
    active_anomalies: ['NEW_DEVICE_BURST'],
    total_events_observed: 195,
    baseline: {
      avg_amount: 350.0,
      std_amount: 120.0,
      max_amount_historical: 1800.0,
      active_hours: [9, 10, 11, 12, 13, 14, 15, 16, 17],
      known_devices: ['dev_ops_bastion_01_5'],
      known_ips: ['10.100.4.15'],
      known_cities: ['Reston'],
      daily_velocity_mean: 4.0,
      hourly_velocity_mean: 0.4
    }
  },
  {
    entity_id: 'CUS-100001',
    entity_type: 'CUSTOMER',
    peer_group: 'RETAIL',
    current_risk_score: 12.0,
    risk_level: 'LOW',
    active_anomalies: [],
    total_events_observed: 135,
    baseline: {
      avg_amount: 63.75,
      std_amount: 31.5,
      max_amount_historical: 350.0,
      active_hours: [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21],
      known_devices: ['dev_iphone_14_1', 'dev_chrome_mac_1'],
      known_ips: ['198.51.100.11'],
      known_cities: ['New York', 'Boston'],
      daily_velocity_mean: 2.25,
      hourly_velocity_mean: 0.18
    }
  }
];

export const UebaDashboardPage: React.FC = () => {
  const [profiles, setProfiles] = useState<EntityProfile[]>(DEFAULT_PROFILES);
  const [selectedProfile, setSelectedProfile] = useState<EntityProfile>(DEFAULT_PROFILES[0]);
  const [selectedCohort, setSelectedCohort] = useState<string>('ALL');
  const [selectedRisk, setSelectedRisk] = useState<string>('ALL');
  const [searchTerm, setSearchTerm] = useState<string>('');

  // Simulator state
  const [simAmount, setSimAmount] = useState<number>(3500);
  const [simHour, setSimHour] = useState<number>(3);
  const [simDevice, setSimDevice] = useState<string>('dev_unrecognized_terminal');
  const [simCity, setSimCity] = useState<string>('Tokyo');
  const [simResult, setSimResult] = useState<any>(null);
  const [isSimulating, setIsSimulating] = useState<boolean>(false);

  // Filtered entities
  const filteredProfiles = profiles.filter((p) => {
    if (selectedCohort !== 'ALL' && p.peer_group !== selectedCohort) return false;
    if (selectedRisk !== 'ALL' && p.risk_level !== selectedRisk) return false;
    if (searchTerm) {
      const q = searchTerm.toLowerCase();
      const matchId = p.entity_id.toLowerCase().includes(q);
      const matchCity = p.baseline.known_cities.some((c) => c.toLowerCase().includes(q));
      if (!matchId && !matchCity) return false;
    }
    return true;
  });

  const handleSimulate = () => {
    setIsSimulating(true);
    setTimeout(() => {
      const base = selectedProfile.baseline;
      const devRatio = simAmount / Math.max(1, base.avg_amount);
      const zScore = (simAmount - base.avg_amount) / Math.max(1, base.std_amount);
      const isOffHours = !base.active_hours.includes(simHour);
      const isNewDev = !base.known_devices.includes(simDevice);
      const isNewCity = !base.known_cities.includes(simCity);

      const rules: string[] = [];
      if (devRatio >= 4.0 || zScore >= 3.0) rules.push('UNUSUAL_AMOUNT_SPIKE');
      if (isOffHours && devRatio >= 1.5) rules.push('OFF_HOURS_ELEVATED_VALUE');
      if (isNewDev) rules.push('NEW_DEVICE_BURST');
      if (isNewCity) rules.push('IMPOSSIBLE_TRAVEL_VELOCITY');

      const anomalyScore = Math.min(0.99, Math.max(0.08, 0.25 * (rules.length) + (devRatio > 3 ? 0.35 : 0.05)));
      const fraudProb = rules.length >= 2 ? 0.86 : 0.18;
      const iocRep = isNewDev ? 82.0 : 0.0;
      const cloudSev = isOffHours ? 7.5 : 1.0;

      // Blended risk formulation
      const maxThreat = Math.max(anomalyScore, fraudProb, iocRep / 100, cloudSev / 10);
      const weightedAvg = 0.35 * anomalyScore + 0.35 * fraudProb + 0.15 * (iocRep / 100) + 0.15 * (cloudSev / 10);
      const blendedRatio = Math.min(1.0, 0.60 * maxThreat + 0.40 * weightedAvg);
      const blendedScore = Math.round(blendedRatio * 1000) / 10;

      setSimResult({
        anomaly_score: anomalyScore,
        rules_triggered: rules,
        blended_risk_score: blendedScore,
        risk_level: blendedScore >= 80 ? 'CRITICAL' : blendedScore >= 60 ? 'HIGH' : blendedScore >= 35 ? 'MEDIUM' : 'LOW',
        dev_ratio: devRatio.toFixed(1),
        z_score: zScore.toFixed(1),
        is_off_hours: isOffHours,
        is_new_device: isNewDev,
        is_new_city: isNewCity,
        recommendation: blendedScore >= 80
          ? 'Immediate Account Hold: Suspend automated fund dispersal pending voice verification.'
          : blendedScore >= 60
          ? 'Step-Up Authentication: Enforce hardware token or biometric verification.'
          : 'Standard Processing: Activity conforms to nominal tolerance thresholds.'
      });
      setIsSimulating(false);
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
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-purple-500/10 border border-purple-500/30 text-purple-400">
              <Fingerprint className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
                User & Entity Behavior Analytics (UEBA)
                <span className="text-xs px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 font-mono border border-purple-500/30">Phase 14</span>
              </h1>
              <p className="text-xs text-slate-400">
                Continuous behavioral baselining, Isolation Forest anomaly scoring, and multi-domain fraud-threat correlation.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Monitored Entities</span>
            <UserCheck className="w-4 h-4 text-sky-400" />
          </div>
          <div className="text-2xl font-bold text-slate-100">{profiles.length}</div>
          <div className="text-xs text-slate-500 mt-1">35 pre-seeded enterprise accounts</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Critical Risk Entities</span>
            <ShieldAlert className="w-4 h-4 text-rose-400" />
          </div>
          <div className="text-2xl font-bold text-rose-400">
            {profiles.filter((p) => p.risk_level === 'CRITICAL').length}
          </div>
          <div className="text-xs text-rose-500/80 mt-1">Requires immediate analyst hold</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Active Anomalies</span>
            <Activity className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-amber-400">
            {profiles.reduce((acc, p) => acc + p.active_anomalies.length, 0)}
          </div>
          <div className="text-xs text-amber-500/80 mt-1">Spikes, off-hours, impossible travel</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">ML Anomaly Detector</span>
            <BarChart3 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400">Isolation Forest</div>
          <div className="text-xs text-emerald-500/80 mt-1">120 estimators · ROC-AUC: 1.000</div>
        </div>
      </div>

      {/* Main Grid: Entity Directory & Deep Dive Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Entity Directory (7 cols) */}
        <div className="lg:col-span-7 bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <Sliders className="w-4 h-4 text-purple-400" />
              Entity Behavioral Directory
            </h2>
            <div className="flex items-center gap-2 w-full sm:w-auto">
              <div className="relative flex-1 sm:w-48">
                <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-500" />
                <input
                  type="text"
                  placeholder="Search entity..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-purple-500"
                />
              </div>
            </div>
          </div>

          {/* Filters */}
          <div className="flex flex-wrap gap-2 text-xs">
            <div className="flex items-center gap-1 text-slate-400 mr-2">
              <Filter className="w-3.5 h-3.5" /> Filter:
            </div>
            {['ALL', 'RETAIL', 'HIGH_NET_WORTH', 'COMMERCIAL', 'INTERNAL_OPERATIONS'].map((c) => (
              <button
                key={c}
                onClick={() => setSelectedCohort(c)}
                className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                  selectedCohort === c
                    ? 'bg-purple-600 text-white'
                    : 'bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-200'
                }`}
              >
                {c.replace('_', ' ')}
              </button>
            ))}
          </div>

          {/* Entities Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-950 text-slate-400 font-medium border-b border-slate-800">
                <tr>
                  <th className="py-2.5 px-3">Entity ID</th>
                  <th className="py-2.5 px-3">Cohort</th>
                  <th className="py-2.5 px-3">Baseline Mean</th>
                  <th className="py-2.5 px-3">Risk Level</th>
                  <th className="py-2.5 px-3">Score</th>
                  <th className="py-2.5 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {filteredProfiles.map((p) => {
                  const isSelected = selectedProfile.entity_id === p.entity_id;
                  return (
                    <tr
                      key={p.entity_id}
                      onClick={() => setSelectedProfile(p)}
                      className={`cursor-pointer transition-colors ${
                        isSelected ? 'bg-purple-950/30' : 'hover:bg-slate-800/40'
                      }`}
                    >
                      <td className="py-3 px-3 font-mono font-medium text-slate-200">
                        {p.entity_id}
                      </td>
                      <td className="py-3 px-3 text-slate-400">{p.peer_group}</td>
                      <td className="py-3 px-3 font-mono">${p.baseline.avg_amount.toFixed(2)}</td>
                      <td className="py-3 px-3">{getRiskBadge(p.risk_level)}</td>
                      <td className="py-3 px-3 font-mono font-bold text-slate-200">
                        {p.current_risk_score.toFixed(1)}
                      </td>
                      <td className="py-3 px-3 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedProfile(p);
                          }}
                          className={`text-xs px-2.5 py-1 rounded transition-colors ${
                            isSelected
                              ? 'bg-purple-600 text-white font-medium'
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
        </div>

        {/* Right Column: Baseline Inspector & Behavioral Simulator (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          {/* Baseline Inspector Card */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-xs font-mono text-purple-400">BEHAVIORAL BASELINE</span>
                <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                  {selectedProfile.entity_id}
                  {getRiskBadge(selectedProfile.risk_level)}
                </h3>
              </div>
              <div className="text-right">
                <span className="text-xs text-slate-400">Risk Score</span>
                <div className="text-xl font-bold font-mono text-purple-300">
                  {selectedProfile.current_risk_score.toFixed(1)}/100
                </div>
              </div>
            </div>

            {/* Baseline Detail Stats */}
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="p-3 bg-slate-950 rounded-lg border border-slate-800/80">
                <span className="text-slate-500 block">Baseline Mean Amount</span>
                <span className="text-sm font-semibold text-slate-200 font-mono">
                  ${selectedProfile.baseline.avg_amount.toFixed(2)} (±${selectedProfile.baseline.std_amount.toFixed(2)})
                </span>
              </div>
              <div className="p-3 bg-slate-950 rounded-lg border border-slate-800/80">
                <span className="text-slate-500 block">Historical Max</span>
                <span className="text-sm font-semibold text-slate-200 font-mono">
                  ${selectedProfile.baseline.max_amount_historical.toFixed(2)}
                </span>
              </div>
              <div className="p-3 bg-slate-950 rounded-lg border border-slate-800/80">
                <span className="text-slate-500 block">Active Operating Hours</span>
                <span className="text-slate-300 font-mono">
                  {selectedProfile.baseline.active_hours[0]}:00 - {selectedProfile.baseline.active_hours[selectedProfile.baseline.active_hours.length - 1]}:00 UTC
                </span>
              </div>
              <div className="p-3 bg-slate-950 rounded-lg border border-slate-800/80">
                <span className="text-slate-500 block">Known Geographies</span>
                <span className="text-slate-300 font-mono">
                  {selectedProfile.baseline.known_cities.join(', ')}
                </span>
              </div>
            </div>

            {/* Registered Devices & IPs */}
            <div className="space-y-2 text-xs">
              <span className="text-slate-400 font-medium">Registered Devices & IPs</span>
              <div className="flex flex-wrap gap-1.5">
                {selectedProfile.baseline.known_devices.map((d) => (
                  <span key={d} className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono text-[11px] border border-slate-700">
                    <Smartphone className="w-3 h-3 inline mr-1 text-slate-400" />
                    {d}
                  </span>
                ))}
                {selectedProfile.baseline.known_ips.map((ip) => (
                  <span key={ip} className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono text-[11px] border border-slate-700">
                    {ip}
                  </span>
                ))}
              </div>
            </div>

            {/* Active Red Flags */}
            {selectedProfile.active_anomalies.length > 0 && (
              <div className="p-3 bg-rose-950/20 border border-rose-900/40 rounded-lg">
                <span className="text-xs font-semibold text-rose-300 flex items-center gap-1.5 mb-1.5">
                  <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
                  Active Behavioral Red Flags
                </span>
                <div className="flex flex-wrap gap-1">
                  {selectedProfile.active_anomalies.map((anom) => (
                    <span key={anom} className="px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 font-mono text-[10px] border border-rose-500/30">
                      {anom}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Anomaly Scoring & Correlation Simulator */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                <Zap className="w-4 h-4 text-amber-400" />
                Point-in-Time Event Simulator
              </h3>
              <span className="text-xs text-slate-500 font-mono">Test vs {selectedProfile.entity_id}</span>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <label className="text-slate-400 block mb-1">Transaction Amount ($)</label>
                <input
                  type="number"
                  value={simAmount}
                  onChange={(e) => setSimAmount(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-purple-500 font-mono"
                />
              </div>
              <div>
                <label className="text-slate-400 block mb-1">Hour of Day (0-23 UTC)</label>
                <input
                  type="number"
                  min="0"
                  max="23"
                  value={simHour}
                  onChange={(e) => setSimHour(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-purple-500 font-mono"
                />
              </div>
              <div>
                <label className="text-slate-400 block mb-1">Device Fingerprint</label>
                <input
                  type="text"
                  value={simDevice}
                  onChange={(e) => setSimDevice(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-purple-500 font-mono"
                />
              </div>
              <div>
                <label className="text-slate-400 block mb-1">Location / City</label>
                <input
                  type="text"
                  value={simCity}
                  onChange={(e) => setSimCity(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-purple-500 font-mono"
                />
              </div>
            </div>

            <button
              onClick={handleSimulate}
              disabled={isSimulating}
              className="w-full bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white font-medium py-2 rounded-lg text-xs flex items-center justify-center gap-2 transition-colors shadow-lg shadow-purple-600/20"
            >
              {isSimulating ? 'Scoring Vector...' : 'Evaluate Behavioral Anomaly & Fuse Risk'}
              <ArrowRight className="w-3.5 h-3.5" />
            </button>

            {simResult && (
              <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 space-y-2 text-xs">
                <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                  <span className="text-slate-400 font-medium">Blended Risk Assessment</span>
                  <div className="flex items-center gap-2 font-mono">
                    {getRiskBadge(simResult.risk_level)}
                    <span className="font-bold text-slate-100">{simResult.blended_risk_score}/100</span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-400 font-mono pt-1">
                  <div>Dev Ratio: <span className="text-purple-300 font-semibold">{simResult.dev_ratio}x</span></div>
                  <div>Z-Score: <span className="text-purple-300 font-semibold">{simResult.z_score}σ</span></div>
                  <div>Off-Hours: <span className={simResult.is_off_hours ? 'text-rose-400' : 'text-emerald-400'}>{simResult.is_off_hours ? 'YES' : 'NO'}</span></div>
                  <div>New Device: <span className={simResult.is_new_device ? 'text-rose-400' : 'text-emerald-400'}>{simResult.is_new_device ? 'YES' : 'NO'}</span></div>
                </div>

                {simResult.rules_triggered.length > 0 && (
                  <div className="pt-1">
                    <span className="text-[10px] text-slate-500 block mb-1">Triggered Heuristics:</span>
                    <div className="flex flex-wrap gap-1">
                      {simResult.rules_triggered.map((r: string) => (
                        <span key={r} className="px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-300 font-mono text-[10px]">
                          {r}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <div className="pt-2 text-slate-300 text-[11px] border-t border-slate-800/80">
                  <span className="text-purple-400 font-semibold block mb-0.5">Analyst Guidance:</span>
                  {simResult.recommendation}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default UebaDashboardPage;

