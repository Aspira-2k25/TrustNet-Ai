import { assessmentVerdict } from './verdict';
import { jsPDF } from 'jspdf';
import type { ScanRecord } from '../types';
import { API_BASE_URL, httpClient } from './api/client';

export async function exportForensicPDFReport(scan: ScanRecord, download = true): Promise<Uint8Array> {
  if(scan.content_type!=='image')return exportMessagePDF(scan,download);
  const doc=new jsPDF();let y=18;
  const line=(value:string)=>{
    const lines:string[]=doc.splitTextToSize(value.replace(/[^\x20-\x7e\n]/g,' '),180);
    for(const text of lines){if(y>275){doc.addPage();y=18;}doc.text(text,15,y);y+=5;}y+=3;
  };
  doc.setFontSize(16);line('TrustNet image evidence report');doc.setFontSize(10);
  line(`Scan: ${scan.id}. Recorded: ${scan.created_at}`);
  line('This tool can make mistakes. Results are probabilistic indicators, not proof. Verify important decisions independently.');
  const result=scan.result;
  if(result?.detector_id!=='image_deepfake.evidence.v2'){
    line('Inconclusive. Historical detector output requires a new assessment.');
    if(download)doc.save(`TrustNet_Image_${scan.id}.pdf`);return new Uint8Array(doc.output('arraybuffer'));
  }
  const image=result.metadata?.image_analysis||{};
  line(`Verdict: ${assessmentVerdict(scan)}`);
  (image.reasons||[]).forEach((r:string)=>line(r));
  const number=(v:unknown)=>typeof v==='number'?`${(100*v).toFixed(1)}%`:'Unavailable';
  line(`AI generation reading: ${number(image.ai_generated_prob)}. ${image.ai_note||''}`);
  line(`Manipulation reading: ${number(image.manipulation_prob)}. ${image.localization_note||''}`);
  line(`Source SHA-256: ${image.source_sha256||'Unavailable'}`);
  line(`Model: ${result.model_version}. Calibration: ${image.calibration_version||'Unavailable'}`);
  line(image.model_view_note||'');
  line(`Provenance: ${image.provenance?.c2pa_status||'Not assessed'}. Signature trusted: ${image.provenance?.signature_trusted?'yes':'no'}. Missing metadata is neutral.`);
  (image.quality?.limits||[]).forEach((r:string)=>line(r));
  line(`Supported pixel regions: ${image.regions?.length??0}. Model segmentation is not a verified edit mask.`);
  const supporting=image.supporting_forensics;
  if(supporting){
    line(`Classical forensic observations: ${supporting.notice}`);
    if(supporting.scope)line(`Native diagnostic window ${supporting.scope.width} x ${supporting.scope.height} at (${supporting.scope.x}, ${supporting.scope.y}); whole-image coverage: ${supporting.scope.whole_image?'yes':'no'}.`);
    if(supporting.ela)line(`JPEG / ELA: ${supporting.ela.note}`);
    if(supporting.noise)line(`Noise residual: ${supporting.noise.residual_rms} luminance levels RMS. ${supporting.noise.note}`);
    if(supporting.copy_move)line(`Repeated-pattern check: ${supporting.copy_move.geometric_inliers} geometric inliers. ${supporting.copy_move.note}`);
  }
  for(const [kind,url] of [['Original upload',image.original_url],['Supported region overlay',image.assets?.overlay]]){
    if(typeof url!=='string'||!url.startsWith(`/api/v1/scans/${encodeURIComponent(scan.id)}/image/`))continue;
    try{
      const response=await fetch(API_BASE_URL+url,{headers:httpClient.getHeaders()});
      if(!response.ok)throw new Error('Asset unavailable');
      const bytes=new Uint8Array(await response.arrayBuffer());
      const props=doc.getImageProperties(bytes);
      const width=180,height=Math.min(210,width*props.height/props.width);
      doc.addPage();y=18;line(kind);
      const fittedWidth=height*props.width/props.height;
      doc.addImage(bytes,props.fileType,15,y,fittedWidth,height);y+=height+8;
    }catch{line(`${kind}: saved image unavailable in this export. The scan record remains available on the website.`);}
  }
  if(download)doc.save(`TrustNet_Image_${scan.id}.pdf`);
  return new Uint8Array(doc.output('arraybuffer'));
}

