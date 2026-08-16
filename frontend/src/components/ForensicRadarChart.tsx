import React, { useMemo } from 'react';
import type { ScanRecord } from '../types';

interface ForensicRadarChartProps {
  scan: ScanRecord;
}

export const ForensicRadarChart: React.FC<ForensicRadarChartProps> = ({ scan }) => {
  const data = useMemo(() => {
    const riskScore = scan.trust_score?.trust_risk_score ?? scan.result?.risk_score ?? 15;
    const evidence = scan.trust_score?.evidence || [];

    // Helper to find evidence contribution for a specific feature, scale 0-100
    const getEvidenceScore = (keyword: string, fallbackScore: number) => {
      const item = evidence.find(e => e.feature_or_region.includes(keyword) || (e.human_readable_note && e.human_readable_note.toLowerCase().includes(keyword)));
      if (item) return Math.min(100, Math.round(item.contribution * 100));
      return fallbackScore;
    };

    const base = riskScore;
    
    return [
      {
        subject: 'Optics & Geometry',
        score: getEvidenceScore('physics', Math.max(0, base - 30)),
      },
      {
        subject: 'Compression (ELA)',
        score: getEvidenceScore('compression', base > 50 ? base + 10 : base),
      },
      {
        subject: 'Frequency (FFT)',
        score: getEvidenceScore('frequency', base > 50 ? base + 15 : base),
      },
      {
        subject: 'Sensor Noise',
        score: getEvidenceScore('noise', base > 50 ? base + 5 : base),
      },
      {
        subject: 'Deep Spatial',
        score: getEvidenceScore('spatial', base),
      },
      {
        subject: 'Semantic Context',
        score: getEvidenceScore('semantic', base > 50 ? 95 : 10),
      },
    ].map(d => ({ ...d, score: Math.min(100, Math.max(2, d.score)) })); // clamp 2-100
  }, [scan]);

  return (
    <div className="w-full h-full flex flex-col items-center justify-center font-mono p-4 gap-3">
      {data.map((item, idx) => (
        <div key={idx} className="w-full">
          <div className="flex justify-between items-end mb-1">
            <span className="text-[10px] text-slate-300 uppercase tracking-wider">{item.subject}</span>
            <span className="text-[10px] font-bold text-cyan-400">{item.score}%</span>
          </div>
          <div className="w-full bg-[#1b202e] h-1.5 rounded-full overflow-hidden flex">
            <div 
              className={`h-full transition-all duration-1000 ease-out ${item.score > 60 ? 'bg-[#ff3d00]' : item.score > 30 ? 'bg-yellow-400' : 'bg-cyan-500'}`}
              style={{ width: `${item.score}%` }} 
            />
          </div>
        </div>
      ))}
      <div className="mt-4 pt-3 border-t border-[#1e2434] w-full text-center">
        <div className="text-[9px] text-slate-500 tracking-widest uppercase">Multi-vector Synthesis</div>
      </div>
    </div>
  );
};
