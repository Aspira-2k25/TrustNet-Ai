import type { ScanRecord } from '../../types';
import { exportForensicPDFReport } from '../../services/pdfExporter';
export function ScamResult({scan, onBack}: {scan: ScanRecord; onBack?: () => void}) {
  const result=scan.result; const meta=result?.metadata || {}; const text=meta.assessed_text || scan.raw_input || ''; const characters=Array.from(text);
  const valid=scan.status==='SUCCESS' && result?.status==='SUCCESS';
  const riskLabel=meta.evaluated_domains?.includes('English email') ? 'Message-model fraud estimate (limited coverage)' : `SMS-model smishing estimate${meta.message_type==='email'?' (email calibration unavailable)':''}`;
  const spans: Array<{start:number;end:number;kind:string;contribution:number;direction:string;note:string}>=meta.spans || [];
  const boundaries=[...new Set([0,characters.length,...spans.flatMap(s=>[s.start,s.end])])].filter(i=>i>=0&&i<=characters.length).sort((a,b)=>a-b);
  return <section className="max-w-5xl mx-auto p-6 space-y-6">
    {onBack && <button onClick={onBack} className="text-sky-300">Back to history</button>}
    <div className="rounded-2xl border border-[#1e3a5f] bg-[#0b132b] p-6 space-y-3">
      <h2 className="text-xl font-bold">{valid ? meta.display_verdict || result.verdict?.replaceAll('_',' ') : 'Assessment unavailable'}</h2>
      {valid && <><p className="text-3xl text-sky-300">{result.risk_score.toFixed(1)} / 100 <span className="text-sm">{riskLabel}</span></p>
      <p className="text-sm">{result.explanation}</p><p className="text-xs text-slate-400">Prediction confidence: {(result.confidence*100).toFixed(1)}%. {meta.confidence_definition}</p>
      <div className="flex flex-wrap gap-4 text-sm">{Object.entries(meta.probabilities || {}).map(([name,value])=><span key={name}>{name}: {(Number(value)*100).toFixed(1)}%</span>)}</div></>}
      {meta.assessment_dimensions&&<div className="text-sm space-y-2"><p>Message category: {meta.assessment_dimensions.message_category.value} — {meta.assessment_dimensions.message_category.reason}</p><p>Sender: not verified. {meta.assessment_dimensions.sender_verification.reason}</p><p>AI authorship: not assessed. {meta.assessment_dimensions.ai_authorship.reason}</p></div>}
      {(meta.next_steps || []).map((step:string)=><p key={step} className="text-sm text-slate-300">{step}</p>)}
      {!valid && <p>No successful result is available. This is not a low-risk assessment.</p>}
      <button onClick={()=>exportForensicPDFReport(scan)} className="px-4 py-2 bg-[#0077b6] rounded-lg">Export message report</button>
    </div>
    <div className="rounded-2xl border border-[#1e3a5f] p-6 space-y-4"><h3 className="font-bold">Original message and evidence</h3>
      <div className="flex flex-wrap gap-3 text-xs"><span className="text-red-300">Red: model support</span><span className="text-emerald-300">Green: model counterevidence</span><span className="text-amber-300">Amber underline: context observation</span><span className="text-sky-300">Blue underline: extracted link</span></div>
      <p className="whitespace-pre-wrap break-words leading-8">{boundaries.slice(0,-1).map((start,i)=>{
        const end=boundaries[i+1]; const active=spans.filter(s=>s.start<=start&&s.end>=end);
        const model=active.filter(s=>s.kind==='model').reduce((n,s)=>n+s.contribution,0);
        const cls=(model>0?'bg-red-950 text-red-200 ':model<0?'bg-emerald-950 text-emerald-200 ':'')+(active.some(s=>s.kind==='link')?'underline decoration-sky-400 ':active.some(s=>s.kind==='context')?'underline decoration-amber-400 ':'');
        return <span key={start} className={cls} title={active.map(s=>s.note+(s.kind==='model'?`: ${s.contribution.toFixed(4)} ${meta.attribution_unit || 'logit margin'}`:': observation')).join('; ')}>{characters.slice(start,end).join('')}</span>;
      })}</p><p className="text-xs text-slate-400">{meta.attribution_definition || 'Attribution unavailable'}. Overlapping evidence combines for display. Attribution is partial; read the model-specific definition above.</p>
    </div>
    <div className="grid md:grid-cols-2 gap-5"><div className="border border-[#1e3a5f] rounded-xl p-5"><h3 className="font-bold mb-3">Analysis layers</h3>{result?.analyzers?.map(a=><p key={a.name} className="text-sm mb-3">{a.name}: {a.status}<br/><span className="text-slate-400">{a.finding || a.reason}</span></p>)}</div>
    <div className="border border-[#1e3a5f] rounded-xl p-5"><h3 className="font-bold mb-3">Coverage and limitations</h3>{(meta.limitations || ['No model assessment available']).map((l:string)=><p key={l} className="text-sm mb-2 text-slate-300">{l}</p>)}{meta.coverage && <p className="text-xs">Processed {meta.coverage.characters_processed} characters; truncated: {String(meta.coverage.truncated)}</p>}</div></div>
    {(meta.links || []).length>0 && <div className="border border-[#1e3a5f] rounded-xl p-5"><h3>Embedded links (not opened)</h3>{meta.links.map((l:{url:string;reason:string})=><p key={l.url} className="break-all text-sm mt-3">{l.url}<br/><span className="text-slate-400">{l.reason}</span></p>)}</div>}
    {(meta.sender_link_observations || []).length>0&&<div className="border border-[#1e3a5f] rounded-xl p-5"><h3>Sender and displayed-link observations</h3>{meta.sender_link_observations.map((o:Record<string,unknown>,i:number)=><p className="break-all text-sm mt-3" key={i}>{Object.entries(o).filter(([,v])=>v!==null).map(([k,v])=>`${k}: ${String(v)}`).join(' · ')}</p>)}</div>}
    {meta.optional_explanation&&<div className="text-sm"><h3>Optional evidence summary: {meta.optional_explanation.status}</h3><p>{meta.optional_explanation.reason || meta.optional_explanation.method}</p>{(meta.optional_explanation.evidence || []).map((e:{id:number;note:string})=><p key={e.id}>{e.note}</p>)}</div>}
    <p className="text-xs text-slate-400">Model: {result?.detector_id} / {result?.model_version}. {meta.span_offset_unit}</p>
  </section>;
}
