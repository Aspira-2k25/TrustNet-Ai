import { AssessmentNotice } from '../../components/AssessmentNotice';
import React, { useEffect, useRef, useState } from 'react';
import type { ScanRecord } from '../../types';
import { submitPhishing, retrievePhishing } from '../../services/api/phishing.api';

interface Props { onScanCompleted: (scan: ScanRecord) => void; onViewReport: (scan: ScanRecord) => void; }
export const PhishingScanView: React.FC<Props> = ({onScanCompleted, onViewReport}) => {
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
      for (let attempt = 0; attempt < 120; attempt++) {
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
  const result = scan?.result;
  const legacy = !!result && (result.metadata?.assessment_policy!=='dynamic-v2' || result.metadata?.link_analysis_version!=='links-v1');
  const assessed = result && !legacy && ['SUCCESS','PARTIAL_SUCCESS'].includes(result.status);
  return <div className="max-w-4xl mx-auto space-y-5">
    <div className="bg-white border border-[#cbd3d7] rounded-2xl p-6">
      <h2 className="text-xl font-bold text-white">Phishing URL detection</h2>
      <p className="text-sm text-slate-600 mt-2">Enter a domain or link. Bare domains use HTTPS. Other link types receive offline checks without opening apps, scripts or files.</p>
      <div className="flex gap-2 mt-5">
        <input type="text" aria-label="Domain or link" value={url} onChange={e=>setUrl(e.target.value)} placeholder="example.com or paste a link" maxLength={2048} disabled={processing} className="flex-1 min-w-0 bg-white text-white border border-[#cbd3d7] p-3 rounded-lg"/>
        <button onClick={analyze} disabled={processing || !url.trim()} className="bg-[#24695b] disabled:opacity-50 text-white px-4 rounded-lg">{processing?'Scanning...':'Scan URL'}</button>
      </div>
      {processing && <p role="status" className="text-[#24695b] mt-4">Waiting for phishing analysis...</p>}
      {error && <p role="alert" className="text-amber-900 mt-4">{error}</p>}
    </div>
    {scan && <div className="bg-white border border-[#cbd3d7] rounded-2xl p-6 text-slate-700 space-y-3">
      <AssessmentNotice/>
      <p className="text-xs break-all">Scan: {scan.id}</p>
      {assessed && <>
        <p className="text-xl">{result.metadata?.display_verdict || (result.label==='phishing'?'Phishing risk detected':'Low phishing signal')}</p>
        <p>Risk index: {(scan.trust_score?.trust_risk_score ?? result.risk_score).toFixed(1)} / 100  /  {scan.trust_score?.risk_level || 'UNKNOWN'} risk (higher means more risk)</p>
        {(result.metadata?.reasons || []).slice(0,3).map((reason:string)=><p key={reason} className="text-sm text-slate-700">{reason}</p>)}
        <p className="text-xs text-slate-600">{result.metadata?.coverage?.website_fetched?'Live website checks applied.':'URL analysis completed; some live checks were unavailable.'} A low score does not guarantee safety.</p>
      </>}
      {!assessed && result && <div className="space-y-2 text-sm text-amber-900"><p>{legacy?'This saved result uses an earlier detector. Submit a new scan to apply the current model and live checks.':result.explanation || result.error_message || 'No reliable trust score is available.'}</p>{(!legacy && result.metadata?.reasons || []).map((reason:string)=><p key={reason}>{reason}</p>)}</div>}
      {result && <button className="text-[#24695b] underline" onClick={()=>onViewReport(scan)}>View report</button>}
    </div>}
  </div>;
};
