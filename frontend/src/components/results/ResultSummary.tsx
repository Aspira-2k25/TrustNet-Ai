import type { ReactNode } from 'react';
import { CircleHelp, ShieldAlert, ShieldCheck, CircleSlash } from 'lucide-react';
import type { ResultPresentation, ScanRecord } from '../../types';
import { resultView, resultWords, useResultLanguage, notice } from '../../services/resultLanguage.ts';

export function VerdictCard({view,compact=false}:{view:ResultPresentation;compact?:boolean}) {
  const {language}=useResultLanguage();
  const warning=['looks_ai','looks_edited','scam','risky'].includes(view.verdict_key);
  const Icon=view.verdict_key==='incomplete'?CircleSlash:warning?ShieldAlert:view.verdict_key==='no_clear_signs'?ShieldCheck:CircleHelp;
  if(compact)return <span className={`verdict-card verdict-${warning?'warning':view.verdict_key==='no_clear_signs'?'low':'unsure'}`}><Icon size={22} aria-hidden="true"/><span>{view.headline}</span></span>;
  return <div><header className={`verdict-card verdict-${warning?'warning':view.verdict_key==='no_clear_signs'?'low':'unsure'}`}><Icon size={30} aria-hidden="true"/><h2>{view.headline}</h2></header><dl className="signal-levels">{Object.entries(view.level).map(([name,value])=><div key={name}><dt>{(resultWords[language] as Record<string,string>)[name]||name}</dt><dd>{resultWords[language][value]}</dd></div>)}</dl></div>;
}
export function ReasonList({view}:{view:ResultPresentation}) {
  const {language}=useResultLanguage();
  return <section><h3>{resultWords[language].why}</h3><ul>{view.reasons.map((r,i)=><li key={r.evidence_id+':'+i} data-evidence-id={r.evidence_id}>{r.text}</li>)}</ul></section>;
}
export function NextSteps({view}:{view:ResultPresentation}) {
  const {language}=useResultLanguage();
  return view.next_steps.length>0&&<section><h3>{resultWords[language].next}</h3><ul>{view.next_steps.map(s=><li key={s}>{s}</li>)}</ul></section>;
}
export function LimitsNote({view}:{view:ResultPresentation}) {
  const {language}=useResultLanguage();
  return view.limits.length>0&&<section className="result-limits"><h3>{resultWords[language].limits}</h3><ul>{view.limits.map(s=><li key={s}>{s}</li>)}</ul></section>;
}
export function ExpertDetails({view,children}:{view:ResultPresentation;children?:ReactNode}) {
  const {language}=useResultLanguage();
  return <details className="report-details"><summary>{resultWords[language].experts}</summary><dl className="expert-records">{Object.entries(view.details).map(([key,value])=><div key={key}><dt>{key.replaceAll('_',' ')}</dt><dd>{typeof value==='object'?JSON.stringify(value):String(value)}</dd></div>)}</dl>{children}</details>;
}
export function Disclaimer(){const {language}=useResultLanguage();return <p className="assessment-notice">{notice(language)}</p>;}
export function ResultSummary({scan,children}:{scan:ScanRecord;children?:ReactNode}) {
  const {language}=useResultLanguage(),view=resultView(scan,language);
  return <article className="result-summary"><VerdictCard view={view}/><ReasonList view={view}/><NextSteps view={view}/><LimitsNote view={view}/><ExpertDetails view={view}>{children}</ExpertDetails><Disclaimer/></article>;
}
