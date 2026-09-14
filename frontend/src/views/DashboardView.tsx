import React, { useState } from 'react';
import type { ScanRecord } from '../types';
import { Search, ArrowUpRight, ShieldAlert, ShieldCheck, Activity, Image, Plus, Film, Mic, Globe, Star } from 'lucide-react';

interface DashboardViewProps {
  scans: ScanRecord[];
  onSelectScan: (scan: ScanRecord) => void;
  onNewScan: () => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({ scans, onSelectScan, onNewScan }) => {
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedModalityFilter, setSelectedModalityFilter] = useState<'ALL' | 'image' | 'video' | 'audio' | 'url' | 'text'>('ALL');

  const totalScans = scans.length;
  const threatScans = scans.filter((s) => (s.trust_score?.trust_risk_score || 0) >= 50).length;
  const safeScans = scans.filter((s) => (s.trust_score?.trust_risk_score || 0) < 50 && s.status === 'SUCCESS').length;

  const filteredScans = scans.filter((s) => {
    const matchesSearch =
      s.filename?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.content_type?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesModality = selectedModalityFilter === 'ALL' || s.content_type === selectedModalityFilter;
    return matchesSearch && matchesModality;
  });

  const getModalityBadge = (type?: string) => {
    switch (type) {
      case 'video':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-bold bg-indigo-950/70 text-indigo-300 border border-indigo-800">
            <Film size={13} className="text-indigo-400" />
            Video Clip
          </span>
        );
      case 'audio':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-bold bg-purple-950/70 text-purple-300 border border-purple-800">
            <Mic size={13} className="text-purple-400" />
            Voice Audio
          </span>
        );
      case 'url':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-bold bg-emerald-950/70 text-emerald-300 border border-emerald-800">
            <Globe size={13} className="text-emerald-400" />
            Website Link
          </span>
        );
      case 'text':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-bold bg-rose-950/70 text-rose-300 border border-rose-800">
            <Star size={13} className="text-rose-400" />
            Reviews / Text
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-bold bg-blue-950/70 text-blue-300 border border-blue-800">
            <Image size={13} className="text-blue-400" />
            Photo
          </span>
        );
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-[#f8fafc] font-serif tracking-tight">
            Scan History &amp; Past Checks
          </h1>
          <p className="text-xs sm:text-sm text-[#94a3b8] mt-1">
            Review past checks across photos, videos, voice recordings, website links, scam texts, and fake reviews.
          </p>
        </div>

        <button
          onClick={onNewScan}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[#0077b6] hover:bg-[#0096c7] text-white text-xs font-bold transition-all shadow-3d-sm cursor-pointer"
        >
          <Plus size={15} />
          <span>New Check</span>
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-5 mb-8">
        <div className="bg-[#111d38] border border-[#1e3a5f] rounded-xl p-5 shadow-3d-card">
          <div className="flex items-center justify-between gap-2 mb-2">
            <span className="text-xs font-bold text-[#94a3b8] uppercase tracking-wider">
              Total Checks Done
            </span>
            <div className="w-8 h-8 rounded-lg bg-[#0b132b] border border-[#1e3a5f] flex items-center justify-center text-[#00b4d8]">
              <Activity size={16} />
            </div>
          </div>
          <div className="text-3xl font-bold font-mono text-[#f8fafc]">{totalScans}</div>
          <span className="text-xs text-[#64748b]">Across all media, text &amp; links</span>
        </div>

        <div className="bg-[#111d38] border border-[#1e3a5f] rounded-xl p-5 shadow-3d-card">
          <div className="flex items-center justify-between gap-2 mb-2">
            <span className="text-xs font-bold text-red-400 uppercase tracking-wider">
              Fakes &amp; Scams Found
            </span>
            <div className="w-8 h-8 rounded-lg bg-red-950/70 border border-red-800 flex items-center justify-center text-red-400">
              <ShieldAlert size={16} />
            </div>
          </div>
          <div className="text-3xl font-bold font-mono text-red-400">{threatScans}</div>
          <span className="text-xs text-[#64748b]">Flagged as altered or fraudulent</span>
        </div>

        <div className="bg-[#111d38] border border-[#1e3a5f] rounded-xl p-5 shadow-3d-card">
          <div className="flex items-center justify-between gap-2 mb-2">
            <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider">
              Verified Real Content
            </span>
            <div className="w-8 h-8 rounded-lg bg-emerald-950/70 border border-emerald-800 flex items-center justify-center text-emerald-400">
              <ShieldCheck size={16} />
            </div>
          </div>
          <div className="text-3xl font-bold font-mono text-emerald-400">{safeScans}</div>
          <span className="text-xs text-[#64748b]">Confirmed authentic &amp; safe</span>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-[#111d38] border border-[#1e3a5f] rounded-xl p-4 mb-6 shadow-3d-card flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-2.5 px-3.5 py-2 rounded-lg bg-[#0b132b] border border-[#1e3a5f] min-w-[280px] focus-within:border-[#00b4d8] transition-colors">
          <Search size={14} className="text-[#64748b]" />
          <input
            type="text"
            placeholder="Search by filename or check ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="bg-transparent border-none outline-none text-xs text-[#f8fafc] placeholder:text-[#64748b] w-full font-medium"
          />
        </div>

        {/* Modality Filter Pills */}
        <div className="flex flex-wrap items-center gap-1.5 text-xs">
          {[
            { id: 'ALL', label: 'All Checks' },
            { id: 'image', label: 'Photos' },
            { id: 'video', label: 'Videos' },
            { id: 'audio', label: 'Voice Notes' },
            { id: 'url', label: 'Websites' },
            { id: 'text', label: 'Messages & Reviews' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setSelectedModalityFilter(tab.id as any)}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                selectedModalityFilter === tab.id
                  ? 'bg-[#0077b6] text-white shadow-sm'
                  : 'text-[#94a3b8] hover:text-[#f8fafc] hover:bg-[#0b132b]'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Scans Registry Table */}
      <div className="bg-[#111d38] border border-[#1e3a5f] rounded-xl overflow-hidden shadow-3d-card">
        <table className="w-full text-left text-sm border-collapse">
          <thead>
            <tr className="border-b border-[#1e3a5f] bg-[#0b132b] text-[#94a3b8] font-bold text-xs">
              <th className="py-3.5 px-4">Check ID</th>
              <th className="py-3.5 px-4">Category</th>
              <th className="py-3.5 px-4">Item Checked</th>
              <th className="py-3.5 px-4">Verdict</th>
              <th className="py-3.5 px-4">Risk Level</th>
              <th className="py-3.5 px-4 text-right">Details</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#1e3a5f] text-xs">
            {filteredScans.length > 0 ? (
              filteredScans.map((scan) => {
                const isSafe = (scan.trust_score?.trust_risk_score || 0) < 50;
                return (
                  <tr
                    key={scan.id}
                    onClick={() => onSelectScan(scan)}
                    className="hover:bg-[#16254a] cursor-pointer transition-colors"
                  >
                    <td className="py-3 px-4 font-mono font-bold text-[#00b4d8]">
                      {scan.id}
                    </td>
                    <td className="py-3 px-4">
                      {getModalityBadge(scan.content_type)}
                    </td>
                    <td className="py-3 px-4 font-medium max-w-xs truncate text-[#f8fafc]" title={scan.filename}>
                      {scan.filename}
                    </td>
                    <td className="py-3 px-4">
                      {isSafe ? (
                        <span className="px-2.5 py-1 rounded-md text-[11px] font-bold bg-emerald-950 text-emerald-300 border border-emerald-800">
                          Real &amp; Safe
                        </span>
                      ) : (
                        <span className="px-2.5 py-1 rounded-md text-[11px] font-bold bg-red-950 text-red-300 border border-red-800">
                          Fake / Scam Detected
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <span className="font-mono font-bold text-[#f8fafc]">
                        {scan.trust_score?.trust_risk_score ?? '—'} / 100
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectScan(scan);
                        }}
                        className="inline-flex items-center gap-1 text-xs font-bold text-[#00b4d8] hover:text-[#38bdf8] cursor-pointer"
                      >
                        <span>View Result</span>
                        <ArrowUpRight size={13} />
                      </button>
                    </td>
                  </tr>
                );
              })
            ) : (
              <tr>
                <td colSpan={6} className="py-8 text-center text-[#64748b] text-xs">
                  No checks found matching your search.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
