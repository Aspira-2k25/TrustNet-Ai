import type {ScanRecord} from '../types';
export function assessmentVerdict(scan: ScanRecord): string {
 const r=scan.result;
 if (!r || !['SUCCESS','PARTIAL_SUCCESS'].includes(scan.status) || !['SUCCESS','PARTIAL_SUCCESS'].includes(r.status)) return 'ASSESSMENT UNAVAILABLE';
 if(r.module==='scam_message')return r.metadata?.display_verdict || (r.verdict || 'UNKNOWN').replaceAll('_',' ');
 const risk=scan.trust_score?.trust_risk_score ?? r.risk_score;
 if(r.verdict==='UNCERTAIN'||r.metadata?.is_contradiction||scan.trust_score?.contradiction_detected||(risk>=40&&risk<62))return 'UNCERTAIN';
 if(['LIKELY_AI_MANIPULATED','AI_GENERATED'].includes(r.verdict)||risk>=62)return 'LIKELY AI / MANIPULATED';
 if(r.verdict==='LIKELY_AUTHENTIC'||(risk>=22&&risk<62))return 'LIKELY AUTHENTIC';
 return 'LOW MANIPULATION SIGNAL';
}
