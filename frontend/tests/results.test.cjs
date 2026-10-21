const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),ts=require('typescript');
const oldTs=require.extensions['.ts'],oldTsx=require.extensions['.tsx'];
function compile(module,filename){let source=fs.readFileSync(filename,'utf8').replaceAll('import.meta.env','({DEV:true})');module._compile(ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true,target:ts.ScriptTarget.ES2022}}).outputText,filename);}
require.extensions['.ts']=compile;require.extensions['.tsx']=compile;
const storage=new Map();global.localStorage={getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)};
const React=require('react'),{renderToStaticMarkup}=require('react-dom/server');
const {simpleResult,notice,LanguageContext}=require('../src/services/resultLanguage.ts');
const {ReportView}=require('../src/views/ReportView.tsx');
const {exportForensicPDFReport}=require('../src/services/pdfExporter.ts');
const {execFileSync}=require('node:child_process'),path=require('node:path');
const python=process.env.TRUSTNET_TEST_PYTHON||path.resolve(__dirname,'../../.venv/Scripts/python.exe');
const mapResult=result=>JSON.parse(execFileSync(python,['-c',"import sys,json;from shared.presentation.result import public_result;print(json.dumps(public_result(json.load(sys.stdin))))"],{cwd:path.resolve(__dirname,'../..'),input:JSON.stringify(result),encoding:'utf8'}));
const scan=(verdict='INCONCLUSIVE',extra={})=>{
 const result={module:'image_deepfake',status:'SUCCESS',verdict,detector_id:'image_deepfake.evidence.v2',risk_score:10,metadata:{image_analysis:{ai_generated_prob:.1,manipulation_prob:null,regions:[],assets:{overlay:'/api/v1/scans/scan-unit/image/overlay'},...extra}}};
 result.presentation=mapResult(result);
 return {id:'scan-unit',status:'SUCCESS',content_type:'image',created_at:'2026-10-21T00:00:00Z',result};
};
const render=(record,language='en')=>renderToStaticMarkup(React.createElement(LanguageContext.Provider,{value:{language,setLanguage(){}}},React.createElement(ReportView,{scan:record,onBack(){}})));
test('an incomplete edit check is never presented as proof of a real image',()=>{
 const plain=simpleResult(scan());assert.equal(plain.title,'Image check partly finished');assert.match(plain.why,/edit check/);
 for(const language of ['en','hi']){const html=render(scan(),language);assert(html.includes(notice(language)));assert(!html.includes('Likely authentic'));}
});

test('a high score on a quality-limited real-photo report is not a reliable AI warning',()=>{
 const record=scan('INCONCLUSIVE',{ai_generated_prob:.935,quality:{adequate:false,limits:['JPEG compression']},analysis_complete:false});
 const html=render(record);
 assert(!html.includes('>High</p>'));
 assert.match(simpleResult(record).why,/quality/i);assert.match(simpleResult(record).why,/edit check/i);
 assert(html.includes('93.5%')); // Preserve the original numerical evidence in expert details.
});

test('an unsupported experimental head warning is shown as disagreement, not a confirmed high AI result',()=>{
 const record=scan('INCONCLUSIVE',{ai_generated_prob:.935,ai_checks_disagree:true,quality:{adequate:true},analysis_complete:false});
 assert.match(simpleResult(record).why,/AI checks disagree/);
});
test('zero supported regions do not offer an identical edited-area overlay',()=>{
 const html=render(scan());assert(html.includes('Edited-area check did not finish. No heatmap or mask is available.'));
 assert(!html.includes('>Edited areas</button>'));assert(html.includes('Details for experts'));assert(!/<details[^>]*open/.test(html));
});
test('high AI and editing results use simple headings in both languages',()=>{
 assert(render(scan('LIKELY_AI_GENERATED',{analysis_complete:true,manipulation_prob:.1})).includes('Looks AI-made'));
 assert(render(scan('LIKELY_MANIPULATED',{analysis_complete:true,manipulation_prob:.9,regions:[{area:20}]})).includes('Looks edited'));
 assert(render(scan('LIKELY_AI_GENERATED',{analysis_complete:true,manipulation_prob:.1}),'hi').includes('AI se bani lagti hai'));
});
test('unknown message verdicts and failed links do not become a low-warning result',()=>{
 const message={...scan(),content_type:'text',result:{module:'scam_message',status:'SUCCESS',verdict:'UNKNOWN',risk_score:1,metadata:{}}};
 message.result.presentation=mapResult(message.result);assert.equal(simpleResult(message).title,'We are not sure');
 message.result.verdict='NO_STRONG_INDICATORS';message.result.metadata.links=[{status:'UNAVAILABLE'}];message.result.presentation=mapResult(message.result);assert.equal(simpleResult(message).title,'Could not check this');
});
test('PDF starts with the same plain result and does not fetch zero-region overlay assets',async()=>{
 const calls=[];global.fetch=async url=>{calls.push(url);throw Error('No assets in unit fixture');};
 const data=await exportForensicPDFReport(scan(),false);const pdf=Buffer.from(data).toString('latin1');assert(pdf.startsWith('%PDF'));assert(pdf.includes('Image check partly finished'));assert(pdf.includes('What to do next'));assert.equal(calls.length,0);
});

test('message technical identity stays inside expert details',()=>{
 const {ScamResult}=require('../src/components/scam_message/ScamResult.tsx');
 const result={module:'scam_message',status:'SUCCESS',verdict:'LIKELY_SCAM',detector_id:'private-expert-identity',risk_score:90,metadata:{}};
 result.presentation=mapResult(result);
 const html=renderToStaticMarkup(React.createElement(ScamResult,{scan:{id:'qa',content_type:'text',status:'SUCCESS',result}}));
 assert(html.includes('private-expert-identity'));assert(!html.replace(/<details[\s\S]*<\/details>/g,'').includes('private-expert-identity'));
});


test('high reference reading below a decision boundary never becomes a High AI warning',()=>{
 const record=scan('INCONCLUSIVE',{ai_generated_prob:.8153,analysis_complete:true,manipulation_prob:.1,quality:{adequate:true}});
 assert.equal(record.result.presentation.level.ai,undefined);
 assert(!('risk_score' in record.result.presentation.details));
 assert.equal(record.result.presentation.checks[0].state,'uncertain');
});
test('available attention offers an accessible comparison slider even without edited regions',()=>{
 const record=scan('INCONCLUSIVE',{original_url:'/api/v1/scans/scan-unit/image/original',assets:{attention:'/api/v1/scans/scan-unit/image/attention'}});
 const html=render(record);
 assert(html.includes('type="range"'));assert(html.includes('aria-label="Comparison position"'));
 assert(!html.includes('>Mask</button>'));assert(!html.includes('>Heatmap</button>'));
 assert(html.includes('not where the edit is'));
});
