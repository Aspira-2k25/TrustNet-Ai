import { useResultLanguage } from '../../services/resultLanguage.ts';
import { ResultSummary } from '../../components/results/ResultSummary';
import React, { useEffect, useRef, useState } from 'react';
import { Globe, Clock, Lock, Unlock, ShieldAlert } from 'lucide-react';
import type { ScanRecord } from '../../types';
import { submitPhishing, retrievePhishing } from '../../services/api/phishing.api';

interface Props { onScanCompleted: (scan: ScanRecord) => void; onViewReport: (scan: ScanRecord) => void; }
export const PhishingScanView: React.FC<Props> = ({onScanCompleted, onViewReport}) => {
  const {t}=useResultLanguage();
  const [url, setUrl] = useState('');
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState('');
  const [scan, setScan] = useState<ScanRecord | null>(null);
  const active = useRef<AbortController | null>(null);
  useEffect(() => () => active.current?.abort(), []);
  const analyze = async () => {
    if (processing) return;
    const target = url.trim();
    // eslint-disable-next-line no-control-regex -- Reject control bytes in URL input.
    if (!target || target.length>2048 || /[\s\\\x00-\x1f\x7f]/.test(target)) { setError('Enter a domain or link without spaces (up to 2048 characters).'); return; }
    const controller = new AbortController(); active.current?.abort(); active.current = controller;
    setProcessing(true); setError(''); setScan(null);
    try {
      const accepted = await submitPhishing(target, controller.signal); setScan(accepted);
      for (let attempt = 0; attempt < 20; attempt++) {
        const current = await retrievePhishing(accepted.id, controller.signal); setScan(current);
        if (!['QUEUED', 'PROCESSING', 'PENDING'].includes(current.status)) {
          if (current.result?.module !== 'phishing' || current.result.scan_id !== current.id) throw new Error('Phishing result missing or mismatched.');
          onScanCompleted(current);
          if (['FAILED','TIMEOUT'].includes(current.status)) setError(current.result.error_message || 'Phishing assessment unavailable.');
          return;
        }
        await new Promise<void>((resolve, reject) => {
          const cancel = () => { window.clearTimeout(timer); reject(new DOMException('Aborted','AbortError')); };
          const timer = window.setTimeout(() => { controller.signal.removeEventListener('abort',cancel); resolve(); },1500);
          controller.signal.addEventListener('abort',cancel,{once:true});
        });
      }
      setError('Scan still processing. Check scan history later.');
    } catch (reason) { if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'Unable to scan URL.'); }
    finally { if (!controller.signal.aborted) setProcessing(false); }
  };
  return <div className="max-w-4xl mx-auto space-y-5">
    <div className="bg-white border border-[#cbd3d7] rounded-2xl p-6">
      <h2 className="text-xl font-bold text-[#252a27]">Phishing URL detection</h2>
      <p className="text-sm text-slate-600 mt-2">Enter a domain or link. Bare domains use HTTPS. Other link types receive offline checks without opening apps, scripts or files.</p>
      <div className="flex gap-2 mt-5">
        <input type="text" aria-label="Domain or link" value={url} onChange={e=>setUrl(e.target.value)} placeholder="example.com or paste a link" maxLength={2048} disabled={processing} className="flex-1 min-w-0 bg-white text-[#252a27] border border-[#cbd3d7] p-3 rounded-lg"/>
        <button onClick={analyze} disabled={processing || !url.trim()} className="bg-[#24695b] disabled:opacity-50 text-white px-4 rounded-lg">{processing?'Scanning...':'Scan URL'}</button>
      </div>
      {processing && <p role="status" className="text-[#24695b] mt-4">Waiting for phishing analysis...</p>}
      {error && <p role="alert" className="text-amber-900 mt-4">{error}</p>}
    </div>
    {scan && <div className="bg-white border border-[#cbd3d7] rounded-2xl p-6 text-slate-700 space-y-4">
      {(() => {
        const intel = (scan.result?.metadata?.domain_intel || {}) as {
          domain?: string;
          domain_age_days?: number | null;
          registration_date?: string | null;
          ssl_status?: string;
          ssl_issuer?: string;
          has_password_form?: boolean;
          final_url?: string;
        };
        const domain = intel.domain || (scan.result?.metadata?.features?.domain as string) || scan.raw_input;
        const isNew = typeof intel.domain_age_days === 'number' && intel.domain_age_days < 30;
        const sslVerified = intel.ssl_status === 'SECURE_HTTPS';
        const sslInvalid = intel.ssl_status === 'INVALID_OR_MISSING';
        const hasAge = typeof intel.domain_age_days === 'number';
        const hasRegDate = Boolean(intel.registration_date);

        return <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-200 pb-2.5">
            <div className="flex items-center gap-2 text-slate-900 font-semibold">
              <Globe size={18} className="text-[#24695b]" />
              <span>Domain &amp; Security Intelligence</span>
            </div>
            {isNew && <span className="bg-amber-100 text-amber-900 text-xs font-bold px-2.5 py-0.5 rounded-full border border-amber-300">
              ⚠️ Newly Registered Domain
            </span>}
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 text-sm">
            <div className="bg-white p-3 rounded-lg border border-slate-200">
              <span className="text-xs text-slate-500 block mb-0.5">Domain Name</span>
              <span className="font-mono font-medium text-slate-800 break-all">{domain || 'Unknown'}</span>
            </div>
            <div className="bg-white p-3 rounded-lg border border-slate-200">
              <span className="text-xs text-slate-500 block mb-0.5">Domain Age / Registration</span>
              <div className="flex items-center gap-1.5 font-medium">
                <Clock size={15} className={isNew ? "text-amber-600" : hasAge ? "text-emerald-600" : "text-slate-400"} />
                <span className={isNew ? "text-amber-800 font-semibold" : hasAge || hasRegDate ? "text-slate-800" : "text-slate-500 italic"}>
                  {hasAge
                    ? intel.domain_age_days! < 30
                      ? `${intel.domain_age_days} days old (Brand New!)`
                      : intel.domain_age_days! < 365
                      ? `${Math.floor(intel.domain_age_days! / 30)} months old (${intel.domain_age_days}d)`
                      : `${(intel.domain_age_days! / 365).toFixed(1)} years old`
                    : hasRegDate
                    ? `Registered: ${intel.registration_date!.slice(0, 10)}`
                    : 'Registration data unavailable'}
                </span>
              </div>
            </div>
            <div className="bg-white p-3 rounded-lg border border-slate-200">
              <span className="text-xs text-slate-500 block mb-0.5">SSL / Encryption Security</span>
              <div className="flex items-center gap-1.5 font-medium">
                {sslVerified ? <Lock size={15} className="text-emerald-600" /> : sslInvalid ? <Unlock size={15} className="text-amber-600" /> : <Globe size={15} className="text-slate-400" />}
                <span className={sslVerified ? "text-emerald-700 font-medium" : sslInvalid ? "text-amber-800 font-medium" : "text-slate-500 italic"}>
                  {sslVerified
                    ? `Encrypted HTTPS (${intel.ssl_issuer || 'Verified TLS'})`
                    : sslInvalid
                    ? 'No SSL / Unencrypted or Invalid Certificate'
                    : 'Live TLS check unavailable'}
                </span>
              </div>
            </div>
          </div>
          {intel.has_password_form && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-2.5 text-xs text-amber-900 flex items-center gap-2">
              <ShieldAlert size={16} className="text-amber-700 shrink-0" />
              <span><strong>Warning:</strong> This page contains password or credential entry fields. Never enter banking or private credentials on unfamiliar domains.</span>
            </div>
          )}
        </div>;
      })()}
      <ResultSummary scan={scan}/>
      {scan.result && <button className="text-[#24695b] underline" onClick={()=>onViewReport(scan)}>{t("View full report")}</button>}
    </div>}
  </div>;
};
