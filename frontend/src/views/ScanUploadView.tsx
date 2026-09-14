import React, { useState } from 'react';
import { ShieldCheck, Image, Film, Mic, Globe, MessageSquare, Star } from 'lucide-react';
import type { ScanRecord } from '../types';
import { ImageScanView } from './image/ImageScanView';
import { VideoScanView } from './video/VideoScanView';
import { AudioScanView } from './audio/AudioScanView';
import { PhishingScanView } from './phishing_url/PhishingScanView';
import { ScamMessageScanView } from './scam_message/ScamMessageScanView';
import { FakeReviewScanView } from './fake_review/FakeReviewScanView';

interface ScanUploadViewProps {
  onScanCompleted: (scan: ScanRecord) => void;
  onViewReport: (scan: ScanRecord) => void;
}

export type ModalityType = 'image' | 'video' | 'audio' | 'phishing' | 'scam_message' | 'fake_review';

export const ScanUploadView: React.FC<ScanUploadViewProps> = ({ onScanCompleted, onViewReport }) => {
  const [selectedModality, setSelectedModality] = useState<ModalityType>('image');

  const modalityTabs = [
    {
      id: 'image' as const,
      label: 'Deepfake Photos',
      icon: <Image size={16} />,
    },
    {
      id: 'video' as const,
      label: 'Deepfake Videos',
      icon: <Film size={16} />,
    },
    {
      id: 'audio' as const,
      label: 'Voice Clones',
      icon: <Mic size={16} />,
    },
    {
      id: 'phishing' as const,
      label: 'Phishing Websites',
      icon: <Globe size={16} />,
    },
    {
      id: 'scam_message' as const,
      label: 'Scam Messages',
      icon: <MessageSquare size={16} />,
    },
    {
      id: 'fake_review' as const,
      label: 'Fake Reviews (CSV Batch)',
      icon: <Star size={16} />,
    },
  ];

  return (
    <div className="max-w-6xl mx-auto px-6 py-10">
      {/* Header */}
      <div className="text-center max-w-2xl mx-auto mb-8">
        <div className="inline-flex items-center gap-2 px-3 py-1 mb-3 rounded-full bg-[#111d38] border border-[#1e3a5f] text-[#00b4d8] text-xs font-bold shadow-sm">
          <ShieldCheck size={14} className="text-[#00b4d8]" />
          <span>TrustNet AI Multi-Threat Scanner</span>
        </div>

        <h1 className="text-3xl sm:text-4xl font-bold text-[#f8fafc] font-serif tracking-tight mb-2">
          What Would You Like to Check?
        </h1>
        <p className="text-xs sm:text-sm text-[#94a3b8]">
          Select what type of content you want to inspect below. You will receive an immediate, clear verdict in seconds.
        </p>
      </div>

      {/* 6 Clean Category Switcher Tabs */}
      <div className="flex flex-wrap items-center justify-center gap-2 mb-10 p-1.5 bg-[#080e20] border border-[#1e3a5f] rounded-2xl max-w-4xl mx-auto shadow-3d-card">
        {modalityTabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setSelectedModality(tab.id)}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
              selectedModality === tab.id
                ? 'bg-[#0077b6] text-white shadow-3d-sm'
                : 'text-[#94a3b8] hover:text-[#f8fafc] hover:bg-[#111d38]'
            }`}
          >
            {tab.icon}
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      {/* Dynamic Active Modality View */}
      <div>
        {selectedModality === 'image' && (
          <ImageScanView onScanCompleted={onScanCompleted} onViewReport={onViewReport} />
        )}
        {selectedModality === 'video' && (
          <VideoScanView onScanCompleted={onScanCompleted} onViewReport={onViewReport} />
        )}
        {selectedModality === 'audio' && (
          <AudioScanView onScanCompleted={onScanCompleted} onViewReport={onViewReport} />
        )}
        {selectedModality === 'phishing' && (
          <PhishingScanView onScanCompleted={onScanCompleted} onViewReport={onViewReport} />
        )}
        {selectedModality === 'scam_message' && (
          <ScamMessageScanView onScanCompleted={onScanCompleted} onViewReport={onViewReport} />
        )}
        {selectedModality === 'fake_review' && (
          <FakeReviewScanView onScanCompleted={onScanCompleted} onViewReport={onViewReport} />
        )}
      </div>
    </div>
  );
};
