const test=require('node:test'),assert=require('node:assert/strict'),P=require('../presentation.js');
const result={module:'scam_message',status:'SUCCESS',risk_score:20,verdict:'NO_STRONG_INDICATORS',metadata:{}};
const words=P.words;
function view(key){return {verdict_key:key,locales:Object.fromEntries(['en','hi'].map(language=>[language,{verdict_key:key,headline:words[language][key],reasons:[{text:words[language].uncertain,evidence_id:'/verdict'}],next_steps:[words[language].next_text],limits:[]}]))};}
test('missing canonical result never falls back to legacy safe or warning labels',()=>{
 for(const verdict of ['LIKELY_SCAM','NO_STRONG_INDICATORS','UNKNOWN'])assert.equal(P.summary({...result,verdict}).title,'Could not check this');
});
test('canonical incomplete results preserve reasons and never become safe',()=>{
 const summary=P.summary({...result,presentation:view('incomplete')});assert.equal(summary.tone,'unsure');assert.equal(summary.title,'Could not check this');
});
test('both languages render the server contract without deriving a verdict',()=>{
 for(const key of ['scam','no_clear_signs','not_sure','incomplete'])for(const language of ['en','hi']){
 const summary=P.summary({...result,presentation:view(key)},language);assert.equal(summary.title,words[language][key]);assert(summary.why);assert(summary.next);assert(P.notice(language).length>30);
 }
});
test('report links are fixed local URLs with strict saved IDs',()=>{
 assert.equal(P.reportUrl('scan-abc'),'http://localhost:5173/?scan=scan-abc');
 for(const id of ['https://evil.test','../secret','a?url=evil','<script>',null])assert.throws(()=>P.reportUrl(id));
});
test('links need the server presentation, not a client risk threshold',()=>{
 assert.equal(P.linkLabel({status:'SUCCESS',risk_score:99}),'Could not check this link');
 assert.equal(P.linkLabel({presentation:view('risky')}),'This link looks risky');
});
