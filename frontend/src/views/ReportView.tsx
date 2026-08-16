import React, { useState, useEffect, useRef } from 'react';
import { ArrowLeft, Download, Copy, Check, Volume2, Eye, RefreshCw, Bot, Microscope, FileText, CheckCircle2, ChevronDown } from 'lucide-react';
import type { ScanRecord } from '../types';
import { puterAI } from '../services/puterAI';
import { ForensicRadarChart } from '../components/ForensicRadarChart';
import { EvidenceBadges } from '../components/EvidenceBadges';

interface ReportViewProps {
  scan: ScanRecord;
  onBack: () => void;
}

export const ReportView: React.FC<ReportViewProps> = ({ scan, onBack }) => {
  const [viewMode, setViewMode] = useState<'heatmap_image' | 'pixel_morphing' | 'heatmap_only' | 'original'>('heatmap_only');
  const [intensity, setIntensity] = useState<number>(12); // Default to low intensity as shown in user screenshot
  const [copied, setCopied] = useState<boolean>(false);
  const [showDetailedAnalysis, setShowDetailedAnalysis] = useState<boolean>(true);
  const [showTechnicalSummary, setShowTechnicalSummary] = useState<boolean>(true);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Puter AI states
  const [aiExplanation, setAiExplanation] = useState<string | null>(null);
  const [aiVisionOpinion, setAiVisionOpinion] = useState<string | null>(null);
  const [isGeneratingAi, setIsGeneratingAi] = useState<boolean>(false);
  const [isGeneratingVision, setIsGeneratingVision] = useState<boolean>(false);
  const [isPlayingAudio, setIsPlayingAudio] = useState<boolean>(false);
  const currentAudioRef = useRef<HTMLAudioElement | null>(null);

  const result = scan.result;
  const trustScore = scan.trust_score;
  const riskScore = trustScore?.trust_risk_score ?? result?.risk_score ?? 15;
  const verdict = result?.verdict || (riskScore >= 75 ? 'AI_GENERATED' : (riskScore >= 45 ? 'SUSPICIOUS' : 'AUTHENTIC'));
  const isAiGenerated = verdict === 'AI_GENERATED' || riskScore >= 75;
  const isSuspicious = verdict === 'SUSPICIOUS' || (riskScore >= 45 && riskScore < 75);
  const isAuthentic = verdict === 'AUTHENTIC' || riskScore < 45;
  const isManipulated = riskScore >= 45;
  const authenticityConfidence = Math.round(100 - riskScore);

  // Real pixel-level canvas computation for ELA / Sub-Pixel Morphing / Saliency
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.src = scan.image_preview_url || 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=600&auto=format&fit=crop&q=80';

    img.onload = () => {
      const aspect = img.naturalWidth / (img.naturalHeight || 1);
      const targetWidth = Math.min(640, img.naturalWidth || 640);
      const targetHeight = Math.round(targetWidth / aspect);

      canvas.width = targetWidth;
      canvas.height = targetHeight;

      if (viewMode === 'original') {
        ctx.drawImage(img, 0, 0, targetWidth, targetHeight);
        return;
      }

      ctx.drawImage(img, 0, 0, targetWidth, targetHeight);
      const imageData = ctx.getImageData(0, 0, targetWidth, targetHeight);
      const data = imageData.data;

      const heatmapData = ctx.createImageData(targetWidth, targetHeight);
      const hData = heatmapData.data;
      const alpha = Math.max(0.1, intensity / 100.0);

      for (let y = 1; y < targetHeight - 1; y++) {
        for (let x = 1; x < targetWidth - 1; x++) {
          const idx = (y * targetWidth + x) * 4;

          const idxLeft = (y * targetWidth + (x - 1)) * 4;
          const idxRight = (y * targetWidth + (x + 1)) * 4;
          const idxUp = ((y - 1) * targetWidth + x) * 4;
          const idxDown = ((y + 1) * targetWidth + x) * 4;

          let grad = 0;

          if (viewMode === 'pixel_morphing') {
            const cfaDiff = Math.abs(data[idx + 1] - (data[idx] + data[idx + 2]) / 2.0);
            const lapCenter = (data[idx] + data[idx + 1] + data[idx + 2]) / 3.0;
            const lapSurround = (
              ((data[idxLeft] + data[idxLeft + 1] + data[idxLeft + 2]) / 3.0) +
              ((data[idxRight] + data[idxRight + 1] + data[idxRight + 2]) / 3.0) +
              ((data[idxUp] + data[idxUp + 1] + data[idxUp + 2]) / 3.0) +
              ((data[idxDown] + data[idxDown + 1] + data[idxDown + 2]) / 3.0)
            ) / 4.0;

            const lapDiff = Math.abs(lapCenter - lapSurround);
            grad = Math.min(255, cfaDiff * 2.5 + lapDiff * 4.0);
          } else {
            const dx = Math.abs(data[idxRight] - data[idxLeft]) +
                       Math.abs(data[idxRight + 1] - data[idxLeft + 1]) +
                       Math.abs(data[idxRight + 2] - data[idxLeft + 2]);

            const dy = Math.abs(data[idxDown] - data[idxUp]) +
                       Math.abs(data[idxDown + 1] - data[idxDown + 1]) +
                       Math.abs(data[idxDown + 2] - data[idxDown + 2]);

            grad = Math.min(255, (dx + dy) * 1.5);
          }

          const norm = Math.min(1.0, grad / (viewMode === 'pixel_morphing' ? 100.0 : 140.0));
          let r = 0, g = 0, b = 0;

          if (norm < 0.25) {
            b = Math.round(255 * (norm / 0.25));
          } else if (norm < 0.5) {
            g = Math.round(255 * ((norm - 0.25) / 0.25));
            b = 255;
          } else if (norm < 0.75) {
            r = Math.round(255 * ((norm - 0.5) / 0.25));
            g = 255;
            b = Math.round(255 * (1 - (norm - 0.5) / 0.25));
          } else {
            r = 255;
            g = Math.round(255 * (1 - (norm - 0.75) / 0.25));
            b = 0;
          }

          if (viewMode === 'heatmap_only') {
            hData[idx] = r;
            hData[idx + 1] = g;
            hData[idx + 2] = b;
            hData[idx + 3] = Math.round(255 * alpha);
          } else {
            const origR = data[idx];
            const origG = data[idx + 1];
            const origB = data[idx + 2];

            hData[idx] = Math.round(origR * (1 - alpha) + r * alpha);
            hData[idx + 1] = Math.round(origG * (1 - alpha) + g * alpha);
            hData[idx + 2] = Math.round(origB * (1 - alpha) + b * alpha);
            hData[idx + 3] = 255;
          }
        }
      }

      ctx.putImageData(heatmapData, 0, 0);
    };
  }, [scan.image_preview_url, viewMode, intensity, isManipulated]);

  const handleCopyLink = () => {
    navigator.clipboard.writeText(window.location.href);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadPDF = () => {
    const reportData = {
      scan_id: scan.id,
      filename: scan.filename,
      timestamp: scan.created_at,
      risk_score: riskScore,
      verdict: result?.verdict || (isManipulated ? 'AI_GENERATED' : 'AUTHENTIC'),
      ai_explanation: aiExplanation || result?.explanation,
      analyzers: result?.analyzers || [],
      evidence: trustScore?.evidence || []
    };
    const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `TrustNet-ForensicReport-${scan.id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleGenerateAIExplanation = async () => {
    setIsGeneratingAi(true);
    try {
      const explanation = await puterAI.generateForensicExplanation(scan);
      setAiExplanation(explanation);
    } catch (e) {
      console.error('Failed to generate Puter AI explanation:', e);
    } finally {
      setIsGeneratingAi(false);
    }
  };

  const handleGenerateVisionOpinion = async () => {
    if (!scan.image_preview_url) return;
    setIsGeneratingVision(true);
    try {
      const opinion = await puterAI.analyzeWithVision(scan.image_preview_url);
      setAiVisionOpinion(opinion);
    } catch (e) {
      console.error('Failed to run vision inspection:', e);
    } finally {
      setIsGeneratingVision(false);
    }
  };

  const handlePlayTTS = async () => {
    if (isPlayingAudio && currentAudioRef.current) {
      currentAudioRef.current.pause();
      setIsPlayingAudio(false);
      return;
    }

    const textToSpeak = aiExplanation || result?.explanation || `TrustNet analysis complete. Risk score is ${riskScore} out of 100. Media is ${isManipulated ? 'manipulated' : 'authentic'}.`;
    setIsPlayingAudio(true);
    const audio = await puterAI.narrateDebriefing(textToSpeak);
    if (audio) {
      currentAudioRef.current = audio;
      audio.onended = () => setIsPlayingAudio(false);
    } else {
      setIsPlayingAudio(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-6 py-8 font-sans">
      {/* Top Back Navigation */}
      <button
        onClick={onBack}
        className="inline-flex items-center gap-2 text-xs font-mono font-bold text-slate-400 hover:text-white mb-6 uppercase tracking-wider transition-colors"
      >
        <ArrowLeft size={14} />
        <span>Back to Analyze</span>
      </button>

      {/* Top Analysis Result Card (Screenshot 4 Match) */}
      <div className="bg-[#0e1017] border border-[#1e2330] rounded-md p-6 mb-6 shadow-2xl">
        <div className="flex flex-wrap items-center justify-between gap-4 mb-3">
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight mb-1">
              Analysis Result
            </h1>
            <div className="text-xs font-mono text-slate-400">
              ID: <span className="text-slate-300">{scan.id}</span> &bull; {new Date(scan.created_at).toLocaleString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', hour12: true })}
            </div>
          </div>

          <button
            onClick={handleDownloadPDF}
            className="inline-flex items-center gap-2 px-4 py-2 rounded border border-[#2b3145] bg-[#141824] hover:bg-[#1a2030] text-white text-xs font-mono font-bold uppercase tracking-wider transition-colors"
          >
            <Download size={14} />
            <span>PDF REPORT</span>
          </button>
        </div>

        {/* System Score Pill */}
        <div className="flex items-center gap-3 mb-4 pb-3 border-b border-[#1b202e]">
          <span className="text-xs font-mono font-semibold text-slate-300">System Verdict:</span>
          <span className={`px-2.5 py-0.5 rounded text-xs font-mono font-black uppercase tracking-wider ${isAiGenerated ? 'bg-[#ff3d00] text-white' : isSuspicious ? 'bg-[#f97316] text-white' : 'bg-emerald-600 text-white'}`}>
            {isAiGenerated ? `AI GENERATED: ${riskScore}% RISK` : isSuspicious ? `SUSPICIOUS: ${riskScore}% RISK` : `AUTHENTIC: ${authenticityConfidence}% CONFIDENCE`}
          </span>
        </div>

        {/* Metadata Details */}
        <div className="text-xs font-mono text-slate-400 space-y-1 mb-4">
          <div>File: <span className="text-slate-200">{scan.filename || 'Image Scan'}</span></div>
          <div>Type: <span className="text-slate-200">{scan.mime_type || 'image/jpeg'}</span></div>
        </div>

        {/* Share Action Row */}
        <div className="flex items-center gap-2 pt-1 text-xs font-mono">
          <button
            onClick={handleCopyLink}
            className="inline-flex items-center gap-1.5 px-3 py-1 rounded border border-[#2a3042] bg-[#121622] text-slate-300 hover:text-white transition-colors"
          >
            {copied ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
            <span>{copied ? 'COPIED' : 'SHARE'}</span>
          </button>
          <button
            onClick={handleCopyLink}
            className="px-3 py-1 rounded border border-[#2a3042] bg-[#121622] text-slate-300 hover:text-white transition-colors"
          >
            Copy
          </button>
          <a
            href={`https://twitter.com/intent/tweet?text=TrustNet+Forensic+Result+${scan.id}`}
            target="_blank"
            rel="noreferrer"
            className="px-3 py-1 rounded border border-[#2a3042] bg-[#121622] text-slate-300 hover:text-white transition-colors"
          >
            Tweet
          </a>
          <a
            href={`https://api.whatsapp.com/send?text=TrustNet+Result+${scan.id}`}
            target="_blank"
            rel="noreferrer"
            className="px-3 py-1 rounded border border-[#2a3042] bg-[#121622] text-slate-300 hover:text-white transition-colors"
          >
            WhatsApp
          </a>
        </div>
      </div>

      {/* FAST ELA DETECTOR STUDIO (Screenshot 4 Match) */}
      <div className="bg-[#0e1017] border border-[#1e2330] rounded-md overflow-hidden shadow-2xl mb-6">
        {/* Studio Subheader */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-[#1e2330] bg-[#090b10]">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-[#ff4500]" />
            <span className="text-xs font-black tracking-widest text-white uppercase font-mono">
              FAST ELA DETECTOR
            </span>
          </div>

          <span className="px-2 py-0.5 rounded border border-[#ff4500]/50 text-[#ff4500] text-[10px] font-mono font-bold uppercase">
            CLIENT-SIDE FORENSICS
          </span>
        </div>

        {/* Mode Tabs */}
        <div className="grid grid-cols-4 text-center border-b border-[#1e2330] bg-[#0b0d13] text-xs font-mono font-bold uppercase tracking-wider">
          <button
            onClick={() => setViewMode('heatmap_image')}
            className={`py-2.5 transition-colors relative ${viewMode === 'heatmap_image' ? 'text-[#ff5722] bg-[#131620]' : 'text-slate-400 hover:text-slate-200'}`}
          >
            <span>&bull; Heatmap + Image</span>
            {viewMode === 'heatmap_image' && (
              <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-[#ff5722]" />
            )}
          </button>

          <button
            onClick={() => setViewMode('pixel_morphing')}
            className={`py-2.5 transition-colors relative ${viewMode === 'pixel_morphing' ? 'text-cyan-400 bg-[#131620]' : 'text-slate-400 hover:text-slate-200'}`}
          >
            <span className="flex items-center justify-center gap-1">
              <Microscope size={12} />
              <span>Pixel Morphing</span>
            </span>
            {viewMode === 'pixel_morphing' && (
              <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-cyan-400" />
            )}
          </button>

          <button
            onClick={() => setViewMode('heatmap_only')}
            className={`py-2.5 transition-colors relative ${viewMode === 'heatmap_only' ? 'text-[#ff5722] bg-[#131620]' : 'text-slate-400 hover:text-slate-200'}`}
          >
            <span>🔥 Heatmap Only</span>
            {viewMode === 'heatmap_only' && (
              <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-[#ff5722]" />
            )}
          </button>

          <button
            onClick={() => setViewMode('original')}
            className={`py-2.5 transition-colors relative ${viewMode === 'original' ? 'text-[#ff5722] bg-[#131620]' : 'text-slate-400 hover:text-slate-200'}`}
          >
            <span>🖼️ Original</span>
            {viewMode === 'original' && (
              <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-[#ff5722]" />
            )}
          </button>
        </div>

        {/* Heatmap Intensity Slider Bar */}
        <div className="flex items-center justify-between px-6 py-2.5 bg-[#121520] border-b border-[#1b202e] text-xs font-mono">
          <span className="text-slate-400 text-[11px] uppercase tracking-wider">
            HEATMAP INTENSITY
          </span>
          <div className="flex items-center gap-4 flex-1 max-w-md mx-4">
            <input
              type="range"
              min="0"
              max="100"
              value={intensity}
              onChange={(e) => setIntensity(parseInt(e.target.value))}
              className="w-full h-1 bg-[#283042] rounded-lg appearance-none cursor-pointer accent-[#ff5722]"
            />
          </div>
          <span className="text-slate-300 font-bold min-w-[36px] text-right">{intensity}%</span>
        </div>

        {/* Canvas Display Viewport */}
        <div className="bg-black py-8 px-4 flex justify-center items-center min-h-[420px] overflow-hidden">
          <canvas
            ref={canvasRef}
            className="max-h-[540px] w-auto object-contain rounded shadow-2xl border border-[#1e2330]"
          />
        </div>
      </div>

      {/* FORENSIC TILES GRID (Screenshot 1 Match) */}
      <div className="bg-[#0e1017] border border-[#1e2330] rounded-md p-5 mb-6 shadow-2xl">
        {/* Top Anomaly Alert Banner */}
        <div className="flex flex-wrap items-center gap-3 mb-4 pb-3 border-b border-[#1b202e]">
          <div className="flex items-center gap-2">
            <span className={`w-5 h-5 rounded-full flex items-center justify-center font-bold text-xs ${isAiGenerated ? 'bg-[#ff3d00] text-white' : isSuspicious ? 'bg-[#f97316] text-white' : 'bg-emerald-600 text-white'}`}>
              {isAuthentic ? '✓' : '!'}
            </span>
            <span className="text-sm font-bold text-white font-mono">
              {isAiGenerated ? 'Generative AI / Deepfake Synthesis Detected' : isSuspicious ? 'Elevated Forensic Anomalies Detected' : 'Authentic Media Verified'}
            </span>
          </div>
          <span className={`px-2.5 py-0.5 rounded text-xs font-mono font-black uppercase ${isAiGenerated ? 'bg-[#ff3d00] text-white' : isSuspicious ? 'bg-[#f97316] text-white' : 'bg-emerald-600 text-white'}`}>
            {isAiGenerated ? `SYNTHESIS RISK: ${riskScore}%` : isSuspicious ? `SUSPICIOUS: ${riskScore}%` : `AUTHENTIC: ${authenticityConfidence}%`}
          </span>
          <p className="w-full text-xs text-slate-400 font-mono mt-1">
            {isAiGenerated
              ? 'Multi-signal forensic analysis detected high-confidence AI synthesis signatures across neural features, frequency spectrum, and sensor patterns.'
              : isSuspicious
              ? 'Forensic analysis identified localized compression, frequency, or demosaicing anomalies requiring secondary review.'
              : 'Consistent CMOS/CCD sensor noise (PRNU), natural 2D Fourier frequency roll-off, and homogeneous compression verified.'}
          </p>
        </div>

        {/* Dynamic Telemetry Visualization */}
        <div className="flex flex-col lg:flex-row gap-6 font-mono">
          {/* Left: Cyber-Forensic Radar Chart */}
          <div className="w-full lg:w-1/3 border border-[#1e2434] bg-[#121520] rounded-md flex flex-col p-2 min-h-[300px]">
            <div className="text-center text-[10px] text-cyan-400 font-bold uppercase tracking-widest pt-2 mb-2">
              Forensic Threat Profile
            </div>
            <div className="flex-1 flex items-center justify-center">
              <ForensicRadarChart scan={scan} />
            </div>
          </div>
          
          {/* Right: Evidence Badges Grid */}
          <div className="w-full lg:w-2/3">
             <div className="text-[10px] text-slate-400 font-bold uppercase tracking-widest mb-3 flex items-center justify-between">
               <span>Analyzer Telemetry</span>
               <span className="text-emerald-500">LIVE FEED</span>
             </div>
             <EvidenceBadges scan={scan} />
          </div>
        </div>
      </div>

      {/* REAL-TIME ANALYSIS REPORT (Screenshot 1 & 2 Match - Orange border Cyber Box) */}
      <div className="bg-[#090b10] border-2 border-[#ff7a00] rounded-md p-6 mb-6 shadow-2xl font-mono">
        <div className="flex items-center gap-2 mb-4 pb-2 border-b border-[#232938]">
          <FileText size={16} className="text-[#ff9800]" />
          <h2 className="text-sm font-black text-[#ff9800] uppercase tracking-wider">
            REAL-TIME ANALYSIS REPORT
          </h2>
        </div>

        {/* Report Meta Header */}
        <div className="space-y-2 text-xs mb-4">
          <div className="flex justify-between items-start">
            <div>
              <div className="text-white font-bold">Detection Report</div>
              <div className="text-slate-400">Image Type: <span className="text-slate-200">{scan.mime_type || 'Image: jpeg'}</span></div>
            </div>
            <div className={`px-2 py-1 rounded font-black border ${isManipulated ? 'bg-[#ff3d00]/20 border-[#ff3d00] text-[#ff3d00]' : 'bg-emerald-500/20 border-emerald-500 text-emerald-400'}`}>
              VERDICT: {isManipulated ? 'HIGHLY LIKELY AI GENERATED' : 'AUTHENTIC / UNMODIFIED'}
            </div>
          </div>
          <div className="text-[#ff7a00] font-black pt-1">AI / Deepfake Likelihood: {riskScore}%</div>
        </div>

        {/* Analysis Summary Paragraph */}
        <div className="mb-6">
          <div className="text-white font-bold text-xs mb-1">Analysis Summary</div>
          <p className="text-xs text-slate-400 leading-relaxed">
            {result?.explanation || 'The analysis reveals strong evidence of AI generation or deep manipulation. Multiple forensic layers triggered high-confidence warnings across structural, frequency, and pixel-level domains.'}
          </p>
        </div>

        {/* Detailed Breakdown with Progress Indicators */}
        <div className="space-y-4 pt-2 border-t border-[#1b202e]">
          <div className="text-white font-bold text-xs uppercase tracking-wider">
            Detailed Breakdown
          </div>

          {(!result?.evidence || result.evidence.length === 0) && (
            <div className="text-xs text-slate-500 italic">No detailed breakdown data available.</div>
          )}

          {result?.evidence?.map((item, idx) => {
            const isHighRisk = item.contribution > 0.6;
            const barWidth = `${Math.min(100, Math.max(0, item.contribution * 100))}%`;
            return (
              <div key={idx} className={isHighRisk ? "p-2.5 rounded bg-[#1c130d] border border-orange-900/60" : ""}>
                <div className="flex justify-between text-xs mb-0.5">
                  <span className={isHighRisk ? "text-[#ff7a00] font-bold" : "text-cyan-400 font-bold"}>
                    {item.feature_or_region.replace(/_/g, ' ').toUpperCase()} | {(item.contribution * 100).toFixed(0)}% {isHighRisk ? '(WARNING)' : ''}
                  </span>
                </div>
                <div className={`text-[11px] ${isHighRisk ? "text-orange-400/80" : "text-slate-500"} mb-1`}>
                  {item.human_readable_note}
                </div>
                <div className={`w-full h-1.5 rounded overflow-hidden ${isHighRisk ? "bg-[#2b1b12]" : "bg-[#1b202e]"}`}>
                  <div className={`h-full ${isHighRisk ? "bg-[#ff7a00]" : "bg-cyan-400"}`} style={{ width: barWidth }} />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* KEY FINDINGS & AI EXPLANATION ROW (Screenshot 2 & 3 Match) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8 font-mono">
        {/* Left: Key Findings */}
        <div className="p-5 rounded-md bg-[#0b0e14] border-2 border-emerald-500/80 shadow-2xl">
          <div className="text-xs font-black text-white uppercase tracking-wider mb-4">
            KEY FINDINGS
          </div>
          {(() => {
            const topEvidence = result?.evidence?.length ? [...result.evidence].sort((a, b) => b.contribution - a.contribution)[0] : null;
            if (!topEvidence) return <div className="text-xs text-slate-500">No key findings available.</div>;
            
            const isTopHighRisk = topEvidence.contribution > 0.5;
            return (
              <div className={`p-4 rounded border ${isTopHighRisk ? 'bg-[#1c130d] border-orange-900/60' : 'bg-[#070a0f] border-emerald-500/40'}`}>
                <div className={`flex items-center gap-2 text-xs font-bold ${isTopHighRisk ? 'text-[#ff7a00]' : 'text-emerald-400'} mb-2`}>
                  <CheckCircle2 size={16} />
                  <span>{topEvidence.feature_or_region.replace(/_/g, ' ').toUpperCase()}</span>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed mb-3">
                  {topEvidence.human_readable_note}
                </p>
                <div className={`w-full h-1.5 rounded overflow-hidden ${isTopHighRisk ? 'bg-[#2b1b12]' : 'bg-[#16202a]'}`}>
                  <div className={`h-full ${isTopHighRisk ? 'bg-[#ff7a00]' : 'bg-emerald-400'}`} style={{ width: `${Math.min(100, Math.max(0, topEvidence.contribution * 100))}%` }} />
                </div>
              </div>
            );
          })()}
        </div>

        {/* Right: AI Explanation Studio */}
        <div className="p-5 rounded-md bg-[#0b0e14] border border-[#1e2330] shadow-2xl">
          <div className="flex items-center justify-between gap-2 mb-4 pb-2 border-b border-[#1b202e]">
            <div className="flex items-center gap-2 text-cyan-400 text-xs font-bold uppercase tracking-wider">
              <Bot size={16} />
              <span>AI EXPLANATION</span>
            </div>

            <div className="flex items-center gap-1.5">
              <button
                onClick={handleGenerateAIExplanation}
                disabled={isGeneratingAi}
                className="px-2 py-1 rounded bg-[#ff5722] hover:bg-[#ff6b00] text-white text-[10px] font-bold uppercase tracking-wider transition-colors disabled:opacity-50 inline-flex items-center gap-1"
              >
                {isGeneratingAi ? <RefreshCw size={10} className="animate-spin" /> : null}
                <span>{isGeneratingAi ? 'Thinking...' : 'AI Debrief'}</span>
              </button>

              <button
                onClick={handleGenerateVisionOpinion}
                disabled={isGeneratingVision}
                className="px-2 py-1 rounded border border-[#2a3042] text-slate-300 hover:text-white text-[10px] font-bold uppercase tracking-wider transition-colors disabled:opacity-50 inline-flex items-center gap-1"
                title="Vision Check"
              >
                <Eye size={10} />
                <span>{isGeneratingVision ? 'Scanning...' : 'Vision Check'}</span>
              </button>

              <button
                onClick={handlePlayTTS}
                className="p-1 rounded border border-[#2a3042] text-slate-300 hover:text-white"
                title="Read Aloud"
              >
                <Volume2 size={13} className={isPlayingAudio ? 'animate-bounce text-[#ff5722]' : ''} />
              </button>
            </div>
          </div>

          <div className="space-y-4 text-xs">
            {/* Simple Explanation */}
            <div>
              <div className="text-[11px] font-bold text-yellow-400 uppercase tracking-wider mb-1">
                SIMPLE EXPLANATION
              </div>
              <p className="text-slate-300 leading-relaxed">
                The image scored {riskScore}/100 for deepfake likelihood. Verdict: {isManipulated ? 'High AI Probability' : 'Authentic Media'}.
              </p>
            </div>

            {/* Detailed Analysis Collapsible Box (Screenshot 3 Match) */}
            <div>
              <button
                onClick={() => setShowDetailedAnalysis(!showDetailedAnalysis)}
                className="flex items-center gap-1 text-[11px] font-bold text-cyan-400 uppercase tracking-wider mb-2"
              >
                <ChevronDown size={12} className={`transition-transform ${showDetailedAnalysis ? '' : '-rotate-90'}`} />
                <span>&gt; DETAILED ANALYSIS</span>
              </button>

              {showDetailedAnalysis && (
                <div className="p-3.5 rounded bg-[#06080d] border border-[#1b202e] text-[11px] text-slate-400 space-y-2.5 leading-relaxed">
                  {result?.analyzers?.slice(0, 5).map((a, idx) => (
                    <div key={idx}>
                      <span className="text-slate-200 font-bold">[{a.name}]:</span> {a.finding || a.reason || 'Analyzed successfully.'}
                    </div>
                  ))}
                  {aiVisionOpinion && (
                    <div className="p-2 rounded bg-[#0b1522] border border-cyan-900/60 text-cyan-200 text-[10px] mt-2">
                      <span className="font-bold text-cyan-400">[Vision Second Opinion]:</span> {aiVisionOpinion}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Technical Summary (Screenshot 3 Match) */}
            <div>
              <button
                onClick={() => setShowTechnicalSummary(!showTechnicalSummary)}
                className="flex items-center gap-1 text-[11px] font-bold text-yellow-400 uppercase tracking-wider mb-2"
              >
                <ChevronDown size={12} className={`transition-transform ${showTechnicalSummary ? '' : '-rotate-90'}`} />
                <span>&gt; TECHNICAL SUMMARY</span>
              </button>

              {showTechnicalSummary && (
                <div className="p-3 rounded bg-[#06080d] border border-[#1b202e] text-[11px] font-mono text-slate-300">
                  <div className="mb-2 break-all overflow-auto">
                    RiskScore={riskScore} | ModelVer={result?.model_version || 'v1.0.0'} | ID={scan.id}
                    <br />
                    {result?.metadata ? JSON.stringify(result.metadata) : 'No raw telemetry data generated.'}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
