import type { ScanRecord } from '../../types';
import { domainDifference, codePoint } from './domainDifference';

const shown=(value:unknown)=>value==null?'Not recorded':typeof value==='object'?JSON.stringify(value):String(value);

/** Recorded expert evidence only. The shared backend contract owns every verdict. */
export function PhishingAnalysis({scan}:{scan:ScanRecord}) {
  const result=scan.result,meta=result?.metadata||{},report=meta.forensics||{};
  const signals=report.network?.signals||{},match=report.visual_domain_match;
  const differences=match?domainDifference(String(match.actual_domain||''),String(match.resembles_domain||'')):[];
  const addresses={'Submitted address':meta.original_input||scan.raw_input,'Actual hostname':report.hostname,'Registered domain':report.registered_domain,'Inspected path':report.path_analysis?.path,'Observed destination':signals.http?.final_url};
  return <div className="phishing-evidence">
    <section><h3>Recorded address evidence</h3><dl className="expert-records">{Object.entries(addresses).filter(([,value])=>value!=null).map(([name,value])=><div key={name}><dt>{name}</dt><dd>{shown(value)}</dd></div>)}</dl></section>
    {match&&<section><h3>Recorded domain comparison</h3><p>{shown(match.method)}</p><p className="break-all">{shown(match.actual_domain)} compared with {shown(match.resembles_domain)}</p>
      <div className="domain-difference" aria-label="Character differences">{differences.map((cell,i)=><span key={i} className={cell.changed?'domain-changed':''} title={`Destination ${cell.actualPosition}: ${codePoint(cell.actual)}; reference ${codePoint(cell.reference)}`}>{cell.actual||'∅'}<small>{cell.reference||'∅'}</small></span>)}</div>
      <p>Highlighted characters differ between these recorded names. This comparison is not proof of ownership or intent.</p></section>}
    {(report.findings||[]).length>0&&<section><h3>Recorded findings</h3><ul>{report.findings.map((finding:{code:string;reason:string},i:number)=><li key={i}>{finding.reason} <code>{finding.code}</code></li>)}</ul></section>}
    <section><h3>Website observations</h3><p>These are recorded checks. A missing check or an absent threat report does not establish safety. Addresses remain plain text.</p>
      {Object.entries(signals).map(([name,value])=><details key={name} className="report-details"><summary>{name}: {shown((value as {status?:string})?.status)}</summary><pre>{JSON.stringify(value,null,2)}</pre></details>)}
    </section>
    <section><h3>Recorded model inputs and readings</h3><dl className="expert-records">{Object.entries({model:result?.model_version,threshold:meta.threshold,score_definition:meta.score_definition,score_components:meta.score_components,diagnostic_model:meta.diagnostic_model,branch_probabilities:meta.branch_probabilities,structural_features:meta.structural_features}).filter(([,value])=>value!=null).map(([name,value])=><div key={name}><dt>{name.replaceAll('_',' ')}</dt><dd>{shown(value)}</dd></div>)}</dl></section>
    {(meta.limitations||[]).length>0&&<section><h3>Model limits</h3><ul>{meta.limitations.map((value:string)=><li key={value}>{value}</li>)}</ul></section>}
  </div>;
}
