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
      <div className="text-xs text-slate-500">
        No specific analyzer telemetry available for this scan.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
      {analyzers.map((analyzer, idx) => {
        let bgColor = 'bg-[#13161f]';
        let borderColor = 'border-[#1e2231]';
        let icon = <Activity size={14} className="text-slate-400" />;
        let statusText = 'ANALYZED';
        let statusColor = 'text-slate-400';

        const findingLower = (analyzer.finding || '').toLowerCase();
        const isAnomaly = findingLower.includes('anomaly') || findingLower.includes('violation') || findingLower.includes('asymmetrical') || findingLower.includes('detected') && !findingLower.includes('no ');

        if (analyzer.status === 'SKIPPED') {
          borderColor = 'border-slate-800';
          icon = <HelpCircle size={14} className="text-slate-600" />;
          statusText = 'SKIPPED';
          statusColor = 'text-slate-600';
        } else if (isAnomaly) {
          borderColor = 'border-red-500/20';
          bgColor = 'bg-red-500/[0.03]';
          icon = <AlertTriangle size={14} className="text-red-400" />;
          statusText = 'ANOMALY';
          statusColor = 'text-red-400';
        } else {
          borderColor = 'border-emerald-500/20';
          bgColor = 'bg-emerald-500/[0.03]';
          icon = <CheckCircle size={14} className="text-emerald-400" />;
          statusText = 'PASS';
          statusColor = 'text-emerald-400';
        }

        return (
          <div key={idx} className={`p-3.5 rounded-lg border ${borderColor} ${bgColor} transition-colors hover:border-slate-600`}>
            <div className="flex items-start justify-between gap-2 mb-2">
              <div className="flex items-center gap-2 min-w-0 flex-1">
                <div className="shrink-0">{icon}</div>
                <span className="text-xs font-semibold text-slate-200 truncate" title={analyzer.name}>
                  {analyzer.name}
                </span>
              </div>
              <span className={`text-[10px] font-bold tracking-wide shrink-0 ${statusColor}`}>
                {statusText}
              </span>
            </div>
            
            <p className="text-[11px] text-slate-400 line-clamp-2 group-hover:line-clamp-none transition-all duration-300 leading-relaxed">
              {analyzer.finding}
            </p>
          </div>
        );
      })}
    </div>
  );
};
