import { useEffect, useState } from 'react';
import { CircleHelp, ShieldAlert, ShieldCheck } from 'lucide-react';
import type { ScanRecord } from '../types';
import { API_BASE_URL, httpClient } from '../services/api/client';
import { ScamResult } from '../components/scam_message/ScamResult';
import { AssessmentNotice } from '../components/AssessmentNotice';
import { exportForensicPDFReport } from '../services/pdfExporter';

type Layer = 'original' | 'overlay' | 'heatmap' | 'mask' | 'ela' | 'attention';
const titles:Record<string,string>={LIKELY_AI_GENERATED:'Likely AI-generated',LIKELY_MANIPULATED:'Likely manipulated',LIKELY_AUTHENTIC:'Likely authentic',INCONCLUSIVE:'Inconclusive'};
const percent=(value:unknown)=>typeof value==='number'&&Number.isFinite(value)?`${(value*100).toFixed(1)}%`:'Unavailable';

export function ReportView({scan,onBack}:{scan:ScanRecord;onBack:()=>void}) {
  const [layer,setLayer]=useState<Layer>('original');
  const [zoom,setZoom]=useState(1);
  const [source,setSource]=useState('');
  const [imageError,setImageError]=useState('');
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
  const layerPath=layer==='original'?image.original_url:paths[layer];
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
  return <section className="workspace-page">
    <button className="secondary-button" onClick={onBack}>Back to history</button>
    <div className="report-heading"><div><div className={`verdict-heading verdict-${verdict.toLowerCase()}`}><VerdictIcon size={32} aria-hidden="true"/><h1>{titles[verdict]||'Inconclusive'}</h1></div><p>{reasons[0]}</p></div><button className="secondary-button" onClick={()=>exportForensicPDFReport(scan)}>Export report</button></div>
    <AssessmentNotice/>
    <details className="report-details" open><summary>Editing coverage and research limits</summary>
      <p>Evaluated: synthetic splicing/copy-move and a small TGIF sample of SD2 and Photoshop/Firefly partial edits. Inpainting localization was weak and some cases exceeded the CPU budget. These results do not establish reliable detection of generative fill, inpainting, object removal or face swaps.</p>
      <p>A low reading does not rule out these edits. Authenticity verdicts are currently disabled; insufficient evidence returns Inconclusive.</p>
      <p>{image.localizer_license||'TruFor localization is research only, for nonprofit/informational use. Unrestricted commercial deployment requires a different licensed backend.'}</p>
    </details>
    <div className="result-layout">
      <div className="image-workbench">
        <div className="viewer-controls" role="group" aria-label="Image evidence layer">
          {(['original','overlay','heatmap','mask','ela','attention'] as Layer[]).map(value=><button key={value} aria-pressed={layer===value} disabled={value!=='original'&&!paths[value]} onClick={()=>{setLayer(value);setZoom(1);}}>{value==='ela'?'JPEG / ELA':value==='attention'?'Model attention':value[0].toUpperCase()+value.slice(1)}</button>)}
          <label>Zoom <select value={zoom} onChange={e=>setZoom(Number(e.target.value))}><option value={1}>100%</option><option value={1.5}>150%</option><option value={2}>200%</option><option value={3}>300%</option></select></label>
        </div>
        {layer==='ela'&&<p className="viewer-note" role="status">JPEG recompression differences, displayed at fixed 8× gain. Bright pixels are not proof of editing. Native diagnostic window: {supporting?.scope?.width} × {supporting?.scope?.height}, starting at ({supporting?.scope?.x}, {supporting?.scope?.y}). This is separate from the segmentation mask.</p>}
        {layer==='attention'&&<p className="viewer-note" role="status">{image.model_attention?.note} Target: {image.model_attention?.target}. Classifier view: {image.model_attention?.view_width} × {image.model_attention?.view_height}.</p>}
        <div className="image-viewport">{source?<img src={source} alt={`${layer} image evidence`} style={{transform:`scale(${zoom})`}}/>:<p role="status">{imageError||'Loading saved image…'}</p>}</div>
        <p className="viewer-caption">{layer==='original'?'Original upload. The file remains intact on the server.':layer==='attention'?'Classifier attention on its model view, not an edited-region mask.':layer==='ela'?'JPEG recompression differences in the declared native window, not a tampering mask.':'Pixel segmentation evidence from the manipulation model. A highlighted area is a model estimate, not proof of editing.'}</p>
      </div>
      <div className="signal-panel"><h2>Evidence streams</h2>
        <div className="signal-row"><h3>AI generation</h3><p className="score-value">{percent(image.ai_generated_prob)}</p><p>{image.ai_note||'No current AI generation assessment is available.'}</p></div>
        <div className="signal-row"><h3>Manipulation</h3><p className="score-value">{percent(image.manipulation_prob)}</p><p>{image.localization_note||'Localization unavailable. A low AI score cannot establish that the image is unaltered.'}</p><p>{Array.isArray(image.regions)?`${image.regions.length} supported region(s)`:'No region assessment available'}</p></div>
        <div className="signal-row"><h3>Provenance</h3><p>Content Credentials: {provenance.c2pa_status||'not assessed'}.</p><p>{provenance.signature_trusted?'Signature trust verified.':'No trusted signed origin established.'}</p><p>{provenance.note||'Missing metadata is neutral. Software and camera tags are editable.'}</p></div>
        <div className="signal-row"><h3>Quality and limits</h3>{limits.length?limits.map(item=><p key={item}>{item}</p>):<p>No blocking quality limit recorded. This does not guarantee that processing traces survive.</p>}</div>
      </div>
    </div>
    {supporting&&<details className="report-details"><summary>Classical forensic observations</summary>
      <p>{supporting.notice}</p>
      {supporting.scope&&<p>Native diagnostic window: {supporting.scope.width} × {supporting.scope.height} at ({supporting.scope.x}, {supporting.scope.y}). {supporting.scope.whole_image?'Covers this whole image.':'Covers a central window; observations do not describe the whole image.'}</p>}
      <p><strong>JPEG / ELA:</strong> {supporting.ela?.note||'Unavailable'}</p>
      {supporting.noise&&<p><strong>Noise residual:</strong> {supporting.noise.residual_rms} luminance levels RMS. {supporting.noise.note}</p>}
      {supporting.copy_move&&<p><strong>Repeated-pattern check:</strong> {supporting.copy_move.geometric_inliers} consistent feature matches. {supporting.copy_move.note}</p>}
      <p>These observations do not change the verdict or establish that an image is authentic.</p>
    </details>}
    {image.model_attention&&<details className="report-details"><summary>Classifier attention and its limits</summary><p>{image.model_attention.note}</p><p>{image.model_attention.target}</p></details>}
    <details className="report-details" open><summary>Why this result</summary><ul className="result-reasons">{reasons.map(reason=><li key={reason}>{reason}</li>)}</ul></details>
    <details className="report-details"><summary>Model and source record</summary><p>Model: {result?.model_version||'Unavailable'}</p><p>Native source: {scan.dimensions?`${scan.dimensions.width} × ${scan.dimensions.height}`:'Not recorded'}. SHA-256: <code className="break-all">{image.source_sha256||'Not recorded'}</code></p><p>{image.model_view_note||'AI classification and pixel localization use separate model views. Classifier attention is not a localization mask.'}</p></details>
  </section>;
}
