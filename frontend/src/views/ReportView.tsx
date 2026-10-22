import { useEffect, useState } from 'react';
import type { ScanRecord } from '../types';
import { API_BASE_URL, httpClient } from '../services/api/client';
import { ScamResult } from '../components/scam_message/ScamResult';
import { PhishingReport } from '../components/phishing_url/PhishingReport';
import { ResultSummary } from '../components/results/ResultSummary';
import { exportForensicPDFReport } from '../services/pdfExporter';
import { useResultLanguage } from '../services/resultLanguage.ts';

type Layer = 'original' | 'overlay' | 'heatmap' | 'mask' | 'ela' | 'attention' | 'noise' | 'frequency' | 'repetition' | 'gabor';
const diagnosticLayers:Layer[]=['ela','noise','frequency','repetition','gabor'];
const percent=(value:unknown)=>typeof value==='number'&&Number.isFinite(value)?`${(value*100).toFixed(1)}%`:'Unavailable';

export function ReportView({scan,onBack}:{scan:ScanRecord;onBack:()=>void}) {
  const {t}=useResultLanguage();
  const [layer,setLayer]=useState<Layer>('original');
  const [zoom,setZoom]=useState(1);
  const [source,setSource]=useState('');
  const [imageError,setImageError]=useState('');
  const [originalSource,setOriginalSource]=useState('');
  const [comparison,setComparison]=useState(50);
  const [advanced,setAdvanced]=useState(false);
  const result=scan.result;
  const meta=result?.metadata||{};
  const current=result?.detector_id==='image_deepfake.evidence.v2';
  const image=meta.image_analysis||{};
  const supporting=image.supporting_forensics;
  const provenance=image.provenance||{};
  const limits:string[]=image.quality?.limits||[];
  const reasons:string[]=image.reasons||[current?result?.explanation||'Evidence unavailable.':'This historical report used the previous detector. Run a new assessment for separate AI and localization evidence.'];
  const paths=image.assets||{};
  const hasRegions=Array.isArray(image.regions)&&image.regions.length>0;
  const comparisonPath=diagnosticLayers.includes(layer)?paths.diagnostic_original:image.original_url;
  const canCompare=layer!=='original'&&layer!=='frequency'&&!!comparisonPath;
  const layerPath=layer==='original'?image.original_url:paths[layer];
  useEffect(()=>{
    setOriginalSource('');
    if(!canCompare)return;
    const target=comparisonPath;
    if(typeof target!=='string'||!target.startsWith(`/api/v1/scans/${encodeURIComponent(scan.id)}/image/`))return;
    const controller=new AbortController();let owned='';setOriginalSource('');
    fetch(API_BASE_URL+target,{headers:httpClient.getHeaders(),signal:controller.signal}).then(response=>{
      if(!response.ok)throw Error('Original unavailable');return response.blob();
    }).then(blob=>{if(!controller.signal.aborted){owned=URL.createObjectURL(blob);setOriginalSource(owned);}}).catch(()=>{if(!controller.signal.aborted)setImageError('Original image could not be loaded for comparison.');});
    return()=>{controller.abort();if(owned)URL.revokeObjectURL(owned);};
  },[scan.id,comparisonPath,canCompare,layer]);
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
  if(scan.content_type==='url')return <PhishingReport scan={scan} onBack={onBack}/>;
  const labels:Record<Layer,string>={original:t("Original"),overlay:t("Edited areas"),heatmap:t("Heatmap"),mask:t("Mask"),ela:t("JPEG differences"),attention:t("AI explanation"),noise:t("Noise and detail"),frequency:t("Frequency patterns"),repetition:t("Repeated patterns"),gabor:t("Texture directions")};
  return <section className="workspace-page">
    <button className="secondary-button" onClick={onBack}>{t("Back to history")}</button>
    <div className="report-heading"><button className="secondary-button" onClick={()=>exportForensicPDFReport(scan)}>{t("Download report")}</button></div>
    <ResultSummary scan={scan} visual={<div className="result-layout image-result-layout">
      <div className="image-workbench">
        <div className="viewer-intro"><h3>{t('Compare views')}</h3>{canCompare&&<p>{t('Drag to compare with the original.')}</p>}</div>
        <div className="viewer-controls" role="group" aria-label={t("Image view")}>
          {(['original','overlay','heatmap','mask','attention','ela','noise','frequency','repetition','gabor'] as Layer[]).filter(value=>(!['ela','noise','frequency','repetition','gabor'].includes(value)||advanced)&&(value==='original'||!!paths[value]&&(!['overlay','mask'].includes(value)||hasRegions))).map(value=><button key={value} aria-pressed={layer===value} onClick={()=>{setLayer(value);setZoom(1);}}>{labels[value]}</button>)}
          <label className="advanced-views"><input type="checkbox" checked={advanced} onChange={e=>{setAdvanced(e.target.checked);if(!e.target.checked&&diagnosticLayers.includes(layer))setLayer(paths.attention?'attention':'original');}}/>{t("Advanced forensic views")}</label>
          <label>{t("Zoom")} <select value={zoom} onChange={e=>setZoom(Number(e.target.value))}><option value={1}>100%</option><option value={1.5}>150%</option><option value={2}>200%</option><option value={3}>300%</option></select></label>
        </div>
        {layer==='attention'&&<p className="viewer-note"><strong>{t("Explainability")}: </strong>{paths.attention?t("Grad-CAM on the Vision Transformer. Highlights what influenced the AI classifier, not edited pixels."):t("Model explanation unavailable for this scan. Run a new check with explanations enabled.")}</p>}
        {layer==='attention'&&<div className="attention-legend"><span>{t("Lower response")}</span><span className="attention-scale copper-scale" aria-hidden="true"/><span>{t("Higher response")}</span></div>}
        {layer==='heatmap'&&<><p className="viewer-note">{t('Brighter colours mean a stronger edit-model response, not a confirmed edit.')}</p><div className="attention-legend"><span>{t('Lower response')}</span><span className="heatmap-scale" aria-hidden="true"/><span>{t('Higher response')}</span></div></>}
        {layer==='mask'&&<p className="viewer-note">{t('White pixels mark selected suspected areas. Black pixels are not selected. This is an estimate, not proof.')}</p>}
        {layer==='gabor'&&<p className="viewer-note">{t('Shows texture directions and edges. Natural patterns can be bright too. This is not an edited-area mask.')}</p>}
        {layer==='noise'&&<p className="viewer-note">{t('Bright detail includes natural edges, texture and compression. This is not an edit mask.')}</p>}
        {layer==='frequency'&&<p className="viewer-note">{t('This view shows repeating frequency patterns. Its positions are frequencies, not locations of edits in the photo.')}</p>}
        {layer==='repetition'&&<p className="viewer-note">{t('Lines join repeated patterns found by feature matching. Repeated objects can match in real photos too.')}</p>}
        {diagnosticLayers.includes(layer)&&<p className="viewer-note">{t('Native diagnostic window')}: {supporting?.scope?.width} × {supporting?.scope?.height}, x={supporting?.scope?.x}, y={supporting?.scope?.y}</p>}
        {layer==='ela'&&<p className="viewer-note">{t('JPEG differences show recompression changes, not confirmed edits. This is a separate native image window.')} {supporting?.scope?.width} × {supporting?.scope?.height}</p>}
        <div className="image-viewport">{source?canCompare&&originalSource?<div className="image-comparison" style={{transform:`scale(${zoom})`}}><img src={originalSource} alt={t("Original")}/><img className="comparison-overlay" src={source} alt={labels[layer]} style={{clipPath:`inset(0 ${100-comparison}% 0 0)`}}/><span className="comparison-divider" style={{left:`${comparison}%`}} aria-hidden="true"/><span className="comparison-label comparison-label-left">{labels[layer]}</span><span className="comparison-label comparison-label-right">{diagnosticLayers.includes(layer)?t('Original window'):t('Original')}</span></div>:<img src={source} alt={labels[layer]} style={{transform:`scale(${zoom})`}}/>:<p role="status">{imageError?t("This view could not be loaded. Try again."):t("Loading image...")}</p>}</div>
        {canCompare&&<label className="viewer-note comparison-control">{t("Comparison position")}<input aria-label={t('Comparison position')} type="range" min={0} max={100} value={comparison} disabled={!originalSource||!source} onChange={e=>setComparison(Number(e.target.value))}/></label>}
        <p className="viewer-caption">{layer==='original'?t("Your original file is kept unchanged."):layer==='attention'?t("Where the model looked (not where the edit is)"):diagnosticLayers.includes(layer)?t("These patterns can also occur in unedited photos."):t("Highlighted areas are estimates. They are not proof of an edit.")}</p>
        {hasRegions && (
          <div className="detected-regions-badge" style={{marginTop:'0.5rem',padding:'0.5rem 0.75rem',background:'rgba(245,158,11,0.08)',border:'1px solid rgba(245,158,11,0.25)',borderRadius:'6px',fontSize:'0.85rem'}}>
            <strong style={{color:'#d97706'}}>🎯 {t("Suspected AI / Edited Region")}: </strong>
            {image.regions.map((reg:{width:number;height:number;x:number;y:number;mean_probability?:number},idx:number)=>(
              <span key={idx} style={{marginRight:'0.75rem'}}>
                #{idx+1}: {reg.width}×{reg.height}px at ({reg.x},{reg.y}) {reg.mean_probability!=null?`(${percent(reg.mean_probability)})`:''}
              </span>
            ))}
          </div>
        )}
        {image.analysis_complete===true&&!hasRegions&&<p className="viewer-note">{t("No edited area found (edits can still be missed)")}</p>}
        {(layer==='heatmap'||layer==='mask')&&<p className="viewer-note">{t('Heatmap shows the edit model response. Mask shows selected pixels, not confirmed edits.')}</p>}
      </div>
    </div>}><>
      <p>{t("Technical records below are kept in English.")}</p><p>{t("Grad-CAM on the Vision Transformer. Highlights what influenced the AI classifier, not edited pixels.")}</p>
      <p>Reference-mapped AI reading: {percent(image.ai_generated_prob)}. Edit reading: {percent(image.manipulation_prob)}. These are not the chance this photo is fake. A high mapped reading can be below the alert boundary.</p>
      <p>{image.ai_note}</p><p>{image.localization_note}</p>
      {layer==='ela'&&<p>JPEG recompression differences, fixed 8x gain. Bright pixels are not proof of editing. Window {supporting?.scope?.width} x {supporting?.scope?.height} at ({supporting?.scope?.x}, {supporting?.scope?.y}).</p>}
      <p>{image.model_attention?.note}</p>
      <h3>Original model reasons</h3><ul className="result-reasons">{reasons.map(reason=><li key={reason}>{reason}</li>)}</ul>
      <h3>Quality and file records</h3>{limits.map(item=><p key={item}>{item}</p>)}
      <p>Content Credentials: {provenance.c2pa_status||'not assessed'}. Trusted signature: {String(!!provenance.signature_trusted)}. Missing metadata is neutral.</p><p>{provenance.note}</p><p>Metadata fields checked: {(provenance.metadata_fields||[]).join(', ')||'None found'}.</p>{provenance.ai_markers?.length>0&&<ul>{provenance.ai_markers.map((clue:{field:string;marker:string},i:number)=><li key={i}>{clue.field}: {clue.marker} (editable file clue)</li>)}</ul>}
      {supporting&&<><h3>Supporting forensic observations</h3><p>{supporting.notice}</p><p>{supporting.ela?.note}</p><p>{supporting.noise?.note}</p><p>{supporting.copy_move?.note}</p><p>{supporting.frequency?.note}</p><p>{supporting.gabor?.note}</p></>}
      <p>Model: {result?.model_version||'Unavailable'}</p><p>Source SHA-256: <code className="break-all">{image.source_sha256||'Not recorded'}</code></p><p>{image.model_view_note}</p><p>{image.localizer_license}</p>
</></ResultSummary>


  </section>;
}
