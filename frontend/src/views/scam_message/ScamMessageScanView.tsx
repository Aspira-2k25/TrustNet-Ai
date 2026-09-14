import React, { useState } from 'react';
import { ArrowRight } from 'lucide-react';
import type { ScanRecord } from '../../types';

interface ScamMessageScanViewProps {
  onScanCompleted: (scan: ScanRecord) => void;
  onViewReport: (scan: ScanRecord) => void;
}

export const ScamMessageScanView: React.FC<ScamMessageScanViewProps> = ({ onScanCompleted, onViewReport }) => {
  const [messageText, setMessageText] = useState<string>(
    "URGENT: Your bank account will be blocked within 2 hours due to unverified KYC. Click here immediately to update: http://bit.ly/bank-secure-auth or call our agent."
  );
  const [isProcessing, setIsProcessing] = useState<boolean>(false);

  const handleAnalyze = () => {
    if (!messageText.trim()) return;
    setIsProcessing(true);

    setTimeout(() => {
      setIsProcessing(false);

      const mockScamScan: ScanRecord = {
        id: 'scan-scam-' + Math.random().toString(36).substring(2, 9),
        user_id: 'usr-analyst-1',
        status: 'SUCCESS',
        content_type: 'text',
        filename: 'suspicious_sms_message.txt',
        file_size_bytes: messageText.length,
        mime_type: 'text/plain',
        created_at: new Date().toISOString(),
        result: {
          scan_id: 'scan-scam-sample',
          module: 'scam_message',
          detector_id: 'scam_message.nlp.v1',
          model_version: 'v1.0.0',
          preprocessing_version: 'v1.0.0',
          native_score: 0.08,
          native_score_semantics: 'probability_of_negative_class',
          risk_score: 92,
          confidence: 0.96,
          label: 'fake',
          verdict: 'AI_GENERATED',
          has_face: false,
          status: 'SUCCESS',
          evidence: [
            {
              feature_or_region: 'artificial_urgency_panic',
              contribution: 0.94,
              human_readable_note: 'High-pressure countdown tactics and threats of account suspension.',
            },
            {
              feature_or_region: 'malicious_shortener_link',
              contribution: 0.91,
              human_readable_note: 'Shortened redirect URL masking untrusted external destination.',
            },
          ],
          analyzers: [
            { name: 'Scam Semantic & Urgency Detector', category: 'intent', status: 'APPLIED', finding: 'High probability of social engineering fraud and credential theft.' },
          ],
          processing_time_ms: 76,
          timestamp: new Date().toISOString(),
        },
        trust_score: {
          scan_id: 'scan-scam-sample',
          trust_risk_score: 92,
          risk_level: 'CRITICAL',
          reporting_modules: ['scam_message'],
          module_scores: { scam_message: 92 },
          confidence: 0.96,
          contradiction_detected: false,
          evidence: [
            {
              feature_or_region: 'artificial_urgency_panic',
              contribution: 0.94,
              human_readable_note: 'Artificial panic tactics detected threatening immediate account suspension.',
            },
          ],
          explanation: 'Warning: This message is a fraudulent scam. It uses fake urgency and suspicious shortened links to trick you into revealing personal information.',
          timestamp: new Date().toISOString(),
        },
      };

      onScanCompleted(mockScamScan);
      onViewReport(mockScamScan);
    }, 1200);
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-[#111d38] border border-[#1e3a5f] rounded-2xl p-6 shadow-3d-card mb-6">
        <div className="flex items-center justify-between border-b border-[#1e3a5f] pb-4 mb-6">
          <div>
            <h2 className="text-xl font-bold text-[#f8fafc] font-serif">
              Scam Message &amp; Fraud Text Detector
            </h2>
            <p className="text-xs text-[#94a3b8] mt-0.5">
              Paste suspicious SMS, WhatsApp messages, lottery texts, or urgent emails to see if they are fraud attempts.
            </p>
          </div>
          <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-amber-950/70 text-amber-300 border border-amber-800">
            SMS &amp; Text Messages
          </span>
        </div>

        <div className="space-y-4 mb-6">
          <div>
            <label className="block text-xs font-bold text-[#94a3b8] mb-1.5">
              Paste Suspicious Message Text
            </label>
            <textarea
              rows={4}
              value={messageText}
              onChange={(e) => setMessageText(e.target.value)}
              placeholder="Paste the SMS, WhatsApp message, or email you received..."
              className="w-full p-3.5 rounded-xl bg-[#0b132b] border border-[#1e3a5f] text-xs text-[#f8fafc] outline-none focus:border-[#00b4d8] transition-all"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            <div className="p-3 rounded-lg bg-[#0b132b] border border-[#1e3a5f]">
              <span className="text-[11px] font-bold text-amber-400 block mb-1">Checks Fake Urgency</span>
              <span className="text-[#94a3b8]">Catches fake bank alerts, threats of account block, and lottery scams.</span>
            </div>
            <div className="p-3 rounded-lg bg-[#0b132b] border border-[#1e3a5f]">
              <span className="text-[11px] font-bold text-[#00b4d8] block mb-1">Clear Advice</span>
              <span className="text-[#94a3b8]">Tells you immediately whether to ignore, delete, or report the message.</span>
            </div>
          </div>
        </div>

        {isProcessing && (
          <div className="mb-6 p-3.5 rounded-xl bg-[#0b132b] border border-amber-800 text-xs text-amber-300 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping" />
            <span>Scanning message for fraud tactics, urgent keywords, and phishing links...</span>
          </div>
        )}

        <div className="flex items-center justify-end pt-4 border-t border-[#1e3a5f]">
          <button
            onClick={handleAnalyze}
            disabled={!messageText.trim() || isProcessing}
            className={`px-6 py-2.5 rounded-xl font-bold text-xs flex items-center gap-2 transition-all cursor-pointer ${
              !messageText.trim() || isProcessing
                ? 'bg-[#1c2541] text-[#64748b] border border-[#1e3a5f] cursor-not-allowed'
                : 'bg-[#0077b6] hover:bg-[#0096c7] text-white shadow-3d-sm'
            }`}
          >
            <span>{isProcessing ? 'Checking Message...' : 'Check If Message Is a Scam'}</span>
            <ArrowRight size={14} />
          </button>
        </div>
      </div>
    </div>
  );
};
