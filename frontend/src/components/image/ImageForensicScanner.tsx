import React, { useState, useEffect } from 'react';
import { Sparkles, Activity, Cpu, Eye, Lock } from 'lucide-react';

interface ImageForensicScannerProps {
  imageUrl: string;
  fileName?: string;
  fileSize?: number;
  isDeepVision?: boolean;
}

const TELEMETRY_STAGES = [
  { id: 1, label: 'Intake & Cryptographic MIME Verification', icon: Lock, color: 'text-indigo-600' },
  { id: 2, label: '2D Discrete Fourier Spectral Peak Extraction', icon: Activity, color: 'text-indigo-600' },
  { id: 3, label: 'Error Level Analysis (8x8 DCT Variance)', icon: Cpu, color: 'text-violet-600' },
  { id: 4, label: 'Local ViT Neural Feature Vector Generation', icon: Eye, color: 'text-indigo-600' },
  { id: 5, label: 'TrustNet Vision AI Contextual Synthesis', icon: Sparkles, color: 'text-violet-600' },
];

export const ImageForensicScanner: React.FC<ImageForensicScannerProps> = ({
  imageUrl,
  fileName = 'input_sample.jpg',
  fileSize,
  isDeepVision = false,
}) => {
  const [currentStageIdx, setCurrentStageIdx] = useState(0);
  const [detectedPoints, setDetectedPoints] = useState<number[]>([1, 2]);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentStageIdx((prev) => (prev + 1) % TELEMETRY_STAGES.length);
    }, 1800);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const pointInterval = setInterval(() => {
      const p1 = Math.floor(Math.random() * 4);
      const p2 = (p1 + 1) % 4;
      setDetectedPoints([p1, p2]);
    }, 1400);
    return () => clearInterval(pointInterval);
  }, []);

  const currentStage = TELEMETRY_STAGES[currentStageIdx];
  const StageIcon = currentStage.icon;

  return (
    <div className="w-full max-w-2xl mx-auto">
      {/* 3D Perspective Container */}
      <div className="perspective-1500">
        <div className="relative rounded-2xl bg-card border border-border shadow-3d-lg overflow-hidden transform-style-3d transition-transform duration-500">
          {/* Top Instrument HUD Bar */}
          <div className="flex items-center justify-between px-5 py-3 bg-slate-900 text-white text-xs border-b border-slate-800">
            <div className="flex items-center gap-2 font-mono">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
              <span className="text-slate-300 font-semibold uppercase tracking-wider">
                Forensic Grid-Cam 3D
              </span>
              <span className="text-slate-600">|</span>
              <span className="text-slate-400 truncate max-w-[180px]">{fileName}</span>
            </div>

            <div className="flex items-center gap-3 text-[11px] font-mono text-slate-400">
              {fileSize && <span>{(fileSize / 1024).toFixed(0)} KB</span>}
              <span className="px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                {isDeepVision ? 'Deep Vision Active' : 'Fast Scan Mode'}
              </span>
            </div>
          </div>

          {/* Media Viewport with 3D Overlays */}
          <div className="relative aspect-4/3 sm:aspect-16/10 w-full bg-slate-950 flex items-center justify-center overflow-hidden">
            {/* The Actual Uploaded Image */}
            <img
              src={imageUrl}
              alt="Active Inspection Target"
              className="w-full h-full object-contain filter contrast-105"
            />

            {/* Technical Perspective 3D Grid Overlay */}
            <div 
              className="absolute inset-0 pointer-events-none opacity-40 animate-grid-pulse"
              style={{
                backgroundImage: `
                  linear-gradient(to right, rgba(79, 70, 229, 0.25) 1px, transparent 1px),
                  linear-gradient(to bottom, rgba(79, 70, 229, 0.25) 1px, transparent 1px)
                `,
                backgroundSize: '36px 36px',
              }}
            />

            {/* Laser Scanning Plane / Beam */}
            <div className="absolute left-0 right-0 h-1 bg-gradient-to-r from-transparent via-indigo-400 to-transparent shadow-[0_0_15px_4px_rgba(99,102,241,0.6)] animate-scan-beam pointer-events-none">
              {/* Diffuse laser glow area */}
              <div className="absolute -top-12 left-0 right-0 h-12 bg-gradient-to-t from-indigo-500/20 to-transparent pointer-events-none" />
            </div>

            {/* Corner HUD Reticles */}
            <div className="absolute top-3 left-3 w-5 h-5 border-t-2 border-l-2 border-indigo-400" />
            <div className="absolute top-3 right-3 w-5 h-5 border-t-2 border-r-2 border-indigo-400" />
            <div className="absolute bottom-3 left-3 w-5 h-5 border-b-2 border-l-2 border-indigo-400" />
            <div className="absolute bottom-3 right-3 w-5 h-5 border-b-2 border-r-2 border-indigo-400" />

            {/* Localized Analysis Nodes & Reticles */}
            {/* Node 1: Top Left - Periocular / High Freq */}
            <div 
              className={`absolute top-[28%] left-[32%] -translate-x-1/2 -translate-y-1/2 transition-opacity duration-300 pointer-events-none ${
                detectedPoints.includes(0) ? 'opacity-100' : 'opacity-40'
              }`}
            >
              <div className="relative flex items-center justify-center">
                <span className="w-10 h-10 rounded-full border border-indigo-400/80 animate-node-ping absolute" />
                <span className="w-5 h-5 rounded-full border border-indigo-300 bg-indigo-500/30 flex items-center justify-center text-[8px] font-mono text-white font-bold">
                  01
                </span>
                <span className="absolute left-7 top-0 text-[10px] font-mono font-bold text-white bg-slate-900/90 px-1.5 py-0.5 rounded border border-indigo-500/40 whitespace-nowrap shadow-sm">
                  Spectral Discontinuity
                </span>
              </div>
            </div>

            {/* Node 2: Top Right - Frequency Peak */}
            <div 
              className={`absolute top-[38%] right-[28%] translate-x-1/2 -translate-y-1/2 transition-opacity duration-300 pointer-events-none ${
                detectedPoints.includes(1) ? 'opacity-100' : 'opacity-40'
              }`}
            >
              <div className="relative flex items-center justify-center">
                <span className="w-10 h-10 rounded-full border border-violet-400/80 animate-node-ping absolute" />
                <span className="w-5 h-5 rounded-full border border-violet-300 bg-violet-500/30 flex items-center justify-center text-[8px] font-mono text-white font-bold">
                  02
                </span>
                <span className="absolute right-7 top-0 text-[10px] font-mono font-bold text-white bg-slate-900/90 px-1.5 py-0.5 rounded border border-violet-500/40 whitespace-nowrap shadow-sm">
                  2D FFT Peak
                </span>
              </div>
            </div>

            {/* Node 3: Bottom Center - Compression ELA */}
            <div 
              className={`absolute bottom-[24%] left-[45%] -translate-x-1/2 translate-y-1/2 transition-opacity duration-300 pointer-events-none ${
                detectedPoints.includes(2) ? 'opacity-100' : 'opacity-40'
              }`}
            >
              <div className="relative flex items-center justify-center">
                <span className="w-10 h-10 rounded-full border border-emerald-400/80 animate-node-ping absolute" />
                <span className="w-5 h-5 rounded-full border border-emerald-300 bg-emerald-500/30 flex items-center justify-center text-[8px] font-mono text-white font-bold">
                  03
                </span>
                <span className="absolute left-7 bottom-0 text-[10px] font-mono font-bold text-white bg-slate-900/90 px-1.5 py-0.5 rounded border border-emerald-500/40 whitespace-nowrap shadow-sm">
                  DCT Compression Cell
                </span>
              </div>
            </div>

            {/* Real-time Synthesis Indicator in bottom left of viewport */}
            <div className="absolute bottom-4 left-4 bg-slate-900/85 backdrop-blur-md px-3 py-1.5 rounded-lg border border-slate-700/60 text-white flex items-center gap-2">
              <svg className="w-4 h-4 text-indigo-400 animate-spin" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              <span className="text-[11px] font-mono font-medium text-slate-300">
                Synthesizing Calibrated Risk Index...
              </span>
            </div>

            {/* Active Coordinates Display */}
            <div className="absolute bottom-4 right-4 text-[10px] font-mono text-slate-400 bg-slate-900/80 px-2.5 py-1 rounded border border-slate-800">
              x: {(Math.sin(currentStageIdx) * 128 + 256).toFixed(0)} | y: {(Math.cos(currentStageIdx) * 128 + 256).toFixed(0)} px
            </div>
          </div>

          {/* Bottom Telemetry Ticker */}
          <div className="p-4 bg-card border-t border-border flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center text-primary shrink-0">
                <StageIcon size={18} className="animate-pulse" />
              </div>
              <div className="text-left">
                <div className="text-xs font-bold text-foreground">
                  Step {currentStage.id} of 5: {currentStage.label}
                </div>
                <div className="text-[11px] text-muted-foreground font-mono">
                  Multi-signal physical sensors &amp; neural ViT active
                </div>
              </div>
            </div>

            <div className="flex items-center gap-1.5 shrink-0">
              {TELEMETRY_STAGES.map((s, idx) => (
                <span
                  key={s.id}
                  className={`h-2 rounded-full transition-all duration-300 ${
                    idx === currentStageIdx
                      ? 'w-6 bg-primary'
                      : idx < currentStageIdx
                      ? 'w-2 bg-[#00b4d8]/60'
                      : 'w-2 bg-[#1e3a5f]'
                  }`}
                />
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
