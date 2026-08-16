import React from 'react';
import { AlertTriangle, CheckCircle, HelpCircle, Activity } from 'lucide-react';
import type { ScanRecord } from '../types';

interface EvidenceBadgesProps {
  scan: ScanRecord;
}

export const EvidenceBadges: React.FC<EvidenceBadgesProps> = ({ scan }) => {
  const analyzers = scan.result?.analyzers || [];
  
  if (analyzers.length === 0) {
    return (
      <div className="text-xs text-slate-500 font-mono">
        No specific analyzer telemetry available for this scan.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 font-mono">
      {analyzers.map((analyzer, idx) => {
        // Determine status styling
        let bgColor = 'bg-[#121520]';
        let borderColor = 'border-[#1e2434]';
        let icon = <Activity size={14} className="text-slate-400" />;
        let statusText = 'ANALYZED';
        let statusColor = 'text-slate-400';

        // Infer if it found an anomaly based on the finding text
        const findingLower = (analyzer.finding || '').toLowerCase();
        const isAnomaly = findingLower.includes('anomaly') || findingLower.includes('violation') || findingLower.includes('asymmetrical') || findingLower.includes('detected') && !findingLower.includes('no ');

        if (analyzer.status === 'SKIPPED') {
          borderColor = 'border-slate-800';
          icon = <HelpCircle size={14} className="text-slate-600" />;
          statusText = 'SKIPPED';
          statusColor = 'text-slate-600';
        } else if (isAnomaly) {
          borderColor = 'border-[#ff3d00]/30';
          bgColor = 'bg-[#ff3d00]/5';
          icon = <AlertTriangle size={14} className="text-[#ff3d00]" />;
          statusText = 'ANOMALY DETECTED';
          statusColor = 'text-[#ff3d00]';
        } else {
          borderColor = 'border-emerald-500/30';
          bgColor = 'bg-emerald-500/5';
          icon = <CheckCircle size={14} className="text-emerald-500" />;
          statusText = 'PASS';
          statusColor = 'text-emerald-500';
        }

        return (
          <div key={idx} className={`p-3 rounded-md border ${borderColor} ${bgColor} group relative transition-colors hover:border-cyan-500/50`}>
            <div className="flex items-start justify-between gap-2 mb-2">
              <div className="flex items-center gap-2 min-w-0 flex-1">
                <div className="shrink-0">{icon}</div>
                <span className="text-[11px] font-bold text-slate-200 uppercase tracking-wider truncate" title={analyzer.name}>
                  {analyzer.name}
                </span>
              </div>
              <span className={`text-[9px] font-black tracking-widest shrink-0 ${statusColor}`}>
                {statusText}
              </span>
            </div>
            
            {/* The finding text is usually truncated, but hovering expands it natively via title, or we just show 2 lines */}
            <p className="text-[10px] text-slate-400 line-clamp-2 group-hover:line-clamp-none transition-all duration-300">
              {analyzer.finding}
            </p>
          </div>
        );
      })}
    </div>
  );
};
