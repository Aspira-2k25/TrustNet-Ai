import type {ScanRecord} from '../types';
export function assessmentVerdict(scan: ScanRecord): string {
 const r=scan.result;
 if(r?.module==='phishing') {
  if(r.metadata?.assessment_policy!=='dynamic-v2'||r.metadata?.link_analysis_version!=='links-v1')return 'RESCAN REQUIRED';
  if(r.verdict==='UNCERTAIN')return 'ASSESSMENT UNCERTAIN';
  if(!['SUCCESS','PARTIAL_SUCCESS'].includes(scan.status)||!['SUCCESS','PARTIAL_SUCCESS'].includes(r.status))return 'ASSESSMENT UNAVAILABLE';
  return r.metadata?.display_verdict || (r.label==='phishing'?'PHISHING RISK DETECTED':'LOW PHISHING SIGNAL');
 }
 if (!r || !['SUCCESS','PARTIAL_SUCCESS'].includes(scan.status) || !['SUCCESS','PARTIAL_SUCCESS'].includes(r.status)) return 'ASSESSMENT UNAVAILABLE';
 if(r.module==='scam_message')return r.metadata?.display_verdict || (r.verdict || 'UNKNOWN').replaceAll('_',' ');
 if(r.module==='image_deepfake' && r.metadata?.assessment_policy==='image-general-v4') {
  if(r.metadata?.score_available===false)return 'ASSESSMENT UNAVAILABLE';
  if(r.verdict==='LIKELY_AI_MANIPULATED')return 'LIKELY AI-GENERATED SIGNAL';
  if(r.verdict==='LOW_MANIPULATION_SIGNAL')return 'LOW DETECTED AI SIGNAL';
  return 'REVIEW REQUIRED';
 }
 if(r.module==='image_deepfake' && r.metadata?.assessment_policy==='image-vit-v3') {
  if(r.verdict==='UNSUPPORTED')return 'NO ASSESSABLE FACE';
  if(r.metadata?.score_available===false)return 'ASSESSMENT UNAVAILABLE';
  if(r.verdict==='LIKELY_AI_MANIPULATED')return 'LIKELY AI FACE SIGNAL';
  if(r.verdict==='LOW_MANIPULATION_SIGNAL')return 'LOW FACE SIGNAL';
  return 'REVIEW REQUIRED';
 }
 if(r.module==='image_deepfake' && r.metadata?.assessment_policy!=='image-screening-v2')return 'RESCAN REQUIRED';
 const risk=scan.trust_score?.trust_risk_score ?? r.risk_score;
 if(r.verdict==='UNCERTAIN'||r.metadata?.is_contradiction||scan.trust_score?.contradiction_detected||(risk>=40&&risk<62))return 'UNCERTAIN';
 if(['LIKELY_AI_MANIPULATED','AI_GENERATED'].includes(r.verdict)||risk>=62)return 'LIKELY AI / MANIPULATED';
 if(r.verdict==='LIKELY_AUTHENTIC'||(risk>=22&&risk<62))return 'LIMITED MANIPULATION SIGNAL';
 return 'LOW MANIPULATION SIGNAL';
}

export function assessmentCategory(scan: ScanRecord): 'high' | 'low' | 'review' | 'unavailable' {
 const r=scan.result;
 if(!r || !['SUCCESS','PARTIAL_SUCCESS'].includes(scan.status) || !['SUCCESS','PARTIAL_SUCCESS'].includes(r.status) || r.metadata?.score_available===false)return 'unavailable';
 if(assessmentVerdict(scan).includes('RESCAN'))return 'review';
 if(['UNCERTAIN','UNSUPPORTED','UNKNOWN','UNABLE_TO_ASSESS'].includes(r.verdict||''))return 'review';
 if(r.module==='image_deepfake' && !['image-screening-v2'].includes(r.metadata?.assessment_policy||'') && !r.metadata?.decision_policy_validated)return 'review';
 if(['LIKELY_AI_MANIPULATED','AI_GENERATED','LIKELY_SCAM','SUSPICIOUS','SMISHING_RISK'].includes(r.verdict||'') || r.module==='phishing'&&r.label==='phishing')return 'high';
 if(['LOW_MANIPULATION_SIGNAL','LOW_SMISHING_SIGNAL','NO_STRONG_INDICATORS'].includes(r.verdict||'') || r.module==='phishing'&&r.label==='legitimate')return 'low';
 return 'review';
}
