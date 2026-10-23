import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
const require = createRequire(new URL('../../frontend/package.json', import.meta.url));
const ts = require('typescript');
const source = readFileSync(new URL('../../frontend/src/services/imageAssessment.ts', import.meta.url), 'utf8');
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } }).outputText;
const { imageViewLines, imageClassifierLabel, imageConfidenceLabel } = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`);
const result = { module: 'image_deepfake', metadata: { hf_status: 'applied', hf_risk_score: 95.92,
  model_views: { full_frame: { risk_score: .09 }, faces: [{ risk_score: 95.92 }, { risk_score: null }], disagreement: true, coverage_complete: false } } };
const lines = imageViewLines(result).join('\n');
assert.match(lines, /Full image fake score: 0.09\/100/);
assert.match(lines, /Face 1 fake score: 95.92\/100/);
assert.match(lines, /Face 2 fake score: Unavailable/);
assert.match(lines, /disagree/);
assert.match(lines, /coverage is incomplete/);
assert.equal(imageConfidenceLabel(), 'Not calibrated');
assert.equal(imageClassifierLabel(result), 'Highest assessed fake score: 95.92/100');
assert.deepEqual(imageViewLines(undefined), []);
assert.equal(imageClassifierLabel(undefined), 'Classifier unavailable');
assert.doesNotMatch(imageClassifierLabel(result), /Authentic|confidence|%/);
const vit = { ...result, metadata: { ...result.metadata, assessment_policy: 'image-vit-v3', score_available: true,
  scope_state: 'SUPPORTED', decision_policy_validated: false, hf_model: 'fixture', hf_revision: 'revision' } };
assert.match(imageViewLines(vit).join('\n'), /Scope: detected human faces/);
assert.match(imageViewLines(vit).join('\n'), /Full image diagnostic score/);
assert.match(imageViewLines(vit).join('\n'), /Not validated; manual review required/);
assert.doesNotMatch(imageViewLines(vit).join('\n'), /CNN/);
const verdictSource = readFileSync(new URL('../../frontend/src/services/verdict.ts', import.meta.url), 'utf8');
const verdictCode = ts.transpileModule(verdictSource, {compilerOptions:{module:ts.ModuleKind.ESNext}}).outputText;
const {assessmentVerdict} = await import(`data:text/javascript;base64,${Buffer.from(verdictCode).toString('base64')}`);
assert.equal(assessmentVerdict({status:'SUCCESS',result:{...vit,status:'SUCCESS',verdict:'UNCERTAIN',risk_score:99}}), 'REVIEW REQUIRED');
assert.equal(assessmentVerdict({status:'PARTIAL_SUCCESS',result:{...vit,status:'PARTIAL_SUCCESS',verdict:'UNSUPPORTED',risk_score:0}}), 'NO ASSESSABLE FACE');
console.log('PASS: frame/face disagreement and unavailable scores remain visible; no authenticity or confidence claim.');

const general = {...vit, metadata:{...vit.metadata, assessment_policy:"image-general-v4", scope_state:"SUPPORTED", decision_policy_validated:false}};
assert.equal(assessmentVerdict({status:"SUCCESS", result:{...general, status:"SUCCESS",verdict:"UNCERTAIN",risk_score:99.98}}), "REVIEW REQUIRED");
assert.match(imageViewLines(general).join("\n"), /whole-image/i);
