import React, { useState, useMemo } from 'react';
import {
  Search,
  Filter,
  ArrowUpDown,
  ChevronRight,
  SlidersHorizontal,
  RefreshCw,
  AlertTriangle
} from 'lucide-react';
import { InvestigationCase, CaseStatus, CasePriority, RiskLevel } from '../types/case';
import { RiskBadge } from '../components/RiskBadge';
import { StatusBadge } from '../components/StatusBadge';

interface QueuePageProps {
  cases: InvestigationCase[];
  onSelectCase: (caseId: string) => void;
  isLoading: boolean;
  onRefresh: () => void;
}

export const QueuePage: React.FC<QueuePageProps> = ({
  cases,
  onSelectCase,
  isLoading,
  onRefresh
}) => {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [priorityFilter, setPriorityFilter] = useState<string>('ALL');
  const [riskFilter, setRiskFilter] = useState<string>('ALL');
  const [sortBy, setSortBy] = useState<'risk_score' | 'amount' | 'created_at'>('risk_score');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  const filteredCases = useMemo(() => {
    return cases
      .filter((c) => {
        if (statusFilter !== 'ALL' && c.status !== statusFilter) return false;
        if (priorityFilter !== 'ALL' && c.priority !== priorityFilter) return false;
        if (riskFilter !== 'ALL' && c.risk_level !== riskFilter) return false;

        if (search.trim()) {
          const q = search.toLowerCase();
          const matchId = c.case_id.toLowerCase().includes(q);
          const matchCust = c.customer_id.toLowerCase().includes(q);
          const matchAcct = c.account_id.toLowerCase().includes(q);
          const matchTxn = c.transaction_id.toLowerCase().includes(q);
          const matchMerchant = (c.merchant_name || '').toLowerCase().includes(q);
          if (!matchId && !matchCust && !matchAcct && !matchTxn && !matchMerchant) return false;
        }
        return true;
      })
      .sort((a, b) => {
        let valA: any = a[sortBy];
        let valB: any = b[sortBy];
        if (sortBy === 'created_at') {
          valA = new Date(valA).getTime();
          valB = new Date(valB).getTime();
        }
        if (valA < valB) return sortOrder === 'asc' ? -1 : 1;
        if (valA > valB) return sortOrder === 'asc' ? 1 : -1;
        return 0;
      });
  }, [cases, search, statusFilter, priorityFilter, riskFilter, sortBy, sortOrder]);

  const toggleSort = (field: 'risk_score' | 'amount' | 'created_at') => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('desc');
    }
  };

  const formatCurrency = (amt: number, curr: string = 'INR') => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: curr || 'INR',
      maximumFractionDigits: 0
    }).format(amt);
  };

  const formatDate = (iso: string) => {
    try {
      const d = new Date(iso);
      return d.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return iso;
    }
  };

  return (
    <div className="space-y-4">
      {/* Search & Filter Header Bar */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 space-y-3">
        <div className="flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
          {/* Search Input */}
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by Case ID, Customer, Account, or Merchant..."
              className="w-full bg-slate-950/70 border border-slate-800 rounded-lg pl-9 pr-4 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-sky-500 font-mono"
            />
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={onRefresh}
              disabled={isLoading}
              className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-medium flex items-center space-x-1.5 transition-colors"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-sky-400' : ''}`} />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {/* Filter Pills */}
        <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-800/80 text-xs">
          <span className="text-slate-400 font-mono text-[11px] flex items-center gap-1">
            <Filter className="w-3.5 h-3.5" />
            Status:
          </span>
          {['ALL', 'OPEN', 'IN_REVIEW', 'ESCALATED', 'RESOLVED'].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-2.5 py-1 rounded text-[11px] font-mono transition-colors ${
                statusFilter === st
                  ? 'bg-sky-600 text-white font-semibold'
                  : 'bg-slate-950/60 text-slate-400 hover:text-slate-200 hover:bg-slate-800'
              }`}
            >
              {st}
            </button>
          ))}

          <span className="text-slate-600 mx-1">|</span>

          <span className="text-slate-400 font-mono text-[11px]">Risk:</span>
          {['ALL', 'CRITICAL', 'HIGH', 'REVIEW'].map((rk) => (
            <button
              key={rk}
              onClick={() => setRiskFilter(rk)}
              className={`px-2.5 py-1 rounded text-[11px] font-mono transition-colors ${
                riskFilter === rk
                  ? 'bg-rose-600 text-white font-semibold'
                  : 'bg-slate-950/60 text-slate-400 hover:text-slate-200 hover:bg-slate-800'
              }`}
            >
              {rk}
            </button>
          ))}
        </div>
      </div>

      {/* Main Table */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/80 text-slate-400 uppercase font-mono text-[10px] tracking-wider border-b border-slate-800 select-none">
              <tr>
                <th className="py-3 px-4">Case ID</th>
                <th className="py-3 px-4">Customer & Account</th>
                <th className="py-3 px-4">Channel</th>
                <th
                  className="py-3 px-4 cursor-pointer hover:text-white"
                  onClick={() => toggleSort('amount')}
                >
                  <div className="flex items-center space-x-1">
                    <span>Amount</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th
                  className="py-3 px-4 cursor-pointer hover:text-white"
                  onClick={() => toggleSort('risk_score')}
                >
                  <div className="flex items-center space-x-1">
                    <span>Risk Level & Score</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th className="py-3 px-4">ML Signals</th>
                <th className="py-3 px-4">Priority</th>
                <th className="py-3 px-4">Status</th>
                <th
                  className="py-3 px-4 cursor-pointer hover:text-white"
                  onClick={() => toggleSort('created_at')}
                >
                  <div className="flex items-center space-x-1">
                    <span>Flagged At</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80 font-sans">
              {filteredCases.length === 0 ? (
                <tr>
                  <td colSpan={10} className="py-12 text-center text-slate-500">
                    <AlertTriangle className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                    <p className="text-sm">No fraud investigation cases match current filter criteria.</p>
                  </td>
                </tr>
              ) : (
                filteredCases.map((c) => (
                  <tr
                    key={c.case_id}
                    onClick={() => onSelectCase(c.case_id)}
                    className="hover:bg-slate-800/50 cursor-pointer transition-colors group"
                  >
                    <td className="py-3 px-4 font-mono font-semibold text-sky-400">
                      {c.case_id}
                    </td>
                    <td className="py-3 px-4">
                      <div className="text-slate-200 font-medium">{c.customer_id}</div>
                      <div className="text-[10px] text-slate-500 font-mono">{c.account_id}</div>
                    </td>
                    <td className="py-3 px-4">
                      <span className="font-mono text-slate-300 uppercase px-1.5 py-0.5 rounded bg-slate-800 text-[11px]">
                        {c.channel}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-mono font-semibold text-slate-200">
                      {formatCurrency(c.amount, c.currency)}
                    </td>
                    <td className="py-3 px-4">
                      <RiskBadge level={c.risk_level} score={c.risk_score} />
                    </td>
                    <td className="py-3 px-4">
                      <div className="text-[10px] font-mono text-slate-400">
                        P(Fraud): <span className="text-slate-200 font-semibold">{Math.round((c.fraud_probability ?? 0.5) * 100)}%</span>
                      </div>
                      <div className="text-[10px] font-mono text-slate-400">
                        Anomaly: <span className="text-slate-200 font-semibold">{Math.round((c.anomaly_score ?? 0.3) * 100)}%</span>
                      </div>
                    </td>
                    <td className="py-3 px-4 font-mono text-[11px]">
                      <span
                        className={`font-semibold ${
                          c.priority === 'CRITICAL'
                            ? 'text-rose-400'
                            : c.priority === 'HIGH'
                            ? 'text-amber-400'
                            : 'text-slate-400'
                        }`}
                      >
                        {c.priority}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <StatusBadge status={c.status} />
                    </td>
                    <td className="py-3 px-4 text-slate-400 font-mono text-[11px]">
                      {formatDate(c.created_at)}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end space-x-1">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectCase(c.case_id);
                          }}
                          className="p-1.5 rounded bg-sky-500/10 hover:bg-sky-500/20 text-sky-400 group-hover:text-white transition-all"
                          title="Open Case Investigation"
                        >
                          <ChevronRight className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

