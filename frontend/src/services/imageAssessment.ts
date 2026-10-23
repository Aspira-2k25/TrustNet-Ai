import type { DetectionResult } from '../types';

function score(value: unknown): string {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= 100
    ? `${value.toFixed(2)}/100`
    : 'Unavailable';
}

export function imageViewLines(result: DetectionResult | null | undefined): string[] {
  const views = result?.metadata?.model_views;
  if (!result) return [];
  const lines = [`Full image fake score: ${score(views?.full_frame?.risk_score)}`];
  if (result?.metadata?.assessment_policy === 'image-vit-v3') {
    lines[0] = `Full image diagnostic score: ${score(views?.full_frame?.risk_score)} (does not determine the verdict)`;
    lines.unshift('Scope: detected human faces; whole-image authorship is not assessed.');
    lines.push(`Scope state: ${result.metadata.scope_state || 'Unavailable'}`);
    lines.push(`Decision policy: ${result.metadata.decision_policy_validated ? 'Validation-selected boundaries' : 'Not validated; manual review required'}`);
    lines.push(`Model: ${result.metadata.hf_model || 'Unavailable'} · revision ${result.metadata.hf_revision || 'Unavailable'}`);
    lines.push('Face coverage describes detected regions only; missed faces cannot be counted.');
    if (result.metadata.file_safety?.payload_detected) lines.push('File safety warning: payload indicator detected; this does not establish AI authorship.');
    if (result.metadata.source_retention) lines.push('Original image is not retained. Upload it again to inspect the image after reloading history.');
  }
  if (result?.metadata?.assessment_policy === 'image-screening-v2') {
    lines.unshift(`Trained CNN fake score: ${score(result.metadata.cnn_risk_score)}`);
    lines.push('Face coverage describes detected regions only; missed faces cannot be counted.');
    if (result.metadata.cnn_status !== 'APPLIED') lines.push('Trained CNN unavailable. The displayed score is diagnostic fallback screening only.');
    if (result.metadata.file_safety?.payload_detected) lines.push('File safety warning: trailing or hidden payload indicator detected. This does not establish AI authorship.');
    if (result.metadata.source_retention) lines.push('Original image is not retained. Upload it again to inspect the image after reloading history.');
  }

  if (result.metadata?.assessment_policy === 'image-general-v4') {
    lines[0] = `Whole-image model signal: ${score(result.metadata.score_available ? result.risk_score : null)}`;
    lines.push('Face observations are optional diagnostics and do not vote in this policy.');
    lines.push(`Model: ${result.metadata.hf_model || 'Unavailable'} | Execution: ${result.metadata.inference_mode || 'Unavailable'}`);
    lines.push(`Model revision: ${result.metadata.hf_revision || 'Hosted deployment not pinned'}`);
    lines.push(`Scope: ${result.metadata.scope || 'Unavailable'}`);
    lines.push(`Decision policy: ${result.metadata.decision_policy_validated ? 'Independent release gates passed' : 'Not validated; manual review required'}`);
    lines.push(result.metadata.branches?.general?.limits || 'General-image detector scope must be reviewed.');
  }
  if (result.metadata?.assessment_policy === 'image-vit-v3') lines.push('Execution: local');
  const clue = result.metadata?.generator_metadata;
  if (clue?.has_unverified_generator_clue) lines.push(`AI-generator metadata clue: ${clue.generator_name || 'Unknown'} - unverified, editable metadata; not authenticated provenance.`);
  const faces = Array.isArray(views?.faces) ? views.faces.slice(0, 4) : [];
  faces.forEach((face: { risk_score?: number }, index: number) => {
    lines.push(`Face ${index + 1} fake score: ${score(face.risk_score)}`);
  });
  if (views?.disagreement) lines.push('Model views disagree. Manual review required; authenticity is not established.');
  if (views?.coverage_complete === false) lines.push('Assessment coverage is incomplete. Missing checks are not evidence of authenticity.');
  lines.push('Model scores and the screening index are not calibrated correctness probabilities.');
  return lines;
}

export function imageClassifierLabel(result: DetectionResult | null | undefined): string {
  if (result?.metadata?.assessment_policy === 'image-vit-v3' && result.metadata.scope_state === 'NO_ASSESSABLE_FACE') return 'Classifier not run: no assessable face';
  if (result?.metadata?.hf_status !== 'applied') return 'Classifier unavailable';
  if(result.metadata.assessment_policy==='image-general-v4')return `Whole-image AI signal: ${score(result.metadata.hf_risk_score)}`;
  return `${result.metadata.assessment_policy === 'image-vit-v3' ? 'Highest assessed face fake score' : 'Highest assessed fake score'}: ${score(result.metadata.hf_risk_score)}`;
}

export function imageConfidenceLabel(): string {
  return 'Not calibrated';
}

export function analyzerObservation(item: {status?: string; finding?: string; reason?: string}): string {
 return item.finding || item.reason || (item.status==='SKIPPED' ? 'Not run. No conclusion is available.' : ['FAILED','UNAVAILABLE'].includes(item.status||'') ? 'Check unavailable. No conclusion is available.' : 'No finding supplied; absence of evidence is not an all-clear.');
}
