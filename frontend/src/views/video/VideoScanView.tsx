import React, { useState, useRef } from 'react';
import { Film, ArrowRight } from 'lucide-react';
import type { ScanRecord } from '../../types';

interface VideoScanViewProps {
  onScanCompleted: (scan: ScanRecord) => void;
  onViewReport: (scan: ScanRecord) => void;
}

export const VideoScanView: React.FC<VideoScanViewProps> = ({ onScanCompleted, onViewReport }) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [progress, setProgress] = useState<number>(0);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const handleFileSelect = (file: File) => {
    setSelectedFile(file);
    setPreviewUrl(URL.createObjectURL(file));
  };

  const handleAnalyze = () => {
    if (!selectedFile) return;
    setIsProcessing(true);
    setProgress(15);

    const interval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 90) {
          clearInterval(interval);
          return 90;
        }
        return prev + 25;
      });
    }, 400);

    setTimeout(() => {
      clearInterval(interval);
      setProgress(100);
      setIsProcessing(false);

      const mockVideoScan: ScanRecord = {
        id: 'scan-vid-' + Math.random().toString(36).substring(2, 9),
        user_id: 'usr-analyst-1',
        status: 'SUCCESS',
        content_type: 'video',
        filename: selectedFile.name,
        file_size_bytes: selectedFile.size,
        mime_type: selectedFile.type || 'video/mp4',
        created_at: new Date().toISOString(),
        result: {
          scan_id: 'scan-vid-' + Math.random().toString(36).substring(2, 9),
          module: 'video_deepfake',
          detector_id: 'video_deepfake.temporal_sync.v2',
          model_version: 'v2.1.0',
          preprocessing_version: 'v2.0.0',
          native_score: 0.18,
          native_score_semantics: 'probability_of_negative_class',
          risk_score: 82,
          confidence: 0.93,
          label: 'fake',
          verdict: 'AI_GENERATED',
          has_face: true,
          status: 'SUCCESS',
          evidence: [
            {
              feature_or_region: 'temporal_jitter_inconsistency',
              contribution: 0.85,
              human_readable_note: 'Inter-frame landmark position variance exhibits synthetic generation artifacts.',
            },
            {
              feature_or_region: 'audio_visual_sync_offset',
              contribution: 0.79,
              human_readable_note: 'Lip phoneme movement lags speech audio by 140ms, indicating dubbing/reenactment.',
            },
          ],
          analyzers: [
            { name: 'Temporal Consistency RNN-CNN', category: 'temporal', status: 'APPLIED', finding: 'High probability of face swap or reenactment deepfake.' },
            { name: 'Lip Sync Alignment Network', category: 'multimodal', status: 'APPLIED', finding: 'Detected phoneme-to-viseme desynchronization.' },
          ],
          processing_time_ms: 1250,
          timestamp: new Date().toISOString(),
        },
        trust_score: {
          scan_id: 'scan-vid-' + Math.random().toString(36).substring(2, 9),
          trust_risk_score: 82,
          risk_level: 'CRITICAL',
          reporting_modules: ['video_deepfake'],
          module_scores: { video_deepfake: 82 },
          confidence: 0.93,
          contradiction_detected: false,
          evidence: [
            {
              feature_or_region: 'temporal_jitter_inconsistency',
              contribution: 0.85,
              human_readable_note: 'Video frames reveal digital manipulation: unnatural facial blending and desynchronized speech.',
            },
          ],
          explanation: 'TrustNet detected face-swap and audio-visual synchronization anomalies. This video clip exhibits synthetic reenactment artifacts.',
          timestamp: new Date().toISOString(),
        },
      };

      onScanCompleted(mockVideoScan);
      onViewReport(mockVideoScan);
    }, 2200);
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-[#111d38] border border-[#1e3a5f] rounded-2xl p-6 shadow-3d-card mb-6">
        <div className="flex items-center justify-between border-b border-[#1e3a5f] pb-4 mb-6">
          <div>
            <h2 className="text-xl font-bold text-[#f8fafc] font-serif">
              Deepfake Video &amp; Face-Swap Scanner
            </h2>
            <p className="text-xs text-[#94a3b8] mt-0.5">
              Evaluates frame-by-frame stability, audio-visual lip synchronization, and synthetic reenactment artifacts.
            </p>
          </div>
          <span className="px-2.5 py-1 rounded-full text-[10px] font-mono font-bold bg-[#0b132b] text-[#00b4d8] border border-[#1e3a5f]">
            Videos &amp; Clips
          </span>
        </div>

        <input
          ref={fileInputRef}
          type="file"
          accept="video/mp4,video/webm,video/quicktime"
          className="hidden"
          onChange={(e) => {
            if (e.target.files && e.target.files.length > 0) {
              handleFileSelect(e.target.files[0]);
            }
          }}
        />

        {previewUrl ? (
          <div className="mb-6">
            <div className="rounded-xl overflow-hidden bg-black border border-[#1e3a5f] shadow-md aspect-video max-h-72 mx-auto flex items-center justify-center">
              <video src={previewUrl} controls className="w-full h-full object-contain" />
            </div>
            <div className="flex items-center justify-between mt-3 text-xs font-mono text-[#94a3b8]">
              <span className="font-bold text-[#f8fafc]">{selectedFile?.name}</span>
              <button
                onClick={() => fileInputRef.current?.click()}
                className="text-[#00b4d8] hover:underline font-semibold cursor-pointer"
              >
                Change Video
              </button>
            </div>
          </div>
        ) : (
          <div
            onClick={() => fileInputRef.current?.click()}
            className="border-2 border-dashed border-[#1e3a5f] hover:border-[#00b4d8] bg-[#0b132b]/80 rounded-xl p-8 text-center cursor-pointer mb-6"
          >
            <div className="w-12 h-12 rounded-xl bg-[#132247] border border-[#1e3a5f] flex items-center justify-center text-[#00b4d8] mx-auto mb-3">
              <Film size={24} />
            </div>
            <h3 className="text-sm font-bold text-[#f8fafc] mb-1">
              Upload Video Clip for Verification
            </h3>
            <p className="text-xs text-[#94a3b8] mb-3">
              Supports MP4, WebM, and MOV formats (up to 100 MB).
            </p>
            <button
              type="button"
              className="px-4 py-2 rounded-lg bg-[#1c2541] border border-[#1e3a5f] text-xs font-bold text-[#f8fafc] hover:bg-[#223359] shadow-sm"
            >
              Select Video
            </button>
          </div>
        )}

        {isProcessing && (
          <div className="mb-6 p-4 rounded-xl bg-[#0b132b] border border-[#1e3a5f]">
            <div className="flex items-center justify-between text-xs font-mono font-bold mb-2">
              <span className="text-[#f8fafc]">Deconstructing Video Frames (60 FPS)...</span>
              <span className="text-[#00b4d8]">{progress}%</span>
            </div>
            <div className="w-full h-2 bg-[#1c2541] rounded-full overflow-hidden">
              <div
                className="h-full bg-[#0077b6] transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
            <div className="grid grid-cols-3 gap-2 mt-3 text-[11px] font-mono text-[#94a3b8]">
              <span>&bull; Frame Extraction</span>
              <span>&bull; Lip-Sync Analysis</span>
              <span>&bull; Temporal Variance</span>
            </div>
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
            <span>{isProcessing ? 'Analyzing Video...' : 'Run Video Deepfake Scan'}</span>
            <ArrowRight size={14} />
          </button>
        </div>
      </div>
    </div>
  );
};
