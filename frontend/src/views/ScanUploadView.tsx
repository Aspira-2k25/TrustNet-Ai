import React, { useState, useRef } from 'react';
import { UploadCloud, Link as LinkIcon, Camera, Shield, AlertTriangle, RefreshCw } from 'lucide-react';
import { api } from '../services/api';
import type { ScanRecord } from '../types';

interface ScanUploadViewProps {
  onScanCompleted: (scan: ScanRecord) => void;
  onViewReport: (scan: ScanRecord) => void;
}

export const ScanUploadView: React.FC<ScanUploadViewProps> = ({ onScanCompleted, onViewReport }) => {
  const [activeModality, setActiveModality] = useState<'upload' | 'url' | 'camera'>('upload');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const handleFileSelect = (file: File) => {
    setErrorMessage(null);
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
      setErrorMessage('Invalid format. Please select a JPG, PNG, or WebP image.');
      return;
    }
    if (file.size > 25 * 1024 * 1024) {
      setErrorMessage('File size exceeds the 25 MB limit.');
      return;
    }
    setSelectedFile(file);
    setPreviewUrl(URL.createObjectURL(file));
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleAnalyze = async () => {
    if (!selectedFile) return;
    setIsProcessing(true);
    setErrorMessage(null);

    try {
      const scanRecord = await api.uploadImageScan(selectedFile);
      onScanCompleted(scanRecord);
      onViewReport(scanRecord);
    } catch (err: any) {
      setErrorMessage(err.message || 'Analysis failed. Please check backend service connection.');
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-6 py-12 text-center">
      {/* Header Badge */}
      <div className="inline-flex items-center gap-2 px-3 py-1 mb-4 text-[11px] font-mono font-bold tracking-widest text-[#ff5722] uppercase">
        <span>⚡ // ANALYZE</span>
      </div>

      {/* Main Title */}
      <h1 className="text-4xl sm:text-5xl font-black text-white tracking-tight mb-3">
        Scan for <span className="text-[#ff5722]">Deepfakes</span>
      </h1>
      <p className="text-sm text-slate-400 max-w-lg mx-auto mb-8">
        Upload an image, video, or audio file for AI-powered forensic analysis and pixel-level artifact detection.
      </p>

      {/* Modality Selector Tabs */}
      <div className="flex items-center justify-center gap-8 mb-6 border-b border-[#1c202d] pb-2 max-w-md mx-auto">
        <button
          onClick={() => setActiveModality('upload')}
          className={`flex items-center gap-2 text-xs font-bold uppercase tracking-wider pb-2 relative transition-colors ${activeModality === 'upload' ? 'text-[#ff5722]' : 'text-slate-500 hover:text-slate-300'}`}
        >
          <UploadCloud size={16} />
          <span>UPLOAD</span>
          {activeModality === 'upload' && (
            <span className="absolute bottom-[-9px] left-0 right-0 h-[2px] bg-[#ff5722]" />
          )}
        </button>

        <button
          onClick={() => setActiveModality('url')}
          className={`flex items-center gap-2 text-xs font-bold uppercase tracking-wider pb-2 relative transition-colors ${activeModality === 'url' ? 'text-[#ff5722]' : 'text-slate-500 hover:text-slate-300'}`}
        >
          <LinkIcon size={14} />
          <span>URL</span>
          {activeModality === 'url' && (
            <span className="absolute bottom-[-9px] left-0 right-0 h-[2px] bg-[#ff5722]" />
          )}
        </button>

        <button
          onClick={() => setActiveModality('camera')}
          className={`flex items-center gap-2 text-xs font-bold uppercase tracking-wider pb-2 relative transition-colors ${activeModality === 'camera' ? 'text-[#ff5722]' : 'text-slate-500 hover:text-slate-300'}`}
        >
          <Camera size={14} />
          <span>CAMERA</span>
          {activeModality === 'camera' && (
            <span className="absolute bottom-[-9px] left-0 right-0 h-[2px] bg-[#ff5722]" />
          )}
        </button>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="hidden"
        onChange={(e) => {
          if (e.target.files && e.target.files.length > 0) {
            handleFileSelect(e.target.files[0]);
          }
        }}
      />

      {/* Cyber-Dashed Dropzone with Cyan Corner Marks */}
      <div className="relative max-w-2xl mx-auto mb-8">
        {/* Cyan Corner Accents */}
        <div className="absolute -top-1 -left-1 w-4 h-4 border-t-2 border-l-2 border-cyan-400 pointer-events-none" />
        <div className="absolute -top-1 -right-1 w-4 h-4 border-t-2 border-r-2 border-cyan-400 pointer-events-none" />
        <div className="absolute -bottom-1 -left-1 w-4 h-4 border-b-2 border-l-2 border-cyan-400 pointer-events-none" />
        <div className="absolute -bottom-1 -right-1 w-4 h-4 border-b-2 border-r-2 border-cyan-400 pointer-events-none" />

        <div
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border border-dashed rounded-lg p-10 cursor-pointer transition-all bg-[#0a0c12]/80 ${isDragging ? 'border-[#ff5722] bg-orange-950/20' : 'border-[#1e2433] hover:border-slate-600'}`}
        >
          {previewUrl ? (
            <div className="flex flex-col items-center gap-4">
              <img
                src={previewUrl}
                alt="Upload Preview"
                className="max-h-64 w-auto object-contain rounded border border-[#212634] shadow-xl"
              />
              <div className="text-xs text-slate-300 font-mono">
                <span className="text-white font-semibold">{selectedFile?.name}</span> ({selectedFile?.size ? (selectedFile.size / 1024).toFixed(1) : 0} KB)
              </div>
              <span className="text-xs text-[#ff5722] underline cursor-pointer">Choose a different file</span>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-3">
              <div className="w-14 h-14 rounded-full bg-[#11141e] border border-[#212634] flex items-center justify-center text-slate-400">
                <UploadCloud size={28} />
              </div>
              <div>
                <h3 className="text-base font-bold text-white mb-1">
                  Drag &amp; drop media file
                </h3>
                <p className="text-xs font-mono text-slate-500">
                  JPG, PNG, MP4, AVI, WAV, MP3 — up to 100MB
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {errorMessage && (
        <div className="max-w-xl mx-auto flex items-center justify-center gap-2 p-3 rounded bg-rose-950/40 border border-rose-800/60 text-rose-300 text-xs mb-6">
          <AlertTriangle size={15} />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Glowing Orange ANALYZE NOW Button */}
      <div className="flex flex-col items-center gap-3">
        <button
          onClick={handleAnalyze}
          disabled={!selectedFile || isProcessing}
          className={`inline-flex items-center gap-2 px-10 py-3 rounded text-sm font-black uppercase tracking-widest transition-all ${!selectedFile || isProcessing ? 'bg-[#1a1e2a] text-slate-600 border border-[#23293a] cursor-not-allowed' : 'bg-gradient-to-r from-[#ff4500] to-[#ff6b00] hover:from-[#ff5722] hover:to-[#ff7a1a] text-white shadow-xl shadow-orange-500/30 hover:scale-[1.02]'}`}
        >
          {isProcessing ? (
            <>
              <RefreshCw size={16} className="animate-spin" />
              <span>Processing Media...</span>
            </>
          ) : (
            <>
              <Shield size={16} />
              <span>ANALYZE NOW</span>
            </>
          )}
        </button>

        <span className="text-[11px] font-mono text-slate-500 mt-2">
          Powered by AACS &mdash; Multi-signal parallel AI engines
        </span>
      </div>
    </div>
  );
};
