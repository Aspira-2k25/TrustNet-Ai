import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import {dirname,resolve} from 'node:path';
import {createHash} from 'node:crypto';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'../..');
const require=createRequire(resolve(root,'frontend/package.json'));
const ts=require('typescript');const {jsPDF}=require('jspdf');
let document;const text=[];
function CapturedPDF(options){const doc=new jsPDF(options);const original=doc.text.bind(doc);
 doc.text=(value,...args)=>{text.push(...(Array.isArray(value)?value:[String(value)]));return original(value,...args);};
 doc.save=()=>{document=doc;};return doc;}
const cache=new Map();
function load(path){if(cache.has(path))return cache.get(path);const module={exports:{}};
 const compiled=ts.transpileModule(readFileSync(path,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
 new Function('require','module','exports',compiled)((name)=>name==='jspdf'?{jsPDF:CapturedPDF}:name.startsWith('.')?load(resolve(dirname(path),name+'.ts')):require(name),module,module.exports);
 cache.set(path,module.exports);return module.exports;}
const hash=createHash('sha256').update('report contract fixture').digest('hex');
const fixture={id:'report-v2-fixture',created_at:'2026-10-20T00:00:00Z',content_type:'image',status:'PARTIAL_SUCCESS',
 filename:'fixture.jpg',mime_type:'image/jpeg',result:{module:'image_deepfake',status:'PARTIAL_SUCCESS',verdict:'UNCERTAIN',risk_score:91.35,
 explanation:'Required trained CNN unavailable; manual review required.',metadata:{assessment_policy:'image-screening-v2',input_sha256:hash,
 cnn_status:'UNAVAILABLE',cnn_risk_score:null,model_views:{full_frame:{risk_score:.09},faces:[{risk_score:91.35}],disagreement:true,coverage_complete:false}},
 analyzers:['APPLIED','FAILED','UNAVAILABLE','SKIPPED'].map(status=>({name:'Fixture '+status,category:'test',status,finding:'Contract fixture'}))}};
const isV3=process.argv.includes('--v3');
const isV4=process.argv.includes('--v4');
const input=process.argv.slice(2).find(value=>!value.startsWith('--'));
const scan=input?JSON.parse(readFileSync(resolve(root,input),'utf8')):fixture;
if(isV3 && !input){scan.result.metadata={...scan.result.metadata,assessment_policy:'image-vit-v3',score_available:true,
 scope_state:'SUPPORTED',decision_policy_validated:false};scan.result.explanation='Policy not validated; manual review required.';}
load(resolve(root,'frontend/src/services/pdfExporter.ts')).exportForensicPDFReport(scan);
const content=text.join('\n');
for(const status of (input?['SKIPPED']:['FAILED','UNAVAILABLE','SKIPPED']))assert.match(content,new RegExp(status));
assert.ok(content.includes(scan.result.metadata.input_sha256));assert.match(content,/Not calibrated/);
if(isV3){assert.match(content,/detected human faces/);assert.match(content,/Not validated/);assert.doesNotMatch(content,/CNN unavailable/);}
else if(isV4){assert.match(content,/Whole-image model signal/);assert.match(content,/Chatgpt.*unverified/);assert.match(content,/Execution: local/);assert.doesNotMatch(content,/Nominal execution complete/);}
else assert.match(content,/CNN unavailable/);
assert.doesNotMatch(content,/Certified by:|UUID Hash:|APPEARS AUTHENTIC AND GENUINE/);
if(!isV4){assert.match(content,/0.09\/100/);assert.match(content,/91.35\/100/);}
const out=resolve(root,'runtime_state/image-module-audit');mkdirSync(out,{recursive:true});
writeFileSync(resolve(out,isV4?'report-v4.pdf':isV3?'report-v3.pdf':input?'report-v2-portrait.pdf':'report-v2-fixture.pdf'),Buffer.from(document.output('arraybuffer')));
console.log('PASS: actual PDF export preserves failures, source hash, missing CNN, and conflicting scores.');
