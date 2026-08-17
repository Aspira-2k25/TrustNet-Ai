import React, { useState } from 'react';
import type { ScanRecord, RiskLevel } from '../types';
import { Search, ArrowUpRight, ShieldAlert, ShieldCheck, Clock, Activity, FileText, Plus } from 'lucide-react';

interface DashboardViewProps {
  scans: ScanRecord[];
  onSelectScan: (scan: ScanRecord) => void;
  onNewScan: () => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({ scans, onSelectScan, onNewScan }) => {
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedFilter, setSelectedFilter] = useState<'ALL' | RiskLevel>('ALL');

  const totalScans = scans.length;
  const threatScans = scans.filter((s) => (s.trust_score?.trust_risk_score || 0) >= 50).length;
  const safeScans = scans.filter((s) => (s.trust_score?.trust_risk_score || 0) < 50 && s.status === 'SUCCESS').length;
  const avgConfidence = scans.length > 0
    ? (scans.reduce((acc, s) => acc + (s.trust_score?.confidence || 0.85), 0) / scans.length * 100).toFixed(0)
    : '94';

  const filteredScans = scans.filter((s) => {
    const matchesSearch = s.filename?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.id.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesFilter = selectedFilter === 'ALL' || s.trust_score?.risk_level === selectedFilter;
    return matchesSearch && matchesFilter;
  });

  const getRiskBadge = (level?: RiskLevel) => {
    switch (level) {
      case 'LOW':
        return <span className="px-2 py-0.5 rounded-md text-[11px] font-semibold bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">Low</span>;
      case 'MEDIUM':
        return <span className="px-2 py-0.5 rounded-md text-[11px] font-semibold bg-amber-500/10 border border-amber-500/20 text-amber-400">Medium</span>;
      case 'HIGH':
        return <span className="px-2 py-0.5 rounded-md text-[11px] font-semibold bg-orange-500/10 border border-orange-500/20 text-orange-400">High</span>;
      case 'CRITICAL':
        return <span className="px-2 py-0.5 rounded-md text-[11px] font-semibold bg-red-500/10 border border-red-500/20 text-red-400">Critical</span>;
      default:
        return <span className="px-2 py-0.5 rounded-md text-[11px] text-slate-500">—</span>;
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      {/* Dashboard Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight mb-1">
            Forensic Intelligence History
          </h1>
          <p className="text-sm text-slate-400">
            Real-time telemetry and audit logs of media classification requests.
          </p>
        </div>

        <button
          onClick={onNewScan}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold transition-colors"
        >
          <Plus size={15} />
          <span>New Inspection</span>
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div className="bg-[#13161f] border border-[#1e2231] rounded-xl p-5">
          <div className="flex items-center justify-between gap-2 mb-3">
            <span className="text-xs font-medium text-slate-400">Total Ingested</span>
            <Activity size={16} className="text-slate-500" />
          </div>
          <div className="text-2xl font-bold font-mono text-white mb-1">{totalScans}</div>
          <span className="text-[11px] text-slate-500">Processed media assets</span>
        </div>

        <div className="bg-[#13161f] border border-[#1e2231] rounded-xl p-5">
          <div className="flex items-center justify-between gap-2 mb-3">
            <span className="text-xs font-medium text-red-400">Manipulated Assets</span>
            <ShieldAlert size={16} className="text-red-400/60" />
          </div>
          <div className="text-2xl font-bold font-mono text-red-400 mb-1">{threatScans}</div>
          <span className="text-[11px] text-slate-500">Risk score ≥ 50/100</span>
        </div>

        <div className="bg-[#13161f] border border-[#1e2231] rounded-xl p-5">
          <div className="flex items-center justify-between gap-2 mb-3">
            <span className="text-xs font-medium text-emerald-400">Authentic Media</span>
            <ShieldCheck size={16} className="text-emerald-400/60" />
          </div>
          <div className="text-2xl font-bold font-mono text-emerald-400 mb-1">{safeScans}</div>
          <span className="text-[11px] text-slate-500">Consistent sensor characteristics</span>
        </div>

        <div className="bg-[#13161f] border border-[#1e2231] rounded-xl p-5">
          <div className="flex items-center justify-between gap-2 mb-3">
            <span className="text-xs font-medium text-indigo-400">Mean Confidence</span>
            <Clock size={16} className="text-indigo-400/60" />
          </div>
          <div className="text-2xl font-bold font-mono text-indigo-400 mb-1">{avgConfidence}%</div>
          <span className="text-[11px] text-slate-500">Across active detectors</span>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-[#13161f] border border-[#1e2231] rounded-xl p-4 mb-6 flex flex-wrap items-center justify-between gap-4">
        {/* Search */}
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[#0f1117] border border-[#1e2231] min-w-[280px]">
          <Search size={14} className="text-slate-500" />
          <input
            type="text"
            placeholder="Search by filename or scan ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="bg-transparent border-none outline-none text-sm text-slate-200 placeholder:text-slate-500 w-full"
          />
        </div>

        {/* Risk Filters */}
        <div className="flex items-center gap-1 text-sm">
          {(['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'] as const).map((filter) => (
            <button
              key={filter}
              onClick={() => setSelectedFilter(filter)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${selectedFilter === filter ? 'bg-indigo-500/15 text-indigo-400 border border-indigo-500/25' : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'}`}
            >
              {filter === 'ALL' ? 'All' : filter.charAt(0) + filter.slice(1).toLowerCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Scans Table */}
      <div className="bg-[#13161f] border border-[#1e2231] rounded-xl overflow-hidden">
        <table className="w-full text-left text-sm border-collapse">
          <thead>
            <tr className="border-b border-[#1e2231] bg-[#0f1117] text-slate-400 font-medium text-xs">
              <th className="py-3 px-4">Scan ID</th>
              <th className="py-3 px-4">Media File</th>
              <th className="py-3 px-4">Classification</th>
              <th className="py-3 px-4">Risk Score</th>
              <th className="py-3 px-4">Risk Level</th>
              <th className="py-3 px-4">Status</th>
              <th className="py-3 px-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#1e2231] text-slate-300 text-xs">
            {filteredScans.length > 0 ? (
              filteredScans.map((scan) => (
                <tr
                  key={scan.id}
                  onClick={() => onSelectScan(scan)}
                  className="hover:bg-white/[0.02] cursor-pointer transition-colors"
                >
                  <td className="py-3 px-4 text-indigo-400 font-mono font-medium">
                    {scan.id}
                  </td>
                  <td className="py-3 px-4 font-medium text-slate-200">
                    <div className="flex items-center gap-2">
                      <FileText size={14} className="text-slate-500" />
                      <span>{scan.filename}</span>
                    </div>
                  </td>
                  <td className="py-3 px-4 font-semibold text-white">
                    {scan.result?.verdict || 'AUTHENTIC'}
                  </td>
                  <td className="py-3 px-4 font-mono font-medium text-slate-200">
                    {scan.trust_score?.trust_risk_score ?? '—'}/100
                  </td>
                  <td className="py-3 px-4">
                    {getRiskBadge(scan.trust_score?.risk_level)}
                  </td>
                  <td className="py-3 px-4">
                    <span className="px-2 py-0.5 rounded-md text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                      {scan.status}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectScan(scan);
                      }}
                      className="inline-flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 font-semibold"
                    >
                      <span>View</span>
                      <ArrowUpRight size={13} />
                    </button>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={7} className="py-8 text-center text-slate-500 text-xs">
                  No scan records found matching your filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
