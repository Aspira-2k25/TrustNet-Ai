import type { ScanRecord } from '../../types';
import { jsPDF } from 'jspdf';
import { TrustScoreGauge } from '../TrustScoreGauge';

export function PhishingReport({scan,onBack}:{scan:ScanRecord;onBack:()=>void}) {
  const result=scan.result, meta=result?.metadata || {}, forensic=meta.forensics;
  const legacy=!!result && (meta.assessment_policy!=='dynamic-v2' || meta.link_analysis_version!=='links-v1');
  const assessed=!!result && !legacy && ['SUCCESS','PARTIAL_SUCCESS'].includes(result.status);
  const score=assessed ? scan.trust_score?.trust_risk_score ?? result.risk_score : null;
  const level=scan.trust_score?.risk_level || 'UNKNOWN';
  const title=legacy?'Rescan this URL':meta.display_verdict || 'Check incomplete';
  const url=meta.assessed_url || scan.raw_input || '';
  const reasons:string[]=meta.reasons || [result?.explanation || 'No assessment was produced.'];
  const limitations:string[]=meta.limitations || [];
  const signals=forensic?.network?.signals || {};
  const certificate=signals.tls?.analysis;
  const hops=signals.navigation?.hops || [];
  const rows=[title,`Scan ID: ${scan.id}`,`URL: ${url}`,
    `Trust score: ${score!==null?`${score.toFixed(1)} / 100 (${level} risk; higher means more risk)`:'not available'}`,
    'Findings:',...reasons,
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
  const panel='rounded-2xl border border-[#1e3a5f] bg-[#0b132b] p-6 space-y-4';
  return <section className="max-w-5xl mx-auto p-6 space-y-5 text-slate-200">
    <button onClick={onBack} className="text-sky-300">Back to history</button>
    <div className={panel}>
      <h1 className="text-2xl font-bold">{title}</h1>
      {legacy?<p>Submit a new scan to apply the current detector and live checks.</p>:score!==null?
        <div className="flex flex-wrap items-center gap-6"><TrustScoreGauge score={Math.round(score)} riskLevel={level} label="Trust score" size={160}/>
          <div><p className="text-xl font-bold">{score.toFixed(1)} / 100 · {level} risk</p><p className="text-sm text-slate-400">Higher means more phishing risk.</p><p className="text-xs text-slate-400 mt-2">Risk index, not a probability or safety guarantee.</p></div></div>:
        <p className="text-amber-200">{result?.explanation || 'We could not complete this URL check. Please try again.'}</p>}
      {!legacy && <div className="space-y-2"><h2 className="font-bold">Why this result?</h2>{reasons.map((reason:string,i:number)=><p key={i} className="text-sm">{reason}</p>)}</div>}
      <p className="break-all rounded-xl bg-[#111d38] p-3 font-mono text-sm">{url}</p>
      <div className="flex flex-wrap gap-3"><button onClick={exportPdf} className="px-4 py-2 bg-[#0077b6] rounded-lg">Export report</button></div>
    </div>
    {forensic && <div className={panel}><h2 className="font-bold">Live checks and destination</h2>
      <p className="text-sm break-all">Actual hostname: {forensic.hostname || 'No website hostname in this link'}</p><p className="text-sm">Registered domain: {forensic.registered_domain || 'not established'}</p>
      <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-3">{['dns','tls','http','html','registration','reputation'].map(name=>{
        const state=String(signals[name]?.status || 'not available').toLowerCase();
        return <div key={name} className="rounded-xl border border-[#1e3a5f] p-3 text-sm"><p className="font-semibold">{name==='http'?'Page and redirects':name==='html'?'Page forms':name==='registration'?'Domain registration':name==='reputation'?'Threat reputation':name.toUpperCase()}</p><p className={state==='observed'?'text-emerald-300':'text-slate-400'}>{state==='observed'?'Checked':state==='rate_limited'?'Provider limit reached':'Not available'}</p></div>;
      })}</div>
      <p className="text-xs text-slate-400">Checked does not mean safe. A missing threat-database match is not a clean verdict.</p>
      {forensic.network.domain_age_days!=null && <p className="text-sm">Observed domain age: {forensic.network.domain_age_days} days.</p>}
    </div>}
    {(certificate || hops.length>0 || forensic?.path_analysis?.path) && <div className={panel}>
      <h2 className="font-bold">Certificate and navigation analysis</h2>
      {certificate && <div className="text-sm space-y-1 break-all"><p>TLS certificate chain and hostname verified.</p><p>Issuer: {certificate.issuer}</p><p>Signature: {certificate.signature_hash || certificate.signature_algorithm_oid} · Key: {certificate.public_key_type} {certificate.public_key_bits || ''}</p><p>Expires: {certificate.not_after}</p><p>Revocation: not checked.</p><p className="text-xs text-slate-400">A valid certificate protects the connection; it does not prove the site is legitimate.</p></div>}
      {forensic?.path_analysis?.path && <p className="text-sm break-all">Inspected path: {forensic.path_analysis.path} · {forensic.path_analysis.segments} segments. Redirect parameters are inspected without following them.</p>}
      {hops.map((hop:{url:string;status_code:number},i:number)=><p key={i} className="text-sm break-all">{i+1}. HTTP {hop.status_code} — {hop.url}</p>)}
      <p className="text-xs text-slate-400">Only observed HTTP redirects are followed, with a three-redirect limit and public-address validation at every hop. Page links are not crawled.</p>
    </div>}
    <div className={panel}><h2 className="font-bold">Recommended action</h2>{(meta.next_steps || ['Verify unexpected requests independently before entering credentials.']).map((s:string)=><p key={s} className="text-sm">{s}</p>)}</div>
    <details className={panel}><summary className="cursor-pointer font-bold">Technical details and limitations</summary>
      <p className="text-sm">{meta.score_definition}</p>
      <p className="text-sm">Policy: {meta.assessment_policy || 'legacy'} · Model: {result?.model_version}</p>
      {meta.threshold!=null && <p className="text-sm">Model alert threshold: {(Number(meta.threshold)*100).toFixed(1)}%. {meta.threshold_definition}</p>}
      {Object.entries(meta.branch_probabilities || {}).map(([name,value])=><p key={name} className="text-sm">Diagnostic {name} estimate: {(Number(value)*100).toFixed(1)}%</p>)}
      {(result?.analyzers || []).map((a,i)=><p key={i} className="text-xs">{a.name}: {a.status}. {a.finding || a.reason}</p>)}
      {(result?.evidence || []).map((e,i)=><p key={i} className="text-xs text-slate-400">{e.human_readable_note}</p>)}
      {limitations.map((l:string)=><p key={l} className="text-sm text-slate-400">{l}</p>)}
    </details>
    <p className="text-xs text-slate-400 break-all">Scan: {scan.id} · {result?.processing_time_ms ?? 0} ms · {result?.timestamp || scan.created_at}</p>
  </section>;
}
