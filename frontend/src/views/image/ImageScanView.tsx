import React, { useState, useRef } from 'react';
import { UploadCloud, AlertTriangle, ArrowRight } from 'lucide-react';
import { api } from '../../services/api';
import type { ScanRecord } from '../../types';
import { ImageForensicScanner } from '../../components/image/ImageForensicScanner';

interface ImageScanViewProps {
  onScanCompleted: (scan: ScanRecord) => void;
  onViewReport: (scan: ScanRecord) => void;
}

export const ImageScanView: React.FC<ImageScanViewProps> = ({ onScanCompleted, onViewReport }) => {
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
      // Seamless transition to report/dashboard view for the image
      onViewReport(scanRecord);
    } catch (err: any) {
      setErrorMessage(err.message || 'Image forensic processing failed.');
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-[#111d38] border border-[#1e3a5f] rounded-2xl p-6 shadow-3d-card mb-6">
        <div className="flex items-center justify-between border-b border-[#1e3a5f] pb-4 mb-6">
          <div>
            <h2 className="text-xl font-bold text-[#f8fafc] font-serif">
              Deepfake Photo &amp; Image Verification
            </h2>
            <p className="text-xs text-[#94a3b8] mt-0.5">
              Multi-spectral forensic scan: 2D Fourier (FFT), Error Level Analysis (ELA), and PRNU sensor noise.
            </p>
          </div>
          <span className="px-2.5 py-1 rounded-full text-[10px] font-mono font-bold bg-[#0b132b] text-[#00b4d8] border border-[#1e3a5f]">
            Photos &amp; Portraits
          </span>
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

        {/* 3D Forensic Scanner or Interactive Dropzone */}
        {isProcessing && previewUrl ? (
          <div className="mb-6">
            <ImageForensicScanner
              imageUrl={previewUrl}
              fileName={selectedFile?.name}
              fileSize={selectedFile?.size}
              isDeepVision={enableExplanation}
            />
          </div>
        ) : (
          <div
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all mb-6 ${
              isDragging
                ? 'border-[#00b4d8] bg-[#0b132b]'
                : 'border-[#1e3a5f] hover:border-[#00b4d8] bg-[#0b132b]/80'
            }`}
          >
            {previewUrl ? (
              <div className="flex flex-col items-center">
                <img
                  src={previewUrl}
                  alt="Preview"
                  className="max-h-56 rounded-lg object-contain shadow-md mb-3 border border-[#1e3a5f]"
                />
                <span className="text-xs font-mono font-bold text-[#f8fafc]">{selectedFile?.name}</span>
                <span className="text-[11px] text-[#94a3b8] font-mono mt-0.5">
                  {selectedFile ? (selectedFile.size / 1024).toFixed(1) + ' KB' : ''} &bull; Click or drag to replace
                </span>
              </div>
            ) : (
              <div className="flex flex-col items-center">
                <div className="w-12 h-12 rounded-xl bg-[#132247] border border-[#1e3a5f] flex items-center justify-center text-[#00b4d8] mb-3">
                  <UploadCloud size={24} />
                </div>
                <h3 className="text-sm font-bold text-[#f8fafc] mb-1">
                  Upload Image File for Verification
                </h3>
                <p className="text-xs text-[#94a3b8] mb-3">
                  Supports JPEG, PNG, and WebP (up to 25 MB). Zero external retention.
                </p>
                <button
                  type="button"
                  className="px-4 py-2 rounded-lg bg-[#1c2541] border border-[#1e3a5f] text-xs font-bold text-[#f8fafc] hover:bg-[#223359] shadow-sm"
                >
                  Browse Files
                </button>
              </div>
            )}
          </div>
        )}

        {errorMessage && (
          <div className="p-3.5 mb-5 rounded-xl bg-red-950/70 border border-red-800 text-red-300 text-xs flex items-center gap-2">
            <AlertTriangle size={16} className="text-red-400 shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Scan Options and Submit */}
        <div className="flex flex-wrap items-center justify-between gap-4 pt-4 border-t border-[#1e3a5f]">
          <label className="flex items-center gap-2.5 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={enableExplanation}
              onChange={(e) => setEnableExplanation(e.target.checked)}
              className="w-4 h-4 rounded border-[#1e3a5f] text-[#0077b6] focus:ring-[#00b4d8] cursor-pointer"
            />
            <span className="text-xs font-semibold text-[#cbd5e1]">
              Enable Vision AI Reasoning
            </span>
          </label>

          <button
            onClick={handleAnalyze}
            disabled={!selectedFile || isProcessing}
            className={`px-6 py-2.5 rounded-xl font-bold text-xs flex items-center gap-2 transition-all cursor-pointer ${
              !selectedFile || isProcessing
                ? 'bg-[#1c2541] text-[#64748b] border border-[#1e3a5f] cursor-not-allowed'
                : 'bg-[#0077b6] hover:bg-[#0096c7] text-white shadow-3d-sm'
            }`}
          >
            <span>{isProcessing ? 'Processing 3D Forensics...' : 'Execute Image Scan'}</span>
            <ArrowRight size={14} className="text-[#38bdf8]" />
          </button>
        </div>
      </div>
    </div>
  );
};
