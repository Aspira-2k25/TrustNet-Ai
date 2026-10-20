import { AssessmentNotice } from '../AssessmentNotice';
import type { ScanRecord } from '../../types';
import { jsPDF } from 'jspdf';
import { PhishingAnalysis } from './PhishingAnalysis';
import { domainDifference, reportOpinion, urlReportSummary } from './reportInsights';

export function PhishingReport({scan,onBack}:{scan:ScanRecord;onBack:()=>void}) {
  const result=scan.result, meta=result?.metadata || {}, forensic=meta.forensics;
  const legacy=!!result && (meta.assessment_policy!=='dynamic-v2' || meta.link_analysis_version!=='links-v1');
  const assessed=!!result && !legacy && ['SUCCESS','PARTIAL_SUCCESS'].includes(result.status);
  const score=assessed ? scan.trust_score?.trust_risk_score ?? result.risk_score : null;
  const title=legacy?'Rescan this URL':meta.display_verdict || 'Check incomplete';
  const url=meta.assessed_url || scan.raw_input || '';
  const reasons:string[]=meta.reasons || [result?.explanation || 'No assessment was produced.'];
  const limitations:string[]=meta.limitations || [];
  const signals=forensic?.network?.signals || {};
  const certificate=signals.tls?.analysis;
  const hops=signals.navigation?.hops || [];
  const opinion=reportOpinion(scan);
  const summary=urlReportSummary(scan);
  const domainMatch=forensic?.visual_domain_match;
  const rows=['This tool can make mistakes. Results are indicators, not proof. Verify important decisions independently.',title,`Scan ID: ${scan.id}`,`URL: ${url}`,
    `Risk score: ${summary.risk!==null?`${summary.risk.toFixed(1)} / 100 (higher means more risk)`:'not available'}`,
    `Trust score: ${summary.trust!==null?`${summary.trust.toFixed(1)} / 100 (100 minus risk; higher means less detected risk)`:'not available'}`,
    `Assessment confidence: ${summary.confidence}. ${summary.confidenceReason} Qualitative evidence assessment, not a validated statistical confidence percentage.`,
    'What we found for this URL:',...summary.cards.map(c=>`${c.title}: ${c.text}`),
    `What the model found: ${summary.modelText}`,
    'Findings:',...reasons,
    `Qualitative opinion: ${opinion.title}. ${opinion.reason}`,
    ...(domainMatch?domainDifference(domainMatch.actual_domain,domainMatch.resembles_domain).filter(c=>c.changed).map(c=>`Domain difference at position ${c.actualPosition}: actual '${c.actual || '(absent)'}', reference '${c.reference || '(absent)'}'.`):[]),
    `Threat provider: ${signals.reputation?.provider || 'Unavailable'}; recent exact match: ${signals.reputation?.fresh_match === true?'yes':'not established'}; checked at: ${signals.reputation?.checked_at || 'not recorded'}`,
    ...(signals.reputation?.reports || []).map((r:{id?:number;reported_at?:string;provider_score?:number})=>`Threat report ${r.id}: ${r.reported_at}; provider score ${r.provider_score}`),
    'Recorded forensic findings:',...(forensic?.findings || []).map((f:{code:string;severity:string;reason:string})=>`${f.code} [${f.severity}]: ${f.reason}`),
    `Actual hostname: ${forensic?.hostname || 'Not established'}`,
    `Registered domain: ${forensic?.registered_domain || 'Not established'}`,
    `Inspected path: ${forensic?.path_analysis?.path || 'Not established'}`,
    `Final observed destination: ${signals.http?.final_url || 'Not established'}`,
    `Model ensemble estimate: ${meta.score_components?.model_probability!=null?(Number(meta.score_components.model_probability)*100).toFixed(1)+'%':'Unavailable'}; alert threshold: ${meta.threshold!=null?(Number(meta.threshold)*100).toFixed(1)+'%':'Unavailable'}`,
    ...Object.entries(meta.branch_probabilities || {}).map(([name,value])=>`Diagnostic ${name}: ${(Number(value)*100).toFixed(1)}%`),
    'Exact character-level model attribution is unavailable. Observed features are measurements, not causal explanations.',
    `Combined score formula: ${meta.score_components?.formula || 'Unavailable'}`,
    ...(meta.score_components?.evidence_updates || []).map((u:{code:string;policy_weight:number})=>`Policy update ${u.code}: weight ${u.policy_weight} (not a probability)`),
    ...Object.entries(meta.structural_features || {}).map(([name,value])=>`Observed model input ${name}: ${value}`),
    `Live website inspection: ${meta.coverage?.website_fetched?'applied':'not available'}`,
    ...Object.entries(signals).map(([name,value])=>`${name}: ${(value as {status?:string}).status || 'unknown'}`),
    ...(certificate?[`Certificate issuer: ${certificate.issuer}`,`Signature: ${certificate.signature_hash || certificate.signature_algorithm_oid}; key: ${certificate.public_key_type} ${certificate.public_key_bits || ''}`,`Certificate expires: ${certificate.not_after}`,`Certificate SHA-256: ${certificate.sha256_fingerprint}`,`Revocation: ${certificate.revocation_status}`]:[]),
    ...hops.map((hop:{url:string;status_code:number})=>`Navigation: HTTP ${hop.status_code} ${hop.url}`),
    'Score meaning: This is a risk index, not a probability or a guarantee of website safety.',
    'Limitations:',...limitations,'Recommended action:',...(meta.next_steps || []),
    `Detector: ${result?.detector_id || 'unavailable'} / ${result?.model_version || 'unavailable'}`,
    `Recorded at: ${result?.timestamp || scan.created_at}`];
  const exportPdf=()=>{
    const pdf=new jsPDF();let y=20;
    pdf.setFontSize(16);pdf.text('TrustNet phishing report',15,y);y+=12;pdf.setFontSize(10);
    for(const row of rows) for(const line of pdf.splitTextToSize(row,180) as string[]) {
      if(y>280){pdf.addPage();y=20;}pdf.text(line,15,y);y+=6;
    }
    pdf.save(`phishing-${scan.id}.pdf`);
  };
  const panel='rounded-2xl border border-[#cbd3d7] bg-white p-6 space-y-4';
  return <section className="max-w-5xl mx-auto p-6 space-y-5 text-slate-700">
    <button onClick={onBack} className="text-[#24695b]">Back to history</button>
    <AssessmentNotice/>
    <div className={panel}>
      <h1 className="text-2xl font-bold">{title}</h1>
      {legacy?<p>Submit a new scan to apply the current detector and live checks.</p>:score!==null?
        <div className="space-y-3"><div className="grid sm:grid-cols-2 gap-3">
          <div className="rounded-xl border border-rose-400/30 bg-rose-50 p-4"><p className="text-sm text-rose-800">Risk score</p><p className="text-3xl font-bold mt-2">{summary.risk?.toFixed(1)}<span className="text-sm text-slate-600"> / 100</span></p><div className="h-2 rounded bg-slate-700 mt-3 overflow-hidden"><div className="h-full bg-rose-400" style={{width:`${summary.risk ?? 0}%`}} /></div><p className="text-xs text-slate-600 mt-2">Higher means more detected risk.</p></div>
          <div className="rounded-xl border border-sky-400/30 bg-slate-50 p-4"><p className="text-sm text-[#24695b]">Assessment confidence</p><p className="text-xl font-bold mt-2">{summary.confidence}</p><p className="text-xs text-slate-700 mt-3">{summary.confidenceReason}</p></div>
        </div><p className="text-xs text-slate-600">Risk is a warning index, not a probability or ownership verification. Confidence describes the available evidence qualitatively; a validated confidence percentage is not available.</p></div>:
        <div className="space-y-2"><p className="text-amber-900">{result?.explanation || 'We could not complete this URL check. Please try again.'}</p><p className="text-sm text-slate-600">Risk score: unavailable · Trust score: unavailable · Assessment confidence: {summary.confidence}</p><p className="text-xs text-slate-600">{summary.confidenceReason}</p></div>}
      <p className="break-all rounded-xl bg-white p-3 font-mono text-sm">{url}</p>
      <div className="flex flex-wrap gap-3"><button onClick={exportPdf} className="px-4 py-2 bg-[#24695b] rounded-lg">Export report</button></div>
    </div>
    {!legacy && <PhishingAnalysis scan={scan} />}
    {forensic && <div className={panel}><h2 className="font-bold">Live checks and destination</h2>
      <p className="text-sm break-all">Actual hostname: {forensic.hostname || 'No website hostname in this link'}</p><p className="text-sm">Registered domain: {forensic.registered_domain || 'not established'}</p>
      <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-3">{['dns','tls','http','html','registration','reputation'].map(name=>{
        const state=String(signals[name]?.status || 'not available').toLowerCase();
        return <div key={name} className="rounded-xl border border-[#cbd3d7] p-3 text-sm"><p className="font-semibold">{name==='http'?'Page and redirects':name==='html'?'Page forms':name==='registration'?'Domain registration':name==='reputation'?'Threat reputation':name.toUpperCase()}</p><p className={state==='observed'?'text-emerald-800':'text-slate-600'}>{state==='observed'?'Checked':state==='rate_limited'?'Provider limit reached':'Not available'}</p></div>;
      })}</div>
      <p className="text-xs text-slate-600">Checked does not mean safe. A missing threat-database match is not a clean verdict.</p>
      {forensic.network.domain_age_days!=null && <p className="text-sm">Observed domain age: {forensic.network.domain_age_days} days.</p>}
    </div>}
    {(certificate || hops.length>0 || forensic?.path_analysis?.path) && <div className={panel}>
      <h2 className="font-bold">Certificate and navigation analysis</h2>
      {certificate && <div className="text-sm space-y-1 break-all"><p>{signals.tls?.validated === false?'TLS certificate verification failed.':signals.tls?.validated === true || (signals.tls?.status?.toLowerCase()==='observed' && signals.tls?.certificate)?'TLS certificate chain and hostname verified.':'TLS verification outcome was not recorded.'}</p><p>Issuer: {certificate.issuer}</p><p>Signature: {certificate.signature_hash || certificate.signature_algorithm_oid} · Key: {certificate.public_key_type} {certificate.public_key_bits || ''}</p><p>Expires: {certificate.not_after}</p><p>Revocation: not checked.</p><p className="text-xs text-slate-600">A valid certificate protects the connection; it does not prove the site is legitimate.</p></div>}
      {forensic?.path_analysis?.path && <p className="text-sm break-all">Inspected path: {forensic.path_analysis.path} · {forensic.path_analysis.segments} segments. Redirect parameters are inspected without following them.</p>}
      {hops.map((hop:{url:string;status_code:number},i:number)=><p key={i} className="text-sm break-all">{i+1}. HTTP {hop.status_code} — {hop.url}</p>)}
      <p className="text-xs text-slate-600">Only observed HTTP redirects are followed, with a three-redirect limit and public-address validation at every hop. Page links are not crawled.</p>
    </div>}
    <div className={panel}><h2 className="font-bold">Recommended action</h2>{(meta.next_steps || ['Verify unexpected requests independently before entering credentials.']).map((s:string)=><p key={s} className="text-sm">{s}</p>)}</div>
    <details className={panel}><summary className="cursor-pointer font-bold">Technical details and limitations</summary>
      <p className="text-sm">{meta.score_definition}</p>
      <p className="text-sm">Policy: {meta.assessment_policy || 'legacy'} · Model: {result?.model_version}</p>
      {meta.threshold!=null && <p className="text-sm">Model alert threshold: {(Number(meta.threshold)*100).toFixed(1)}%. {meta.threshold_definition}</p>}
      {Object.entries(meta.branch_probabilities || {}).map(([name,value])=><p key={name} className="text-sm">Diagnostic {name} estimate: {(Number(value)*100).toFixed(1)}%</p>)}
      {(result?.analyzers || []).map((a,i)=><p key={i} className="text-xs">{a.name}: {a.status}. {a.finding || a.reason}</p>)}
      {(result?.evidence || []).map((e,i)=><p key={i} className="text-xs text-slate-600">{e.human_readable_note}</p>)}
      {limitations.map((l:string)=><p key={l} className="text-sm text-slate-600">{l}</p>)}
    </details>
    <p className="text-xs text-slate-600 break-all">Scan: {scan.id} · {result?.processing_time_ms ?? 0} ms · {result?.timestamp || scan.created_at}</p>
  </section>;
}
