import React from 'react';
import { Cpu, Eye, ArrowRight, ShieldCheck, Lock, Activity } from 'lucide-react';
import { TrustScoreGauge } from '../components/TrustScoreGauge';

interface LandingViewProps {
  onStartScan: () => void;
  onExploreDashboard: () => void;
}

export const LandingView: React.FC<LandingViewProps> = ({ onStartScan, onExploreDashboard }) => {
  return (
    <div className="max-w-7xl mx-auto px-6 py-12">
      {/* Hero Section */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center py-8 mb-16 border-b border-[#1c202d] pb-16">
        <div className="lg:col-span-7">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-md bg-orange-950/40 border border-orange-800/50 text-[#ff5722] text-xs font-mono font-bold uppercase tracking-wider mb-6">
            <ShieldCheck size={14} />
            <span>⚡ DIGITAL MEDIA FORENSICS &amp; SYNTHETIC DEFENSE</span>
          </div>

          <h1 className="text-4xl sm:text-5xl font-black text-white tracking-tight leading-[1.12] mb-6">
            Detect Synthetic Imagery with{' '}
            <span className="text-[#ff5722]">Verifiable Explainability.</span>
          </h1>

          <p className="text-sm text-slate-400 leading-relaxed max-w-xl mb-8 font-normal">
            TRUST[NET] conducts real-time multi-signal forensics on digital imagery — fusing 2D Fourier (FFT) grid spikes, Error Level Analysis (ELA) compression variance, and PRNU sensor pattern noise with Explainable AI.
          </p>

          <div className="flex flex-wrap items-center gap-4 mb-10">
            <button
              onClick={onStartScan}
              className="inline-flex items-center gap-2 px-6 py-3 rounded bg-gradient-to-r from-[#ff4500] to-[#ff6b00] hover:from-[#ff5722] hover:to-[#ff7a1a] text-white font-black uppercase text-xs tracking-wider transition-all shadow-xl shadow-orange-500/25 hover:scale-[1.02]"
            >
              <span>Launch Image Inspection</span>
              <ArrowRight size={15} />
            </button>

            <button
              onClick={onExploreDashboard}
              className="inline-flex items-center gap-2 px-5 py-3 rounded bg-[#0e111a] hover:bg-[#151926] border border-[#23293a] text-slate-300 font-bold uppercase text-xs tracking-wider transition-colors"
            >
              <span>View Audit Telemetry</span>
            </button>
          </div>

          {/* Quick specs */}
          <div className="grid grid-cols-3 gap-6 pt-6 border-t border-[#1c202d] text-xs font-mono">
            <div>
              <div className="text-base font-black text-white mb-0.5">&lt; 180 ms</div>
              <div className="text-slate-500 text-[11px]">Inference Latency</div>
            </div>
            <div>
              <div className="text-base font-black text-[#ff5722] mb-0.5">Multi-Signal</div>
              <div className="text-slate-500 text-[11px]">FFT + ELA + PRNU</div>
            </div>
            <div>
              <div className="text-base font-black text-cyan-400 mb-0.5">Puter.js AI</div>
              <div className="text-slate-500 text-[11px]">Explainable Copilot</div>
            </div>
          </div>
        </div>

        {/* Hero Preview Card */}
        <div className="lg:col-span-5 bg-[#0b0d14] border border-[#1b1f2c] rounded-xl p-6 shadow-2xl">
          <div className="flex items-center justify-between gap-2 pb-4 mb-5 border-b border-[#1b1f2c] text-xs font-mono">
            <span className="text-slate-400 font-semibold">BENCHMARK-FF-C23.JPG</span>
            <span className="px-2.5 py-0.5 rounded bg-rose-950/80 border border-rose-800/80 text-rose-400 font-black uppercase text-[10px] tracking-wider">
              AI_GENERATED
            </span>
          </div>

          <div className="flex justify-center my-4">
            <TrustScoreGauge score={88} riskLevel="CRITICAL" size={150} />
          </div>

          <div className="space-y-2 mt-6 text-xs font-mono">
            <div className="flex items-center justify-between p-2.5 rounded bg-[#06080d] border border-[#161a25]">
              <span className="text-slate-400">FFT Frequency Artifacts</span>
              <span className="font-bold text-[#ff5722]">0.88</span>
            </div>
            <div className="flex items-center justify-between p-2.5 rounded bg-[#06080d] border border-[#161a25]">
              <span className="text-slate-400">ELA Compression Anomaly</span>
              <span className="font-bold text-amber-400">0.97</span>
            </div>
          </div>
        </div>
      </section>

      {/* 4-Step Pipeline Architecture Section */}
      <section>
        <div className="mb-8">
          <h2 className="text-xl font-black text-white tracking-tight mb-1">
            Forensic Inspection Architecture
          </h2>
          <p className="text-xs text-slate-400 font-mono">
            Modular multi-signal pipeline designed for zero-leakage media authentication and explainable verification.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          <div className="bg-[#0b0d14] border border-[#1b1f2c] rounded-xl p-5 shadow-sm">
            <div className="w-10 h-10 rounded-lg bg-orange-950/40 border border-orange-800/50 flex items-center justify-center text-[#ff5722] mb-4">
              <Lock size={18} />
            </div>
            <h3 className="text-sm font-bold text-white mb-1">1. Security Intake</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              MIME validation, magic byte verification, and cryptographic UUID hashing at the API perimeter.
            </p>
          </div>

          <div className="bg-[#0b0d14] border border-[#1b1f2c] rounded-xl p-5 shadow-sm">
            <div className="w-10 h-10 rounded-lg bg-cyan-950/40 border border-cyan-800/50 flex items-center justify-center text-cyan-400 mb-4">
              <Cpu size={18} />
            </div>
            <h3 className="text-sm font-bold text-white mb-1">2. Fourier &amp; ELA Core</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              2D Discrete Fourier Transform and Error Level Analysis computing localized 8x8 DCT pixel variance.
            </p>
          </div>

          <div className="bg-[#0b0d14] border border-[#1b1f2c] rounded-xl p-5 shadow-sm">
            <div className="w-10 h-10 rounded-lg bg-emerald-950/40 border border-emerald-800/50 flex items-center justify-center text-emerald-400 mb-4">
              <Activity size={18} />
            </div>
            <h3 className="text-sm font-bold text-white mb-1">3. Calibrated Risk</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Multi-signal weighted fusion mapping anomaly indicators into a calibrated 0 to 100 severity index.
            </p>
          </div>

          <div className="bg-[#0b0d14] border border-[#1b1f2c] rounded-xl p-5 shadow-sm">
            <div className="w-10 h-10 rounded-lg bg-purple-950/40 border border-purple-800/50 flex items-center justify-center text-purple-400 mb-4">
              <Eye size={18} />
            </div>
            <h3 className="text-sm font-bold text-white mb-1">4. Explainable AI</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Puter.js neural debriefing, multimodal vision inspection, and interactive pixel intensity studio.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
};
