import React, { useState } from 'react';
import { Globe, Activity, ArrowRight } from 'lucide-react';
import type { ScanRecord } from '../../types';

interface PhishingScanViewProps {
  onScanCompleted: (scan: ScanRecord) => void;
  onViewReport: (scan: ScanRecord) => void;
}

export const PhishingScanView: React.FC<PhishingScanViewProps> = ({ onScanCompleted, onViewReport }) => {
  const [targetUrl, setTargetUrl] = useState<string>('https://secure-bank-login-update-auth.com/account/verify');
  const [isProcessing, setIsProcessing] = useState<boolean>(false);

  const handleAnalyze = () => {
    if (!targetUrl.trim()) return;
    setIsProcessing(true);

    setTimeout(() => {
      setIsProcessing(false);

      const mockPhishingScan: ScanRecord = {
        id: 'scan-url-' + Math.random().toString(36).substring(2, 9),
        user_id: 'usr-analyst-1',
        status: 'SUCCESS',
        content_type: 'url',
        filename: targetUrl,
        file_size_bytes: 0,
        mime_type: 'text/uri-list',
        created_at: new Date().toISOString(),
        result: {
          scan_id: 'scan-url-' + Math.random().toString(36).substring(2, 9),
          module: 'phishing_url',
          detector_id: 'phishing_url.homoglyph_dns.v1',
          model_version: 'v1.1.0',
          preprocessing_version: 'v1.0.0',
          native_score: 0.04,
          native_score_semantics: 'probability_of_negative_class',
          risk_score: 96,
          confidence: 0.98,
          label: 'fake',
          verdict: 'AI_GENERATED',
          has_face: false,
          status: 'SUCCESS',
          evidence: [
            {
              feature_or_region: 'homoglyph_brand_spoofing',
              contribution: 0.96,
              human_readable_note: 'Cyrillic homoglyph character detected substituting Latin character in domain string.',
            },
            {
              feature_or_region: 'domain_age_risk',
              contribution: 0.88,
              human_readable_note: 'Domain registered < 48 hours ago via anonymized offshore registrar.',
            },
            {
              feature_or_region: 'credential_harvesting_heuristic',
              contribution: 0.92,
              human_readable_note: 'DOM structure matches high-confidence online banking portal clone.',
            },
          ],
          analyzers: [
            { name: 'Homoglyph & Punycode Threat Resolver', category: 'dns', status: 'APPLIED', finding: 'Deceptive script substitution identified in domain authority.' },
            { name: 'Domain Age & Threat Intelligence Feed', category: 'reputation', status: 'APPLIED', finding: 'Domain registered recently with known phishing ASN.' },
            { name: 'DOM Structural Page Clone Matcher', category: 'heuristic', status: 'APPLIED', finding: '98% visual similarity to commercial banking credential form.' },
          ],
          processing_time_ms: 92,
          timestamp: new Date().toISOString(),
        },
        trust_score: {
          scan_id: 'scan-url-mock',
          trust_risk_score: 96,
          risk_level: 'CRITICAL',
          reporting_modules: ['phishing_url'],
          module_scores: { phishing_url: 96 },
          confidence: 0.98,
          contradiction_detected: false,
          evidence: [
            {
              feature_or_region: 'homoglyph_brand_spoofing',
              contribution: 0.96,
              human_readable_note: 'Deceptive fake link detected attempting to impersonate a trusted banking service.',
            },
          ],
          explanation: 'Warning: This link is a dangerous phishing scam. It was recently created to deceive visitors and steal passwords or payment credentials.',
          timestamp: new Date().toISOString(),
        },
      };

      onScanCompleted(mockPhishingScan);
      onViewReport(mockPhishingScan);
    }, 1400);
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-[#111d38] border border-[#1e3a5f] rounded-2xl p-6 shadow-3d-card mb-6">
        <div className="flex items-center justify-between border-b border-[#1e3a5f] pb-4 mb-6">
          <div>
            <h2 className="text-xl font-bold text-[#f8fafc] font-serif">
              Phishing Website &amp; Scam Link Checker
            </h2>
            <p className="text-xs text-[#94a3b8] mt-0.5">
              Paste suspect web addresses to check for fake login pages, brand impersonation, and fraudulent domains.
            </p>
          </div>
          <span className="px-2.5 py-1 rounded-full text-[10px] font-mono font-bold bg-[#0b132b] text-[#00b4d8] border border-[#1e3a5f]">
            Websites &amp; URLs
          </span>
        </div>

        <div className="space-y-4 mb-6">
          <div>
            <label className="block text-xs font-bold text-[#94a3b8] mb-1.5 font-mono uppercase tracking-wider">
              Paste Suspicious Website Link
            </label>
            <div className="flex items-center gap-2 p-2 rounded-xl bg-[#0b132b] border border-[#1e3a5f] focus-within:border-[#00b4d8] transition-all">
              <Globe size={18} className="text-[#64748b] ml-2 shrink-0" />
              <input
                type="url"
                value={targetUrl}
                onChange={(e) => setTargetUrl(e.target.value)}
                placeholder="https://suspect-website-to-check.com"
                className="w-full bg-transparent border-none outline-none text-xs font-mono text-[#f8fafc] font-semibold"
              />
              <button
                onClick={handleAnalyze}
                disabled={!targetUrl.trim() || isProcessing}
                className="px-5 py-2.5 rounded-lg bg-[#0077b6] hover:bg-[#0096c7] text-white text-xs font-bold shrink-0 transition-all cursor-pointer shadow-3d-sm flex items-center gap-1.5"
              >
                <span>{isProcessing ? 'Inspecting...' : 'Scan Website'}</span>
                <ArrowRight size={14} />
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
            <div className="p-3 rounded-lg bg-[#0b132b] border border-[#1e3a5f]">
              <span className="text-[10px] font-mono font-bold text-[#00b4d8] uppercase block mb-1">HOMOGLYPH CHECK</span>
              <span className="text-[#cbd5e1] font-medium">Catches lookalike fake letter spellings</span>
            </div>
            <div className="p-3 rounded-lg bg-[#0b132b] border border-[#1e3a5f]">
              <span className="text-[10px] font-mono font-bold text-[#00b4d8] uppercase block mb-1">DOMAIN AGE REPUTATION</span>
              <span className="text-[#cbd5e1] font-medium">Flags brand-new sites registered days ago</span>
            </div>
            <div className="p-3 rounded-lg bg-[#0b132b] border border-[#1e3a5f]">
              <span className="text-[10px] font-mono font-bold text-[#00b4d8] uppercase block mb-1">PAGE CLONE DETECTION</span>
              <span className="text-[#cbd5e1] font-medium">Spots copied bank or social media login screens</span>
            </div>
          </div>
        </div>

        {isProcessing && (
          <div className="p-4 rounded-xl bg-[#0b132b] border border-[#1e3a5f] text-xs font-mono text-[#00b4d8] flex items-center gap-3">
            <Activity size={18} className="animate-spin text-[#00b4d8]" />
            <span>Resolving authoritative DNS records, SSL/TLS certificate chain, and homoglyph mapping...</span>
          </div>
        )}
      </div>
    </div>
  );
};
