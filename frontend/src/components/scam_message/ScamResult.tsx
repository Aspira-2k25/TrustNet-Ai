import { useResultLanguage } from '../../services/resultLanguage.ts';
import { ResultSummary } from '../results/ResultSummary';
import type { ScanRecord } from '../../types';
import { exportForensicPDFReport } from '../../services/pdfExporter';
import { useEffect, useState } from 'react';
import { LinkInspection, type SavedInspection } from './LinkInspection';
export function ScamResult({scan: initialScan, onBack}: {scan: ScanRecord; onBack?: () => void}) {
  const {t}=useResultLanguage();
  const [scan, setScan] = useState(initialScan);
  useEffect(() => setScan(initialScan), [initialScan]);
  const result=scan.result; const meta=result?.metadata || {}; const text=meta.assessed_text || scan.raw_input || ''; const characters=Array.from(text);
  const spans: Array<{start:number;end:number;kind:string;contribution:number;direction:string;note:string}>=meta.spans || [];
  const boundaries=[...new Set([0,characters.length,...spans.flatMap(s=>[s.start,s.end])])].filter(i=>i>=0&&i<=characters.length).sort((a,b)=>a-b);
  return <section className="max-w-5xl mx-auto p-6 space-y-6">
    {onBack && <button onClick={onBack} className="text-[#24695b]">{t("Back to history")}</button>}
    <ResultSummary scan={scan}><><p>{t("Technical records below are kept in English.")}</p>
    <div className="rounded-2xl border border-[#cbd3d7] p-6 space-y-4"><h3 className="font-bold">Original message and evidence</h3>
      <div className="flex flex-wrap gap-3 text-xs"><span className="text-red-800">Red: model support</span><span className="text-emerald-800">Green: model counterevidence</span><span className="text-amber-900">Amber underline: observed pattern or explicit rule</span><span className="text-[#24695b]">Underlined link: extracted address</span></div>
      <p className="whitespace-pre-wrap break-words leading-8">{boundaries.slice(0,-1).map((start,i)=>{
        const end=boundaries[i+1]; const active=spans.filter(s=>s.start<=start&&s.end>=end);
        const model=active.filter(s=>s.kind==='model').reduce((n,s)=>n+s.contribution,0);
        const cls=(model>=0.015?'bg-red-50 text-red-800 ':model<=-0.015?'bg-emerald-50 text-emerald-800 ':'')+(active.some(s=>s.kind==='link')?'underline decoration-sky-400 ':active.some(s=>['context','rule'].includes(s.kind))?'underline decoration-amber-400 ':'');
        return <span key={start} className={cls} title={active.map(s=>s.note+(s.kind==='model'?`: ${s.contribution.toFixed(4)} ${meta.attribution_unit || 'logit margin'}`:': observation')).join('; ')}>{characters.slice(start,end).join('')}</span>;
      })}</p><p className="text-xs text-slate-600">{meta.attribution_definition || 'Attribution unavailable'}. Overlapping evidence combines for display. Attribution is partial; read the model-specific definition above.</p>
    </div>
    <div className="grid md:grid-cols-2 gap-5"><div className="border border-[#cbd3d7] rounded-xl p-5"><h3 className="font-bold mb-3">Analysis layers</h3>{result?.analyzers?.map(a=><p key={a.name} className="text-sm mb-3">{a.name}: {a.status}<br/><span className="text-slate-600">{a.finding || a.reason}</span></p>)}</div>
    <div className="border border-[#cbd3d7] rounded-xl p-5"><h3 className="font-bold mb-3">Coverage and limitations</h3>{(meta.limitations || ['No model assessment available']).map((l:string)=><p key={l} className="text-sm mb-2 text-slate-700">{l}</p>)}{typeof meta.coverage?.characters_processed==='number' && <p className="text-xs">Processed {meta.coverage.characters_processed} characters; truncated: {String(meta.coverage.truncated)}</p>}</div></div>
    {meta.fusion?.links_found>0 && <div className="border border-[#cbd3d7] rounded-xl p-5 space-y-3"><h3 className="font-bold">Message and URL assessment</h3><p>Message warning index: {Number(meta.fusion.message_score).toFixed(1)}/100. Highest URL risk: {meta.fusion.url_score==null?'Unavailable':`${Number(meta.fusion.url_score).toFixed(1)}/100`}.</p><p className="text-sm text-slate-600">{meta.fusion.definition} Checked {meta.fusion.links_assessed} of {meta.fusion.links_found} links. Websites were not opened.</p></div>}
    {(meta.links || []).length>0 && <div className="border border-[#cbd3d7] rounded-xl p-5"><h3>Embedded link analysis</h3>{meta.links.map((l:{url:string;reason:string;status?:string;risk_score?:number;verdict?:string;inspection?:SavedInspection}, index:number)=><div key={l.url} className="break-words text-sm mt-5"><p className="break-all">{l.url}</p><p>{l.status}{l.risk_score!=null?` — ${l.risk_score.toFixed(1)}/100`:''}{l.verdict?` — ${l.verdict.replaceAll('_',' ')}`:''}</p><p className="text-slate-600">Quick assessment: {l.reason}</p>{index<8 && /^(?:https?:\/\/|www\.)/i.test(l.url) && <LinkInspection scanId={scan.id} index={index} saved={l.inspection} onUpdated={setScan}/>}</div>)}</div>}
    {(meta.sender_link_observations || []).length>0&&<div className="border border-[#cbd3d7] rounded-xl p-5"><h3>Sender and displayed-link observations</h3>{meta.sender_link_observations.map((o:Record<string,unknown>,i:number)=><p className="break-all text-sm mt-3" key={i}>{Object.entries(o).filter(([,v])=>v!==null).map(([k,v])=>`${k}: ${String(v)}`).join(' · ')}</p>)}</div>}
    {meta.optional_explanation&&<div className="text-sm"><h3>Optional evidence summary: {meta.optional_explanation.status}</h3><p>{meta.optional_explanation.reason || meta.optional_explanation.method}</p>{(meta.optional_explanation.evidence || []).map((e:{id:number;note:string})=><p key={e.id}>{e.note}</p>)}</div>}
    <p className="text-xs text-slate-600">Model: {result?.detector_id} / {result?.model_version}. {meta.span_offset_unit}</p>
</></ResultSummary>
    <button onClick={()=>exportForensicPDFReport(scan)} className="primary-button">{t("Download report")}</button>
    {meta.fusion?.links_found>0&&<p>{t("Message and links were checked together. Open the link checks below to see which links could not be checked.")}</p>}


  </section>;
}
