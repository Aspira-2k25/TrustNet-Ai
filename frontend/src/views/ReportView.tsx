import { useEffect, useState } from 'react';
import { CircleHelp, ShieldAlert, ShieldCheck } from 'lucide-react';
import type { ScanRecord } from '../types';
import { API_BASE_URL, httpClient } from '../services/api/client';
import { ScamResult } from '../components/scam_message/ScamResult';
import { AssessmentNotice } from '../components/AssessmentNotice';
import { exportForensicPDFReport } from '../services/pdfExporter';
import { useResultLanguage, simpleResult, level, imageAiLevel } from '../services/resultLanguage.ts';

type Layer = 'original' | 'overlay' | 'heatmap' | 'mask' | 'ela' | 'attention';
const percent=(value:unknown)=>typeof value==='number'&&Number.isFinite(value)?`${(value*100).toFixed(1)}%`:'Unavailable';

export function ReportView({scan,onBack}:{scan:ScanRecord;onBack:()=>void}) {
  const {language,t}=useResultLanguage();
  const plain=simpleResult(scan,language);
  const [layer,setLayer]=useState<Layer>('original');
  const [zoom,setZoom]=useState(1);
  const [source,setSource]=useState('');
  const [imageError,setImageError]=useState('');
  const [originalSource,setOriginalSource]=useState('');
  const [comparison,setComparison]=useState(50);
  const result=scan.result;
  const meta=result?.metadata||{};
  const current=result?.detector_id==='image_deepfake.evidence.v2';
  const image=meta.image_analysis||{};
  const supporting=image.supporting_forensics;
  const provenance=image.provenance||{};
  const limits:string[]=image.quality?.limits||[];
  const reasons:string[]=image.reasons||[current?result?.explanation||'Evidence unavailable.':'This historical report used the previous detector. Run a new assessment for separate AI and localization evidence.'];
  const verdict=current?result?.verdict||'INCONCLUSIVE':'INCONCLUSIVE';
  const VerdictIcon=verdict==='INCONCLUSIVE'?CircleHelp:verdict==='LIKELY_AUTHENTIC'?ShieldCheck:ShieldAlert;
  const paths=image.assets||{};
  const hasRegions=Array.isArray(image.regions)&&image.regions.length>0;
  const layerPath=layer==='original'?image.original_url:paths[layer];
  useEffect(()=>{
    if(layer!=='overlay'||!hasRegions)return;
    const target=image.original_url;
    if(typeof target!=='string'||!target.startsWith(`/api/v1/scans/${encodeURIComponent(scan.id)}/image/`))return;
    const controller=new AbortController();let owned='';setOriginalSource('');
    fetch(API_BASE_URL+target,{headers:httpClient.getHeaders(),signal:controller.signal}).then(response=>{
      if(!response.ok)throw Error('Original unavailable');return response.blob();
    }).then(blob=>{if(!controller.signal.aborted){owned=URL.createObjectURL(blob);setOriginalSource(owned);}}).catch(()=>{});
    return()=>{controller.abort();if(owned)URL.revokeObjectURL(owned);};
  },[scan.id,image.original_url,layer,hasRegions]);
  useEffect(()=>{
    if(scan.content_type!=='image')return;
    let cancelled=false;
    let owned='';
    setSource('');setImageError('');
    const target=layerPath;
    if(!target){
      if(layer==='original'&&scan.image_preview_url)setSource(scan.image_preview_url);
      else setImageError('This image layer is unavailable for the saved assessment.');
      return;
    }
    // Only owner-protected scan assets, never a URL supplied by the scanned image.
    if(typeof target!=='string'||!target.startsWith(`/api/v1/scans/${encodeURIComponent(scan.id)}/image/`)){
      setImageError('The saved image reference is invalid.');return;
    }
    fetch(API_BASE_URL+target,{headers:httpClient.getHeaders()}).then(async response=>{
      if(!response.ok)throw new Error('Saved image could not be retrieved. Sign in again or retry.');
      return response.blob();
    }).then(blob=>{
      if(cancelled)return;
      owned=URL.createObjectURL(blob);setSource(owned);
    }).catch(e=>{if(!cancelled)setImageError(e instanceof Error?e.message:'Image unavailable.');});
    return()=>{cancelled=true;if(owned)URL.revokeObjectURL(owned);};
  },[scan.id,scan.content_type,scan.image_preview_url,layer,layerPath]);
  if(scan.content_type==='text')return <ScamResult scan={scan} onBack={onBack}/>;
  const labels:Record<Layer,string>={original:t('Original','Original'),overlay:t('Edited areas','Edit wale area'),heatmap:t('Heatmap','Heatmap'),mask:t('Mask','Mask'),ela:t('JPEG differences','JPEG ka farak'),attention:t('Where the model looked','Model ne kahan dekha')};
  return <section className="workspace-page">
    <button className="secondary-button" onClick={onBack}>{t('Back to history','History par wapas')}</button>
    <div className="report-heading"><div><div className={`verdict-heading verdict-${verdict.toLowerCase()}`}><VerdictIcon size={32} aria-hidden="true"/><h1>{plain.title}</h1></div><p>{plain.why}</p></div><button className="secondary-button" onClick={()=>exportForensicPDFReport(scan)}>{t('Download report','Report download karein')}</button></div>
    <AssessmentNotice/>
    <div className="result-layout">
      <div className="image-workbench">
        <div className="viewer-controls" role="group" aria-label={t('Image view','Image view')}>
          {(['original','overlay','attention'] as Layer[]).filter(value=>value!=='overlay'||hasRegions).map(value=><button key={value} aria-pressed={layer===value} disabled={value!=='original'&&!paths[value]} onClick={()=>{setLayer(value);setZoom(1);}}>{labels[value]}</button>)}
          <label>{t('Zoom','Zoom')} <select value={zoom} onChange={e=>setZoom(Number(e.target.value))}><option value={1}>100%</option><option value={1.5}>150%</option><option value={2}>200%</option><option value={3}>300%</option></select></label>
        </div>
        {layer==='attention'&&<p className="viewer-note" role="status">{t('Where the model looked (not where the edit is)','Model ne kahan dekha (yeh edit ki jagah nahi hai)')}</p>}
        {layer==='attention'&&<div className="attention-legend"><span>{t('Lower response','Kam response')}</span><span className="attention-scale" aria-hidden="true"/><span>{t('Higher response','Zyada response')}</span></div>}
        <div className="image-viewport">{source?layer==='overlay'&&originalSource?<div className="image-comparison" style={{transform:`scale(${zoom})`}}><img src={originalSource} alt={t('Original','Original')}/><img className="comparison-overlay" src={source} alt={labels[layer]} style={{clipPath:`inset(0 ${100-comparison}% 0 0)`}}/></div>:<img src={source} alt={labels[layer]} style={{transform:`scale(${zoom})`}}/>:<p role="status">{imageError?t('This view could not be loaded. Try again.','Yeh view load nahi hua. Dobara koshish karein.'):t('Loading image...','Image load ho rahi hai...')}</p>}</div>
        {layer==='overlay'&&originalSource&&<label className="viewer-note">{t('Compare original and highlighted areas','Original aur dikhaye gaye areas compare karein')}<input type="range" min={0} max={100} value={comparison} onChange={e=>setComparison(Number(e.target.value))}/></label>}
        <p className="viewer-caption">{layer==='original'?t('Your original file is kept unchanged.','Aapki original file badli nahi gayi hai.'):layer==='attention'?t('Where the model looked (not where the edit is)','Model ne kahan dekha (yeh edit ki jagah nahi hai)'):t('Highlighted areas are estimates. They are not proof of an edit.','Dikhaye gaye area andaze hain. Yeh edit ka saboot nahi hain.')}</p>
        {!hasRegions&&<p className="viewer-note">{t('No edited area found (edits can still be missed)','Koi edit wala area nahi mila (edits phir bhi miss ho sakte hain)')}</p>}
      </div>
      <div className="signal-panel"><h2>{t('What we found','Kya mila')}</h2>
        <div className="signal-row"><h3>{t('Signs of AI','AI ke sanket')}</h3><p className="score-value">{imageAiLevel(scan,language)}</p><p>{t('This reading can be wrong. A low reading does not prove that a photo is real.','Yeh reading galat ho sakti hai. Kam reading se photo ka real hona prove nahi hota.')}</p></div>
        <div className="signal-row"><h3>{t('Signs of editing','Editing ke sanket')}</h3><p className="score-value">{level(image.manipulation_prob,language)}</p><p>{t('Small changes, removed objects and face swaps can be missed.','Chhote edits, hataye gaye objects aur face swap miss ho sakte hain.')}</p></div>
        <div className="signal-row"><h3>{t('Why','Kyun')}</h3><p>{plain.why}</p>{limits.length>0&&<p>{t('Image size or quality also limits this check.','Image ka size ya quality bhi is check ko limit karti hai.')}</p>}</div>
        <div className="signal-row"><h3>{t('What to do next','Ab kya karein')}</h3><p>{plain.next}</p></div>
      </div>
    </div>
    <p className="viewer-note">{t('Editing check: tested mainly on pasted and copied areas. Generative fill, object removal and face swaps are not reliably covered.','Editing check: zyada testing paste aur copy wale edits par hui hai. Generative fill, object removal aur face swap bharosemand tarah se cover nahi hain.')}</p>
    <p className="viewer-note">{t('The edit checker is for research and nonprofit use only.','Edit checker sirf research aur nonprofit use ke liye hai.')}</p>
    <details className="report-details"><summary>{t('Details for experts','Experts ke liye details')}</summary>
      <p>{t('Technical records below are kept in English.','Neeche technical records English mein rakhe gaye hain.')}</p>
      <p>AI generation: {percent(image.ai_generated_prob)}. Manipulation: {percent(image.manipulation_prob)}. These readings are not guarantees.</p>
      <p>{image.ai_note}</p><p>{image.localization_note}</p>
      <div className="viewer-controls" role="group" aria-label="Expert image views">{(['original','heatmap','mask','ela','attention'] as Layer[]).map(value=><button key={value} aria-pressed={layer===value} disabled={value!=='original'&&!paths[value]} onClick={()=>{setLayer(value);setZoom(1);}}>{labels[value]}</button>)}</div>
      {layer==='ela'&&<p>JPEG recompression differences, fixed 8x gain. Bright pixels are not proof of editing. Window {supporting?.scope?.width} x {supporting?.scope?.height} at ({supporting?.scope?.x}, {supporting?.scope?.y}).</p>}
      <p>{image.model_attention?.note}</p>
      <h3>Original model reasons</h3><ul className="result-reasons">{reasons.map(reason=><li key={reason}>{reason}</li>)}</ul>
      <h3>Quality and file records</h3>{limits.map(item=><p key={item}>{item}</p>)}
      <p>Content Credentials: {provenance.c2pa_status||'not assessed'}. Trusted signature: {String(!!provenance.signature_trusted)}. Missing metadata is neutral.</p><p>{provenance.note}</p>
      {supporting&&<><h3>Supporting forensic observations</h3><p>{supporting.notice}</p><p>{supporting.ela?.note}</p><p>{supporting.noise?.note}</p><p>{supporting.copy_move?.note}</p></>}
      <p>Model: {result?.model_version||'Unavailable'}</p><p>Source SHA-256: <code className="break-all">{image.source_sha256||'Not recorded'}</code></p><p>{image.model_view_note}</p><p>{image.localizer_license}</p>
    </details>
  </section>;
}
