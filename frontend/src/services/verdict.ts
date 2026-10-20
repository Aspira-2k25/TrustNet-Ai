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
 if(r.module==='image_deepfake')return r.detector_id==='image_deepfake.evidence.v2'?(r.verdict||'INCONCLUSIVE').replaceAll('_',' '):'INCONCLUSIVE - RESCAN REQUIRED';
 return (r.verdict||'UNKNOWN').replaceAll('_',' ');
}
