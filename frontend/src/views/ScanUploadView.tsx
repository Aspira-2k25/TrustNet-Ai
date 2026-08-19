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

  const modalityTabs = [
    { key: 'upload' as const, label: 'Upload', icon: <UploadCloud size={15} /> },
    { key: 'url' as const, label: 'URL', icon: <LinkIcon size={14} /> },
    { key: 'camera' as const, label: 'Camera', icon: <Camera size={14} /> },
  ];

  return (
    <div className="max-w-5xl mx-auto px-6 py-14 text-center">
      {/* Header Badge */}
      <div className="inline-flex items-center gap-2 px-3.5 py-1.5 mb-5 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-semibold">
        <Shield size={13} />
        <span>Analyze</span>
      </div>

      {/* Main Title */}
      <h1 className="text-4xl sm:text-5xl font-extrabold text-white tracking-tight mb-3">
        Scan for <span className="text-indigo-400">Deepfakes</span>
      </h1>
      <p className="text-[15px] text-slate-400 max-w-lg mx-auto mb-10">
        Upload an image, video, or audio file for AI-powered forensic analysis and pixel-level artifact detection.
      </p>

      {/* Modality Selector Tabs */}
      <div className="flex items-center justify-center gap-1 mb-8 p-1 bg-[#13161f] border border-[#1e2231] rounded-xl max-w-xs mx-auto">
        {modalityTabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveModality(tab.key)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors flex-1 justify-center ${
              activeModality === tab.key
                ? 'text-white bg-indigo-600'
                : 'text-slate-400 hover:text-slate-200'
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
          className={`border border-dashed rounded-2xl p-12 cursor-pointer transition-all bg-[#13161f]/60 ${isDragging ? 'border-indigo-500 bg-indigo-500/5' : 'border-[#2a2f3e] hover:border-slate-500'}`}
        >
          {previewUrl ? (
            <div className="flex flex-col items-center gap-4">
              <img
                src={previewUrl}
                alt="Upload Preview"
                className="max-h-64 w-auto object-contain rounded-xl border border-[#1e2231] shadow-lg"
              />
              <div className="text-sm text-slate-300">
                <span className="text-white font-medium">{selectedFile?.name}</span>{' '}
                <span className="text-slate-500">({selectedFile?.size ? (selectedFile.size / 1024).toFixed(1) : 0} KB)</span>
              </div>
              <span className="text-xs text-indigo-400 hover:text-indigo-300 cursor-pointer">Choose a different file</span>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-3">
              <div className="w-14 h-14 rounded-2xl bg-indigo-500/10 flex items-center justify-center text-indigo-400">
                <UploadCloud size={28} />
              </div>
              <div>
                <h3 className="text-base font-semibold text-white mb-1">
                  Drag & drop media file
                </h3>
                <p className="text-sm text-slate-500">
                  JPG, PNG, MP4, AVI, WAV, MP3 — up to 100MB
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {errorMessage && (
        <div className="max-w-xl mx-auto flex items-center justify-center gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-300 text-sm mb-6">
          <AlertTriangle size={15} />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Analyze Button */}
      <div className="flex flex-col items-center gap-3">
        <button
          onClick={handleAnalyze}
          disabled={!selectedFile || isProcessing}
          className={`inline-flex items-center gap-2.5 px-10 py-3.5 rounded-xl text-sm font-semibold transition-all ${!selectedFile || isProcessing ? 'bg-[#1a1e2a] text-slate-600 border border-[#252a37] cursor-not-allowed' : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/20'}`}
        >
          {isProcessing ? (
            <>
              <RefreshCw size={16} className="animate-spin" />
              <span>Processing Media...</span>
            </>
          ) : (
            <>
              <Shield size={16} />
              <span>Analyze Now</span>
            </>
          )}
        </button>

        <span className="text-xs text-slate-500 mt-2">
          Powered by AACS — Multi-signal parallel AI engines
        </span>
      </div>
    </div>
  );
};
