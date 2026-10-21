const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),ts=require('typescript');
const oldTs=require.extensions['.ts'],oldTsx=require.extensions['.tsx'];
function compile(module,filename){let source=fs.readFileSync(filename,'utf8').replaceAll('import.meta.env','({DEV:true})');module._compile(ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true,target:ts.ScriptTarget.ES2022}}).outputText,filename);}
require.extensions['.ts']=compile;require.extensions['.tsx']=compile;
const storage=new Map();global.localStorage={getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)};
const React=require('react'),{renderToStaticMarkup}=require('react-dom/server');
const {simpleResult,notice,LanguageContext}=require('../src/services/resultLanguage.ts');
const {ReportView}=require('../src/views/ReportView.tsx');
const {exportForensicPDFReport}=require('../src/services/pdfExporter.ts');
const scan=(verdict='INCONCLUSIVE',extra={})=>({id:'scan-unit',status:'SUCCESS',content_type:'image',created_at:'2026-10-21T00:00:00Z',result:{module:'image_deepfake',status:'SUCCESS',verdict,detector_id:'image_deepfake.evidence.v2',risk_score:10,metadata:{image_analysis:{ai_generated_prob:.1,manipulation_prob:null,regions:[],assets:{overlay:'/api/v1/scans/scan-unit/image/overlay'},...extra}}}});
const render=(record,language='en')=>renderToStaticMarkup(React.createElement(LanguageContext.Provider,{value:{language,setLanguage(){}}},React.createElement(ReportView,{scan:record,onBack(){}})));
test('an incomplete edit check is never presented as proof of a real image',()=>{
 const plain=simpleResult(scan());assert.equal(plain.title,'We are not sure');assert.match(plain.why,/incomplete/);
 for(const language of ['en','hi']){const html=render(scan(),language);assert(html.includes(notice(language)));assert(!html.includes('Likely authentic'));}
});

test('a high score on a quality-limited real-photo report is not a reliable AI warning',()=>{
 const record=scan('INCONCLUSIVE',{ai_generated_prob:.935,quality:{adequate:false,limits:['JPEG compression']},analysis_complete:false});
 const html=render(record);
 assert(html.includes('Reading not reliable'));assert(!html.includes('>High</p>'));
 assert.match(simpleResult(record).why,/quality.*edit check/is);
 assert(html.includes('93.5%')); // Preserve the original numerical evidence in expert details.
});
test('zero supported regions do not offer an identical edited-area overlay',()=>{
 const html=render(scan());assert(html.includes('No edited area found (edits can still be missed)'));
 assert(!html.includes('>Edited areas</button>'));assert(html.includes('Details for experts'));assert(!/<details[^>]*open/.test(html));
});
test('high AI and editing results use simple headings in both languages',()=>{
 assert(render(scan('LIKELY_AI_GENERATED')).includes('Looks AI-made'));
 assert(render(scan('LIKELY_MANIPULATED',{regions:[{area:20}]})).includes('Looks edited'));
 assert(render(scan('LIKELY_AI_GENERATED'),'hi').includes('AI se bani lagti hai'));
});
test('unknown message verdicts and failed links do not become a low-warning result',()=>{
 const message={...scan(),content_type:'text',result:{module:'scam_message',status:'SUCCESS',verdict:'UNKNOWN',risk_score:1,metadata:{}}};
 assert.equal(simpleResult(message).title,'We are not sure');
 message.result.verdict='NO_STRONG_INDICATORS';message.result.metadata.links=[{status:'UNAVAILABLE'}];assert.equal(simpleResult(message).title,'We are not sure');
});
test('PDF starts with the same plain result and does not fetch zero-region overlay assets',async()=>{
 const calls=[];global.fetch=async url=>{calls.push(url);throw Error('No assets in unit fixture');};
 const data=await exportForensicPDFReport(scan(),false);const pdf=Buffer.from(data).toString('latin1');assert(pdf.startsWith('%PDF'));assert(pdf.includes('We are not sure'));assert(pdf.includes('What to do next'));assert.equal(calls.length,0);
});
