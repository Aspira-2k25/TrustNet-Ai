import React, { useState, useRef } from 'react';
import { UploadCloud, Link as LinkIcon, Camera, Shield, AlertTriangle, RefreshCw, Sparkles } from 'lucide-react';
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
  const [enableExplanation, setEnableExplanation] = useState<boolean>(false);
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
      const scanRecord = await api.uploadImageScan(selectedFile, enableExplanation);
      onScanCompleted(scanRecord);
      onViewReport(scanRecord);
    } catch (err: any) {
      setErrorMessage(err.message || 'Analysis failed. Please check backend service connection.');
    } finally {
      setIsProcessing(false);
    }
  };

  const modalityTabs = [
    { key: 'upload' as const, label: 'Upload', icon: <UploadCloud size={15} /> },
    { key: 'url' as const, label: 'URL', icon: <LinkIcon size={14} /> },
    { key: 'camera' as const, label: 'Camera', icon: <Camera size={14} /> },
  ];

  return (
    <div className="max-w-5xl mx-auto px-6 py-14 text-center">
      {/* Header Badge */}
      <div className="inline-flex items-center gap-2 px-3.5 py-1.5 mb-5 rounded-full bg-primary/10 border border-primary/20 text-primary text-xs font-semibold">
        <Shield size={13} />
        <span>Analyze</span>
      </div>

      {/* Main Title */}
      <h1 className="text-4xl sm:text-5xl font-extrabold text-foreground tracking-tight mb-3">
        Scan for <span className="text-primary">Deepfakes</span>
      </h1>
      <p className="text-[15px] text-muted-foreground max-w-lg mx-auto mb-10">
        Upload an image, video, or audio file for AI-powered forensic analysis and pixel-level artifact detection.
      </p>

      {/* Modality Selector Tabs */}
      <div className="flex items-center justify-center gap-1 mb-8 p-1 bg-card border border-border shadow-sm rounded-xl max-w-xs mx-auto">
        {modalityTabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveModality(tab.key)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors flex-1 justify-center ${
              activeModality === tab.key
                ? 'text-primary-foreground bg-primary shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            {tab.icon}
            <span>{tab.label}</span>
          </button>
        ))}
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

      {/* Clean Dropzone */}
      <div className="max-w-2xl mx-auto mb-8">
        <div
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border border-dashed rounded-2xl p-12 cursor-pointer transition-all bg-card ${isDragging ? 'border-primary bg-primary/5' : 'border-border hover:border-slate-300'}`}
        >
          {previewUrl ? (
            <div className="flex flex-col items-center gap-4">
              <img
                src={previewUrl}
                alt="Upload Preview"
                className="max-h-64 w-auto object-contain rounded-xl border border-border shadow-md"
              />
              <div className="text-sm text-muted-foreground">
                <span className="text-foreground font-medium">{selectedFile?.name}</span>{' '}
                <span>({selectedFile?.size ? (selectedFile.size / 1024).toFixed(1) : 0} KB)</span>
              </div>
              <span className="text-xs text-primary hover:text-indigo-500 cursor-pointer">Choose a different file</span>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-3">
              <div className="w-14 h-14 rounded-2xl bg-primary/10 flex items-center justify-center text-primary">
                <UploadCloud size={28} />
              </div>
              <div>
                <h3 className="text-base font-semibold text-foreground mb-1">
                  Drag & drop media file
                </h3>
                <p className="text-sm text-muted-foreground">
                  JPG, PNG, MP4, AVI, WAV, MP3 — up to 100MB
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* AI Visual Explanation (TrustNet Vision AI) Toggle Switch */}
      <div className="max-w-xl mx-auto mb-6 p-4 rounded-xl bg-card border border-border shadow-sm flex items-center justify-between text-left transition-all">
        <div className="flex items-start gap-3">
          <div className={`p-2 rounded-lg ${enableExplanation ? 'bg-primary/20 text-primary' : 'bg-slate-100 text-muted-foreground'}`}>
            <Sparkles size={18} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-foreground">AI Visual Explanation</span>
              <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${enableExplanation ? 'bg-amber-50 border border-amber-200 text-amber-700' : 'bg-emerald-50 border border-emerald-200 text-emerald-700'}`}>
                {enableExplanation ? 'Deep Vision (~20s)' : 'Fast Instant (~1s)'}
              </span>
            </div>
            <p className="text-xs text-muted-foreground mt-0.5">
              {enableExplanation
                ? 'TrustNet Vision AI will inspect visual semantics & reasoning in detail.'
                : 'Fast Scan mode: Runs 10 deterministic physical forensics + local ViT in ~1 second.'}
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setEnableExplanation(!enableExplanation)}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${enableExplanation ? 'bg-primary' : 'bg-slate-200'}`}
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${enableExplanation ? 'translate-x-6' : 'translate-x-1'}`}
          />
        </button>
      </div>

      {errorMessage && (
        <div className="max-w-xl mx-auto flex items-center justify-center gap-2 p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm mb-6">
          <AlertTriangle size={15} />
          <span>{errorMessage}</span>
        </div>
      )}

      {isProcessing && (
        <div className="max-w-xl mx-auto p-4 rounded-xl bg-primary/10 border border-primary/20 text-primary text-sm mb-6 flex flex-col items-center gap-2">
          <div className="flex items-center gap-2 font-medium">
            <RefreshCw size={16} className="animate-spin text-primary" />
            <span>
              {enableExplanation
                ? 'Running Deep Forensics & TrustNet Vision Reasoning...'
                : 'Running Fast Forensics & ViT Neural Analysis...'}
            </span>
          </div>
          <p className="text-xs text-muted-foreground text-center">
            {enableExplanation
              ? 'Fusing physical forensic layers with local vision model. Processing in CPU mode...'
              : 'Evaluating 10 deterministic physical layers (FFT, CFA, ELA, PRNU, Gabor) + ViT in ~1 second...'}
          </p>
        </div>
      )}

      {/* Analyze Button */}
      <div className="flex flex-col items-center gap-3">
        <button
          onClick={handleAnalyze}
          disabled={!selectedFile || isProcessing}
          className={`inline-flex items-center gap-2.5 px-10 py-3.5 rounded-xl text-sm font-semibold transition-all ${!selectedFile || isProcessing ? 'bg-slate-100 text-slate-400 border border-border cursor-not-allowed' : 'bg-primary hover:bg-indigo-500 text-primary-foreground shadow-sm'}`}
        >
          {isProcessing ? (
            <>
              <RefreshCw size={16} className="animate-spin" />
              <span>Analyzing Image Forensics...</span>
            </>
          ) : (
            <>
              <Shield size={16} />
              <span>Analyze Now</span>
            </>
          )}
        </button>

        <span className="text-xs text-muted-foreground mt-2">
          Powered by TrustNet AI — Multi-signal parallel engines
        </span>
      </div>
    </div>
  );
};
