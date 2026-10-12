import React, { useMemo } from 'react';
import type { ScanRecord } from '../types';

interface ForensicRadarChartProps {
  scan: ScanRecord;
}

export const ForensicRadarChart: React.FC<ForensicRadarChartProps> = ({ scan }) => {
  const data = useMemo(() => {
    const riskScore = scan.trust_score?.trust_risk_score ?? scan.result?.risk_score ?? 15;
    const evidence = scan.result?.evidence || scan.trust_score?.evidence || [];
    const contentType = scan.content_type || 'image';

    const getEvidenceScore = (keyword: string, _fallbackScore: number): number | null => {
      const aliases: Record<string,string[]> = {frequency:['fft','spectral'],ela:['compression_error'],spatial:['efficientnet_spatial']};
      const terms = aliases[keyword] || [keyword];
      const item = evidence.find(e => terms.some(term => e.feature_or_region.toLowerCase().includes(term)));
      if (item && item.contribution >= 0 && item.contribution <= 1) return Math.round(item.contribution * 100);
      return null;
    };

    const base = riskScore;

    if (contentType === 'audio') {
      return [
        { subject: 'Vocoder Harmonics', score: getEvidenceScore('vocoder', base > 50 ? base + 4 : base) },
        { subject: 'Prosody & Pitch (F0)', score: getEvidenceScore('prosody', base > 50 ? base - 6 : base) },
        { subject: 'Phase Continuity', score: getEvidenceScore('phase', base > 50 ? base - 10 : Math.max(5, base - 15)) },
        { subject: 'Spectral Roll-off', score: getEvidenceScore('spectral', base > 50 ? base + 2 : base) },
        { subject: 'Acoustic Ambiance', score: getEvidenceScore('room', base > 50 ? base - 12 : Math.max(5, base - 20)) },
        { subject: 'Neural TTS Glitch', score: getEvidenceScore('synthetic', base > 50 ? 94 : 8) },
      ];
    }

    if (contentType === 'video') {
      return [
        { subject: 'Temporal Jitter', score: getEvidenceScore('temporal', base > 50 ? base + 5 : base) },
        { subject: 'Audio-Visual Sync', score: getEvidenceScore('sync', base > 50 ? base - 3 : base) },
        { subject: 'Facial Boundary Blending', score: getEvidenceScore('face', base > 50 ? base + 2 : base) },
        { subject: 'Inter-Frame Continuity', score: getEvidenceScore('jitter', base > 50 ? base - 8 : Math.max(5, base - 15)) },
        { subject: 'Phoneme Alignment', score: getEvidenceScore('lip', base > 50 ? base - 5 : Math.max(5, base - 10)) },
        { subject: 'Neural Reenactment ViT', score: getEvidenceScore('synthetic', base > 50 ? 92 : 12) },
      ];
    }

    if (contentType === 'url') {
      return [
        { subject: 'Homoglyph & Punycode', score: getEvidenceScore('homoglyph', base > 50 ? base + 3 : base) },
        { subject: 'Domain Age & Reputation', score: getEvidenceScore('domain', base > 50 ? base - 8 : base) },
        { subject: 'SSL / TLS Verification', score: getEvidenceScore('ssl', base > 50 ? 88 : 12) },
        { subject: 'Redirect Chain Risk', score: getEvidenceScore('redirect', base > 50 ? base - 5 : Math.max(5, base - 15)) },
        { subject: 'DOM Credential Harvester', score: getEvidenceScore('credential', base > 50 ? base - 4 : Math.max(5, base - 10)) },
        { subject: 'Brand Impersonation', score: getEvidenceScore('spoof', base > 50 ? 96 : 10) },
      ];
    }

    if (contentType === 'text') {
      return [
        { subject: 'Artificial Panic Urgency', score: getEvidenceScore('urgency', base > 50 ? base + 2 : base) },
        { subject: 'Social Engineering Threat', score: getEvidenceScore('social', base > 50 ? base - 2 : base) },
        { subject: 'Deceptive Redirect Link', score: getEvidenceScore('link', base > 50 ? base - 4 : Math.max(5, base - 10)) },
        { subject: 'Authority Impersonation', score: getEvidenceScore('authority', base > 50 ? base - 6 : Math.max(5, base - 15)) },
        { subject: 'Syntactic Pattern Repetition', score: getEvidenceScore('duplicate', base > 50 ? base - 10 : Math.max(5, base - 20)) },
        { subject: 'Fraud Intent Index', score: getEvidenceScore('panic', base > 50 ? 95 : 12) },
      ];
    }

    // Default: Image Forensics
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
        subject: 'ImageNet feature signal',
        score: getEvidenceScore('spatial', base),
      },
      {
        subject: 'Semantic Context',
        score: getEvidenceScore('semantic', base > 50 ? 95 : 10),
      },
    ];
  }, [scan]);

  return (
    <div className="w-full h-full flex flex-col items-center justify-center p-4 gap-3">
      {data.map((item, idx) => (
        <div key={idx} className="w-full">
          <div className="flex justify-between items-end mb-1.5">
            <span className="text-[11px] text-muted-foreground font-medium">{item.subject}</span>
            <span className="text-[11px] font-semibold text-primary font-mono">{item.score === null ? 'Unavailable' : `${item.score ?? 0}%`}</span>
          </div>
          <div className="w-full bg-[#1e3a5f] h-1.5 rounded-full overflow-hidden flex shadow-inner">
            <div 
              className={`h-full rounded-full transition-all duration-1000 ease-out ${(item.score ?? 0) > 60 ? 'bg-destructive' : (item.score ?? 0) > 30 ? 'bg-warning' : 'bg-primary'}`}
              style={{ width: `${item.score ?? 0}%` }}
            />
          </div>
        </div>
      ))}
      <div className="mt-4 pt-3 border-t border-border w-full text-center">
        <div className="text-[10px] text-muted-foreground font-medium">Reported heuristic evidence strength; not calibrated correctness</div>
      </div>
    </div>
  );
};
