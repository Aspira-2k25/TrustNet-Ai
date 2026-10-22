import type { ReactNode } from 'react';
import { CircleHelp, ShieldAlert, ShieldCheck, CircleSlash } from 'lucide-react';
import type { ResultPresentation, ScanRecord } from '../../types';
import { resultView, resultWords, useResultLanguage, notice } from '../../services/resultLanguage.ts';

export function VerdictCard({view,compact=false,showLevels=true}:{view:ResultPresentation;compact?:boolean;showLevels?:boolean}) {
  const {language}=useResultLanguage();
  const warning=['looks_ai','looks_edited','scam','risky'].includes(view.verdict_key);
  const isReal=['no_clear_signs','looks_real'].includes(view.verdict_key);
  const Icon=view.verdict_key==='incomplete'?CircleSlash:warning?ShieldAlert:isReal?ShieldCheck:CircleHelp;
  if(compact)return <span className={`verdict-card verdict-${warning?'warning':isReal?'low':'unsure'}`}><Icon size={22} aria-hidden="true"/><span>{view.headline}</span></span>;
  return <div><header className={`verdict-card verdict-${warning?'warning':isReal?'low':'unsure'}`}><Icon size={30} aria-hidden="true"/><h2>{view.headline}</h2></header>{showLevels&&<dl className="signal-levels">{Object.entries(view.level).map(([name,value])=><div key={name}><dt>{(resultWords[language] as Record<string,string>)[name]||name}</dt><dd>{resultWords[language][value]}</dd></div>)}</dl>}</div>;
}
export function ImageAssessment({view,expert=false}:{view:ResultPresentation;expert?:boolean}) {
  const {t}=useResultLanguage();const a=view.image_assessment;
  if(!a)return null;
  const scoreContent=<>
    <div className="evidence-score"><span>{a.score_label}</span><strong>{a.score===null?t(a.model_readings?.length?'Combined score unavailable':'Score unavailable'):<>{a.score.toFixed(1)}<small> / 100</small></>}</strong></div>
    {a.score!==null&&<meter min={0} max={100} value={a.score} aria-label={a.score_label}/>}

    <p className="score-meaning">{a.score_notice}</p>
    {a.score===null&&!!a.model_readings?.length&&<section className="model-reading-breakdown"><h3>{t("Individual model readings")}</h3><dl>{a.model_readings.map(reading=><div key={reading.evidence_id} data-evidence-id={reading.evidence_id}><dt>{reading.name}</dt><dd><strong>{reading.value.toFixed(2)} / 100</strong><p>{reading.note}</p></dd></div>)}</dl></section>}
  </>;
  if(!expert)return <section className="image-assessment image-assessment-compact" aria-label={t('Image assessment')}>
    {a.file_origin?.signer&&<p className="origin-identity" data-evidence-id={a.file_origin.evidence_id}>{t('Signer')}: <strong>{a.file_origin.signer}</strong>{a.file_origin.trusted&&<span className="origin-verified">{t('Signature verified')}</span>}</p>}
    <p className="model-identity"><span>{t('Model')}</span><strong>{a.model}</strong></p>
  </section>;
  return <section className="image-assessment" aria-label={t('Image assessment')}>
    {a.file_origin&&<section className="file-origin" data-evidence-id={a.file_origin.evidence_id}><h3>{t('File origin check')}</h3><p>{a.file_origin.trusted&&a.file_origin.declares_ai?t('Verified signed record declares AI generation'):a.file_origin.trusted&&a.file_origin.declares_ai_edit?t('Verified AI editing record'):a.file_origin.declares_ai?t('File declares AI generation; signer could not be verified'):a.file_origin.status==='absent'?t('No Content Credential found'):t('No verified AI-generation declaration found')}</p>{a.file_origin.signer&&<p>{t('Signer')}: {a.file_origin.signer}</p>}</section>}
    <p className="model-identity"><span>{t('Model')}</span><strong>{a.model}</strong></p>
    {a.file_origin?.trusted&&a.file_origin.declares_ai?<details className="category-rules"><summary>{t('Pixel model readings')}</summary>{scoreContent}</details>:scoreContent}
    <ol className="assessment-bands" aria-label={t('Image assessment')}>{a.bands.map(b=><li key={b.key} aria-current={a.category===b.key?'step':undefined} data-enabled={b.enabled}><span>{b.label}</span>{!b.enabled&&<small>{t('Validation required')}</small>}</li>)}</ol>
    <details className="category-rules"><summary>{t('Category rules')}</summary>{a.alert_boundary!==null&&<p>{t("Alert boundary")}: {a.alert_boundary.toFixed(1)} / 100</p>}<dl>{a.bands.map(b=><div key={b.key}><dt>{b.label}</dt><dd>{b.rule}</dd></div>)}</dl></details>
  </section>;
}

export function ReasonList({view}:{view:ResultPresentation}) {
  const {language}=useResultLanguage();
  if(!view.reasons.length)return null;
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
export function ResultSummary({scan,children,visual}:{scan:ScanRecord;children?:ReactNode;visual?:ReactNode}) {
  const {language}=useResultLanguage(),view=resultView(scan,language);
  const checks=!!view.checks?.length&&<dl className="check-breakdown">{view.checks.map(check=><div key={check.name} data-state={check.state} data-evidence-id={check.evidence_id}><dt>{check.name}</dt><dd>{check.text}</dd></div>)}</dl>;
  const image=!!view.image_assessment;
  const primaryReasons=image?{...view,reasons:view.reasons.filter(r=>!r.evidence_id.endsWith('/analysis_complete'))}:view;
  return <article className="result-summary"><VerdictCard view={view} showLevels={!image}/><ImageAssessment view={view}/><ReasonList view={primaryReasons}/>{image&&view.checks?.some(c=>c.state==='incomplete')&&<p className="scan-completion-note" role="status">{resultWords[language]['Editing check incomplete']}</p>}<Disclaimer/>{visual}{!image&&checks}<NextSteps view={view}/>{!image&&<LimitsNote view={view}/>}<ExpertDetails view={view}>{image&&<><ImageAssessment view={view} expert/>{checks}<LimitsNote view={view}/></>}{children}</ExpertDetails></article>;
}
