import React, { useState, useRef } from 'react';
import { Mic, Volume2, ArrowRight, Activity } from 'lucide-react';
import type { ScanRecord } from '../../types';

interface AudioScanViewProps {
  onScanCompleted: (scan: ScanRecord) => void;
  onViewReport: (scan: ScanRecord) => void;
}

export const AudioScanView: React.FC<AudioScanViewProps> = ({ onScanCompleted, onViewReport }) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const handleFileSelect = (file: File) => {
    setSelectedFile(file);
  };

  const handleAnalyze = () => {
    if (!selectedFile) return;
    setIsProcessing(true);

    setTimeout(() => {
      setIsProcessing(false);

      const mockAudioScan: ScanRecord = {
        id: 'scan-aud-' + Math.random().toString(36).substring(2, 9),
        user_id: 'usr-analyst-1',
        status: 'SUCCESS',
        content_type: 'audio',
        filename: selectedFile.name,
        file_size_bytes: selectedFile.size,
        mime_type: selectedFile.type || 'audio/wav',
        created_at: new Date().toISOString(),
        result: {
          scan_id: 'scan-aud-' + Math.random().toString(36).substring(2, 9),
          module: 'audio_deepfake',
          detector_id: 'audio_deepfake.vocoder_flux.v1',
          model_version: 'v1.4.0',
          preprocessing_version: 'v1.2.0',
          native_score: 0.15,
          native_score_semantics: 'probability_of_negative_class',
          risk_score: 85,
          confidence: 0.95,
          label: 'fake',
          verdict: 'AI_GENERATED',
          has_face: false,
          status: 'SUCCESS',
          evidence: [
            {
              feature_or_region: 'synthetic_vocoder_harmonics',
              contribution: 0.89,
              human_readable_note: 'Unnatural phase uniformity and high-frequency spectral cutoff consistent with neural vocoder speech synthesis.',
            },
            {
              feature_or_region: 'pitch_contour_flatness',
              contribution: 0.76,
              human_readable_note: 'Robotic prosody variance and missing natural micro-tremors in fundamental frequency (F0).',
            },
          ],
          analyzers: [
            { name: 'Spectral Vocoder Flux Detector', category: 'acoustic', status: 'APPLIED', finding: 'High probability of ElevenLabs or VITS synthetic voice clone.' },
            { name: 'Prosody Micro-Tremor Evaluator', category: 'biometric', status: 'APPLIED', finding: 'Robotic fundamental frequency variance detected.' },
          ],
          processing_time_ms: 620,
          timestamp: new Date().toISOString(),
        },
        trust_score: {
          scan_id: 'scan-aud-' + Math.random().toString(36).substring(2, 9),
          trust_risk_score: 85,
          risk_level: 'CRITICAL',
          reporting_modules: ['audio_deepfake'],
          module_scores: { audio_deepfake: 85 },
          confidence: 0.95,
          contradiction_detected: false,
          evidence: [
            {
              feature_or_region: 'synthetic_vocoder_harmonics',
              contribution: 0.89,
              human_readable_note: 'Voice audio shows robotic pitch patterns and missing natural vocal cords micro-tremors. Cloned voice detected.',
            },
          ],
          explanation: 'Warning: This audio recording contains high evidence of voice cloning or AI text-to-speech generation commonly used in impersonation scams.',
          timestamp: new Date().toISOString(),
        },
      };

      onScanCompleted(mockAudioScan);
      onViewReport(mockAudioScan);
    }, 1800);
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-[#111d38] border border-[#1e3a5f] rounded-2xl p-6 shadow-3d-card mb-6">
        <div className="flex items-center justify-between border-b border-[#1e3a5f] pb-4 mb-6">
          <div>
            <h2 className="text-xl font-bold text-[#f8fafc] font-serif">
              Voice Clone &amp; Audio Deepfake Scanner
            </h2>
            <p className="text-xs text-[#94a3b8] mt-0.5">
              Inspect voice notes, recorded phone calls, and speech files for AI voice synthesis and cloned speech.
            </p>
          </div>
          <span className="px-2.5 py-1 rounded-full text-[10px] font-mono font-bold bg-[#0b132b] text-[#00b4d8] border border-[#1e3a5f]">
            Audio &amp; Voice Notes
          </span>
        </div>

        <input
          ref={fileInputRef}
          type="file"
          accept="audio/wav,audio/mpeg,audio/mp3,audio/m4a,audio/flac"
          className="hidden"
          onChange={(e) => {
            if (e.target.files && e.target.files.length > 0) {
              handleFileSelect(e.target.files[0]);
            }
          }}
        />

        {selectedFile ? (
          <div className="p-6 rounded-xl bg-[#0b132b] border border-[#1e3a5f] mb-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-purple-950/70 border border-purple-800 text-purple-400 flex items-center justify-center">
                  <Volume2 size={20} />
                </div>
                <div>
                  <h4 className="text-sm font-bold text-[#f8fafc]">{selectedFile.name}</h4>
                  <span className="text-[11px] font-mono text-[#94a3b8]">
                    {(selectedFile.size / 1024).toFixed(1)} KB &bull; Ready for biometric voiceprint scan
                  </span>
                </div>
              </div>
              <button
                onClick={() => fileInputRef.current?.click()}
                className="text-xs font-semibold text-[#00b4d8] hover:underline cursor-pointer"
              >
                Change File
              </button>
            </div>

            {/* Simulated Spectral Waveform */}
            <div className="h-16 flex items-center justify-between gap-1 px-4 py-2 rounded-lg bg-[#080e20] border border-[#1e3a5f]">
              {Array.from({ length: 48 }).map((_, i) => (
                <div
                  key={i}
                  className="w-1 bg-[#00b4d8] rounded-full transition-all duration-300"
                  style={{
                    height: `${20 + ((i * 17) % 65)}%`,
                    opacity: 0.4 + ((i % 5) * 0.15),
                  }}
                />
              ))}
            </div>
          </div>
        ) : (
          <div
            onClick={() => fileInputRef.current?.click()}
            className="border-2 border-dashed border-[#1e3a5f] hover:border-[#00b4d8] bg-[#0b132b]/80 rounded-xl p-8 text-center cursor-pointer mb-6"
          >
            <div className="w-12 h-12 rounded-xl bg-[#132247] border border-[#1e3a5f] flex items-center justify-center text-[#00b4d8] mx-auto mb-3">
              <Mic size={24} />
            </div>
            <h3 className="text-sm font-bold text-[#f8fafc] mb-1">
              Upload Audio File for Voice Clone Detection
            </h3>
            <p className="text-xs text-[#94a3b8] mb-3">
              Supports WAV, MP3, M4A, and FLAC audio files (up to 50 MB).
            </p>
            <button
              type="button"
              className="px-4 py-2 rounded-lg bg-[#1c2541] border border-[#1e3a5f] text-xs font-bold text-[#f8fafc] hover:bg-[#223359] shadow-sm"
            >
              Select Audio File
            </button>
          </div>
        )}

        {isProcessing && (
          <div className="mb-6 p-4 rounded-xl bg-[#0b132b] border border-[#1e3a5f] text-xs font-mono text-[#00b4d8] flex items-center gap-3">
            <Activity size={18} className="animate-spin text-[#00b4d8]" />
            <span>Analyzing voice pitch contours, micro-tremors, and vocoder harmonics...</span>
          </div>
        )}

        <div className="flex items-center justify-end pt-4 border-t border-[#1e3a5f]">
          <button
            onClick={handleAnalyze}
            disabled={!selectedFile || isProcessing}
            className={`px-6 py-2.5 rounded-xl font-bold text-xs flex items-center gap-2 transition-all cursor-pointer ${
              !selectedFile || isProcessing
                ? 'bg-[#1c2541] text-[#64748b] border border-[#1e3a5f] cursor-not-allowed'
                : 'bg-[#0077b6] hover:bg-[#0096c7] text-white shadow-3d-sm'
            }`}
          >
            <span>{isProcessing ? 'Analyzing Voiceprint...' : 'Scan Voice Biometrics'}</span>
            <ArrowRight size={14} />
          </button>
        </div>
      </div>
    </div>
  );
};
