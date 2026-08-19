import React from 'react';
import { Cpu, Eye, ArrowRight, ShieldCheck, Lock, Activity } from 'lucide-react';
import { TrustScoreGauge } from '../components/TrustScoreGauge';

interface LandingViewProps {
  onStartScan: () => void;
  onExploreDashboard: () => void;
}

export const LandingView: React.FC<LandingViewProps> = ({ onStartScan, onExploreDashboard }) => {
  return (
    <div className="max-w-7xl mx-auto px-6 py-14">
      {/* Hero Section */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-14 items-center py-8 mb-20 border-b border-[#1e2231] pb-20">
        <div className="lg:col-span-7">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-semibold mb-6">
            <ShieldCheck size={14} />
            <span>Digital Media Forensics & Synthetic Defense</span>
          </div>

          <h1 className="text-4xl sm:text-5xl font-extrabold text-white tracking-tight leading-[1.12] mb-6">
            Detect Synthetic Imagery with{' '}
            <span className="text-indigo-400">Verifiable Explainability.</span>
          </h1>

          <p className="text-[15px] text-slate-400 leading-relaxed max-w-xl mb-8">
            TrustNet conducts real-time multi-signal forensics on digital imagery — fusing 2D Fourier (FFT) grid spikes, Error Level Analysis (ELA) compression variance, and PRNU sensor pattern noise with Explainable AI.
          </p>

          <div className="flex flex-wrap items-center gap-3 mb-12">
            <button
              onClick={onStartScan}
              className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm transition-colors"
            >
              <span>Launch Image Inspection</span>
              <ArrowRight size={16} />
            </button>

            <button
              onClick={onExploreDashboard}
              className="inline-flex items-center gap-2 px-5 py-3 rounded-lg bg-white/[0.04] hover:bg-white/[0.07] border border-[#2a2f3e] text-slate-300 font-semibold text-sm transition-colors"
            >
              <span>View Audit Telemetry</span>
            </button>
          </div>

          {/* Quick specs */}
          <div className="grid grid-cols-3 gap-8 pt-6 border-t border-[#1e2231]">
            <div>
              <div className="text-lg font-bold text-white mb-0.5">&lt; 180 ms</div>
              <div className="text-slate-500 text-xs">Inference Latency</div>
            </div>
            <div>
              <div className="text-lg font-bold text-indigo-400 mb-0.5">Multi-Signal</div>
              <div className="text-slate-500 text-xs">FFT + ELA + PRNU</div>
            </div>
            <div>
              <div className="text-lg font-bold text-slate-300 mb-0.5">Puter.js AI</div>
              <div className="text-slate-500 text-xs">Explainable Copilot</div>
            </div>
          </div>
        </div>

        {/* Hero Preview Card */}
        <div className="lg:col-span-5 bg-[#13161f] border border-[#1e2231] rounded-2xl p-6 shadow-xl shadow-black/20">
          <div className="flex items-center justify-between gap-2 pb-4 mb-5 border-b border-[#1e2231] text-xs">
            <span className="text-slate-400 font-medium font-mono">benchmark-ff-c23.jpg</span>
            <span className="px-2.5 py-1 rounded-md bg-red-500/10 border border-red-500/20 text-red-400 font-semibold text-[11px]">
              AI Generated
            </span>
          </div>

          <div className="flex justify-center my-4">
            <TrustScoreGauge score={88} riskLevel="CRITICAL" size={150} />
          </div>

          <div className="space-y-2 mt-6 text-xs font-mono">
            <div className="flex items-center justify-between p-3 rounded-lg bg-[#0f1117] border border-[#1e2231]">
              <span className="text-slate-400">FFT Frequency Artifacts</span>
              <span className="font-semibold text-red-400">0.88</span>
            </div>
            <div className="flex items-center justify-between p-3 rounded-lg bg-[#0f1117] border border-[#1e2231]">
              <span className="text-slate-400">ELA Compression Anomaly</span>
              <span className="font-semibold text-amber-400">0.97</span>
            </div>
          </div>
        </div>
      </section>

      {/* 4-Step Pipeline Architecture Section */}
      <section>
        <div className="mb-10">
          <h2 className="text-xl font-bold text-white tracking-tight mb-2">
            Forensic Inspection Architecture
          </h2>
          <p className="text-sm text-slate-400">
            Modular multi-signal pipeline designed for zero-leakage media authentication and explainable verification.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-[#13161f] border border-[#1e2231] rounded-xl p-5 hover:border-[#2a3040] transition-colors">
            <div className="w-10 h-10 rounded-lg bg-indigo-500/10 flex items-center justify-center text-indigo-400 mb-4">
              <Lock size={18} />
            </div>
            <h3 className="text-sm font-semibold text-white mb-1.5">1. Security Intake</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              MIME validation, magic byte verification, and cryptographic UUID hashing at the API perimeter.
            </p>
          </div>

          <div className="bg-[#13161f] border border-[#1e2231] rounded-xl p-5 hover:border-[#2a3040] transition-colors">
            <div className="w-10 h-10 rounded-lg bg-indigo-500/10 flex items-center justify-center text-indigo-400 mb-4">
              <Cpu size={18} />
            </div>
            <h3 className="text-sm font-semibold text-white mb-1.5">2. Fourier & ELA Core</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              2D Discrete Fourier Transform and Error Level Analysis computing localized 8x8 DCT pixel variance.
            </p>
          </div>

          <div className="bg-[#13161f] border border-[#1e2231] rounded-xl p-5 hover:border-[#2a3040] transition-colors">
            <div className="w-10 h-10 rounded-lg bg-indigo-500/10 flex items-center justify-center text-indigo-400 mb-4">
              <Activity size={18} />
            </div>
            <h3 className="text-sm font-semibold text-white mb-1.5">3. Calibrated Risk</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Multi-signal weighted fusion mapping anomaly indicators into a calibrated 0 to 100 severity index.
            </p>
          </div>

          <div className="bg-[#13161f] border border-[#1e2231] rounded-xl p-5 hover:border-[#2a3040] transition-colors">
            <div className="w-10 h-10 rounded-lg bg-indigo-500/10 flex items-center justify-center text-indigo-400 mb-4">
              <Eye size={18} />
            </div>
            <h3 className="text-sm font-semibold text-white mb-1.5">4. Explainable AI</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Puter.js neural debriefing, multimodal vision inspection, and interactive pixel intensity studio.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
};