function exportMessagePDF(scan: ScanRecord, download: boolean): Uint8Array {
  const doc = new jsPDF(); let y=18;
  const line = (text: string) => {
    // Keep every codepoint recoverable without asking the standard PDF font
    // to encode unsupported glyphs (which can corrupt the entire text run).
    const printable = Array.from(text, c => {
      const point = c.codePointAt(0)!;
      return (point >= 32 && point <= 126) || [9, 10, 13].includes(point) ? c : `\\u{${point.toString(16).toUpperCase()}}`;
    }).join('');
    const lines: string[] = doc.splitTextToSize(printable,180);
    lines.forEach(t=>{if(y>275){doc.addPage();y=18;}doc.text(t,15,y);y+=5;}); y+=3;
  };
  doc.setFontSize(14);line('TrustNet message assessment');doc.setFontSize(10);
  line('This tool can make mistakes. Results are indicators, not proof. Verify important decisions independently.');line(`Scan: ${scan.id} | ${scan.created_at}`);line(`Verdict: ${assessmentVerdict(scan)}`);
  const r=scan.result;
  if(r && ['SUCCESS','PARTIAL_SUCCESS'].includes(r.status) && ['SUCCESS','PARTIAL_SUCCESS'].includes(scan.status)) {
    const riskLabel=r.metadata?.rule_findings?.length?'Rule/model warning index (not probability)':r.metadata?.evaluated_domains?.includes('English email') ? 'Message-model fraud estimate (limited coverage)' : `SMS-model smishing estimate${r.metadata?.message_type==='email'?' (email calibration unavailable)':''}`;
    line(`${r.metadata?.fusion?.links_found?'Combined message / URL warning index':riskLabel}: ${r.risk_score.toFixed(1)}/100`);
    if(r.metadata?.fusion?.links_found){
      const f=r.metadata.fusion;
      line(`Message model: ${f.message_score}/100. Highest URL risk: ${f.url_score??'Unavailable'}. Links assessed: ${f.links_assessed}/${f.links_found}.`);
      line(f.definition);
      (r.metadata.links || []).forEach((link:{url:string;status:string;risk_score?:number;reason?:string;inspection?:import('../components/scam_message/LinkInspection').SavedInspection})=>{
        line(`${link.url}: ${link.status}; quick URL risk ${link.risk_score??'Unavailable'}. ${link.reason||''}`);
        const inspection=link.inspection;
        if(inspection){
          line(`Separate website inspection: ${inspection.status}. Snapshot: ${inspection.updated_at}.`);
          if(inspection.reason)line(inspection.reason);
          if(inspection.summary){
            line(inspection.summary.scope);
            line('What we observed and why it matters:');
            inspection.summary.observations.forEach(item=>{line(`${item.title}: ${item.observed}`);line(`Why it matters: ${item.why_it_matters}`);});
            line(`Model assessment: ${inspection.summary.model_assessment}`);
            line('What we could not check:');
            inspection.summary.missing_checks.forEach(item=>line(`${item.check}: ${item.reason}`));
          }
        }
      });
    }
    const dimensions=r.metadata?.assessment_dimensions;
    if(dimensions){line(`Category: ${dimensions.message_category.value}. ${dimensions.message_category.reason}`);line(`Sender: ${dimensions.sender_verification.status}. ${dimensions.sender_verification.reason}`);line(`AI authorship: ${dimensions.ai_authorship.status}. ${dimensions.ai_authorship.reason}`);}
    (r.metadata?.sender_link_observations || []).forEach((o:Record<string,unknown>)=>line(Object.entries(o).map(([k,v])=>`${k}: ${String(v)}`).join('; ')));
    (r.metadata?.next_steps || []).forEach((s:string)=>line(s));
    if(r.metadata?.optional_explanation){line(`Optional evidence summary: ${r.metadata.optional_explanation.status}. ${r.metadata.optional_explanation.reason || r.metadata.optional_explanation.method}`);(r.metadata.optional_explanation.evidence || []).forEach((e:{note:string})=>line(e.note));}
    const mc=r.metadata?.message_model?.confidence??(r.metadata?.confidence_available===false?null:r.confidence);
    line(`Message-model confidence: ${typeof mc==='number'?`${(mc*100).toFixed(1)}%`:'Unavailable'}. ${r.metadata?.message_model?.confidence_definition || r.metadata?.confidence_definition || 'Definition unavailable'}`);
    line(r.explanation || 'Explanation unavailable');
    (r.metadata?.rule_findings||[]).forEach((f:{reason:string})=>line(`Rule observation: ${f.reason}`));
    line('Original message (non-ASCII codepoints shown as Unicode escapes):');line(scan.raw_input || 'Original message unavailable');
    line(`Signed model evidence (${r.metadata?.attribution_unit || 'logit margin, not probability points'}):`);
    r.evidence?.forEach(e=>line(`${e.feature_or_region}: ${e.contribution.toFixed(4)}. ${e.human_readable_note}`));
    line('Layers:');r.analyzers?.forEach(a=>line(`${a.name}: ${a.status}. ${a.finding || a.reason || 'No finding supplied'}`));
    (r.metadata?.limitations || []).forEach((l:string)=>line(l));
    line(`Model: ${r.detector_id} / ${r.model_version}; preprocessing ${r.preprocessing_version}`);
  } else {line('No successful assessment available. Missing or failed data does not establish safety.');}
  line('PDF uses a standard font and reversible Unicode escapes for non-ASCII characters. The website preserves the original Unicode text.');
  if(download)doc.save(`TrustNet_Message_${scan.id}.pdf`);
  return new Uint8Array(doc.output('arraybuffer'));
}
