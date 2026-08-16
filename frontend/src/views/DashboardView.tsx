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
        return <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-950/60 border border-emerald-800/50 text-emerald-400">LOW</span>;
      case 'MEDIUM':
        return <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-amber-950/60 border border-amber-800/50 text-amber-400">MEDIUM</span>;
      case 'HIGH':
        return <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-orange-950/60 border border-orange-800/50 text-[#ff5722]">HIGH</span>;
      case 'CRITICAL':
        return <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-rose-950/60 border border-rose-800/50 text-rose-400">CRITICAL</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[11px] font-mono text-slate-500">—</span>;
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      {/* Dashboard Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-black text-white tracking-tight mb-1">
            Forensic Intelligence History
          </h1>
          <p className="text-sm text-slate-400 font-mono text-xs">
            Real-time telemetry and audit logs of media classification requests.
          </p>
        </div>

        <button
          onClick={onNewScan}
          className="inline-flex items-center gap-2 px-4 py-2 rounded bg-gradient-to-r from-[#ff4500] to-[#ff6b00] hover:from-[#ff5722] hover:to-[#ff7a1a] text-white text-xs font-black uppercase tracking-wider transition-all shadow-lg shadow-orange-500/20"
        >
          <Plus size={14} />
          <span>New Inspection</span>
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-8">
        <div className="bg-[#0b0d14] border border-[#1b1f2c] rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between gap-2 mb-3">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider font-mono">Total Ingested</span>
            <Activity size={16} className="text-slate-400" />
          </div>
          <div className="text-2xl font-black font-mono text-white mb-1">{totalScans}</div>
          <span className="text-[11px] text-slate-500 font-mono">Processed media assets</span>
        </div>

        <div className="bg-[#0b0d14] border border-[#1b1f2c] rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between gap-2 mb-3">
            <span className="text-xs font-semibold text-rose-400 uppercase tracking-wider font-mono">Manipulated Assets</span>
            <ShieldAlert size={16} className="text-rose-400" />
          </div>
          <div className="text-2xl font-black font-mono text-rose-400 mb-1">{threatScans}</div>
          <span className="text-[11px] text-slate-500 font-mono">Risk score &ge; 50/100</span>
        </div>

        <div className="bg-[#0b0d14] border border-[#1b1f2c] rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between gap-2 mb-3">
            <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider font-mono">Authentic Media</span>
            <ShieldCheck size={16} className="text-emerald-400" />
          </div>
          <div className="text-2xl font-black font-mono text-emerald-400 mb-1">{safeScans}</div>
          <span className="text-[11px] text-slate-500 font-mono">Consistent sensor characteristics</span>
        </div>

        <div className="bg-[#0b0d14] border border-[#1b1f2c] rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between gap-2 mb-3">
            <span className="text-xs font-semibold text-cyan-400 uppercase tracking-wider font-mono">Mean Confidence</span>
            <Clock size={16} className="text-cyan-400" />
          </div>
          <div className="text-2xl font-black font-mono text-cyan-400 mb-1">{avgConfidence}%</div>
          <span className="text-[11px] text-slate-500 font-mono">Across active detectors</span>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-[#0b0d14] border border-[#1b1f2c] rounded-xl p-4 mb-6 shadow-sm flex flex-wrap items-center justify-between gap-4">
        {/* Search */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded bg-[#06080d] border border-[#1b1f2c] min-w-[280px]">
          <Search size={14} className="text-slate-500" />
          <input
            type="text"
            placeholder="Search by filename or scan ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="bg-transparent border-none outline-none text-xs text-slate-200 placeholder:text-slate-500 w-full font-mono"
          />
        </div>

        {/* Risk Filters */}
        <div className="flex items-center gap-1.5 font-mono text-xs">
          {(['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'] as const).map((filter) => (
            <button
              key={filter}
              onClick={() => setSelectedFilter(filter)}
              className={`px-3 py-1 rounded text-xs font-bold transition-colors ${selectedFilter === filter ? 'bg-orange-950/40 text-[#ff5722] border border-orange-800/60' : 'text-slate-400 hover:text-slate-200'}`}
            >
              {filter}
            </button>
          ))}
        </div>
      </div>

      {/* Scans Table */}
      <div className="bg-[#0b0d14] border border-[#1b1f2c] rounded-xl overflow-hidden shadow-sm">
        <table className="w-full text-left text-xs border-collapse font-mono">
          <thead>
            <tr className="border-b border-[#1b1f2c] bg-[#08090f] text-slate-400 font-bold uppercase tracking-wider text-[10px]">
              <th className="py-3 px-4">Scan ID</th>
              <th className="py-3 px-4">Media File</th>
              <th className="py-3 px-4">Classification</th>
              <th className="py-3 px-4">Risk Score</th>
              <th className="py-3 px-4">Risk Level</th>
              <th className="py-3 px-4">Status</th>
              <th className="py-3 px-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#161a25] text-slate-300">
            {filteredScans.length > 0 ? (
              filteredScans.map((scan) => (
                <tr
                  key={scan.id}
                  onClick={() => onSelectScan(scan)}
                  className="hover:bg-[#11141e] cursor-pointer transition-colors"
                >
                  <td className="py-3 px-4 text-[#ff5722] font-semibold">
                    {scan.id}
                  </td>
                  <td className="py-3 px-4 font-medium text-slate-200">
                    <div className="flex items-center gap-2">
                      <FileText size={14} className="text-slate-500" />
                      <span>{scan.filename}</span>
                    </div>
                  </td>
                  <td className="py-3 px-4 font-bold text-white">
                    {scan.result?.verdict || 'AUTHENTIC'}
                  </td>
                  <td className="py-3 px-4 font-bold text-slate-100">
                    {scan.trust_score?.trust_risk_score ?? '—'}/100
                  </td>
                  <td className="py-3 px-4">
                    {getRiskBadge(scan.trust_score?.risk_level)}
                  </td>
                  <td className="py-3 px-4">
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950/40 text-emerald-400 border border-emerald-800/40">
                      {scan.status}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectScan(scan);
                      }}
                      className="inline-flex items-center gap-1 text-xs text-[#ff5722] hover:text-orange-300 font-bold uppercase"
                    >
                      <span>Studio</span>
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
