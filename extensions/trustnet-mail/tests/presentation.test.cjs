const test=require('node:test'),assert=require('node:assert/strict'),P=require('../presentation.js');
const result={module:'scam_message',status:'SUCCESS',risk_score:20,verdict:'NO_STRONG_INDICATORS',metadata:{}};
test('only a completed known low-warning verdict may show the low state',()=>{
 assert.equal(P.summary(result).tone,'low');
 for(const verdict of ['UNKNOWN','INCONCLUSIVE','UNABLE_TO_ASSESS',undefined])assert.equal(P.summary({...result,verdict}).tone,'unsure');
 for(const status of ['FAILED','TIMEOUT','UNAVAILABLE','PARTIAL_SUCCESS'])assert.equal(P.summary({...result,status}).tone,'unsure');
});
test('failed links keep the combined result uncertain and are never called safe',()=>{
 const link={url:'https://bad.invalid/',status:'UNAVAILABLE'};
 assert.equal(P.linkLabel(link),'Could not check this link');
 assert.equal(P.summary({...result,metadata:{links:[link]}}).tone,'unsure');
 assert.equal(P.summary({...result,verdict:'LIKELY_SCAM',metadata:{links:[link]}}).tone,'warning');
});
test('both languages include a verdict, reason, next step and calm notice',()=>{
 for(const language of ['en','hi'])for(const verdict of ['LIKELY_SCAM','NO_STRONG_INDICATORS','UNKNOWN']){
  const s=P.summary({...result,verdict},language);for(const key of ['title','why','next','icon'])assert(s[key].length>0);
  assert(P.notice(language).length>30);
 }
 assert.equal(P.summary({...result,verdict:'LIKELY_SCAM'}).title,'Looks like a scam');
 assert.equal(P.summary(result,'hi').title.includes('safe'),true);
});
test('report links are fixed local URLs with strict saved IDs',()=>{
 assert.equal(P.reportUrl('scan-abc'),'http://localhost:5173/?scan=scan-abc');
 for(const id of ['https://evil.test','../secret','a?url=evil','<script>',null])assert.throws(()=>P.reportUrl(id));
});
test('link success still needs a finite risk reading',()=>{
 assert.equal(P.linkLabel({status:'SUCCESS'}),'Could not check this link');
 assert.match(P.linkLabel({status:'SUCCESS',risk_score:1}),/does not prove/);
 assert.equal(P.linkLabel({status:'SUCCESS',risk_score:80}),'This link looks risky');
});
