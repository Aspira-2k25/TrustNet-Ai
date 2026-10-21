const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {parseHTML}=require('linkedom'),{webcrypto}=require('node:crypto');
async function fixture(scanResult){
 const {window,document}=parseHTML('<html><body><h2 class="hP">Test mail</h2><div class="adn"><span class="gD" email="test@example.com"></span><div class="a3s">Your receipt is ready <a href="https://example.com/">Receipt</a></div></div></body></html>');
 Object.defineProperty(window.HTMLSelectElement.prototype,'value',{get(){return this._testValue||this.querySelector('option')?.value||'';},set(value){this._testValue=value;},configurable:true});
 window.HTMLElement.prototype.getBoundingClientRect=()=>({width:400,height:100});
 const calls=[],pending=[];
 const ctx={window,document,console,crypto:webcrypto,MutationObserver:class{observe(){}},setTimeout:()=>1,clearTimeout(){},addEventListener(){},getComputedStyle:()=>({display:'block',visibility:'visible'}),chrome:{runtime:{getURL:p=>'chrome-extension://fixture/'+p,sendMessage:async request=>{calls.push(request);if(request.action==='GET_LANGUAGE')return {ok:true,language:'en'};if(request.action==='SET_LANGUAGE')return {ok:true,language:request.language};if(request.action==='SCAN')return {ok:true,id:request.id,scan:{id:'scan-fixture',result:scanResult}};return {ok:true};}}}};
 window.getComputedStyle=ctx.getComputedStyle;vm.createContext(ctx);
 for(const name of ['extract.js','translations.js','presentation.js','content.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,'..',name),'utf8'),ctx);
 await Promise.resolve();await Promise.resolve();
 const shadow=document.querySelector('[data-trustnet-control]').shadowRoot;
 return {document,shadow,calls,ctx,pending};
}
const result={module:'scam_message',status:'SUCCESS',risk_score:90,verdict:'LIKELY_SCAM',metadata:{assessed_text:'Share OTP now',rule_findings:[{reason:'OTP request'}],links:[{url:'https://evil.invalid/',status:'UNAVAILABLE',reason:'Offline'}],fusion:{links_found:1,links_assessed:0}}};
const catalog=require('../translations.js');
result.presentation={verdict_key:'incomplete',locales:Object.fromEntries(['en','hi'].map(language=>[language,{verdict_key:'incomplete',headline:catalog[language].incomplete,reasons:[{text:catalog[language].SECRET_REQUEST,evidence_id:'/metadata/rule_findings/0'}],next_steps:[catalog[language].next_text],limits:[]}]))};

test('injecting a control never scans or sends email content',async()=>{
 const f=await fixture(result);assert(f.shadow.querySelector('section').textContent.includes('Nothing is sent until you click'));
 assert(!f.calls.some(c=>c.action==='SCAN'||c.message));
});
test('explicit click renders combined warning and inert URLs, with full report and no injected HTML',async()=>{
 const malicious={...result,explanation:'<img src=x onerror=alert(1)>',metadata:{...result.metadata,links:[{url:'https://evil.invalid/<script>',status:'UNAVAILABLE'}]}};
 const f=await fixture(malicious);await f.shadow.querySelector('button.primary').onclick();
 assert.equal(f.calls.filter(c=>c.action==='SCAN').length,1);assert(f.shadow.querySelector('section').textContent.includes('Could not check this'));assert(f.shadow.querySelector('section').textContent.includes('Could not check this link'));
 assert(!f.shadow.querySelector('script'));assert(!f.shadow.querySelector('img'));
 const links=[...f.shadow.querySelectorAll('a')];assert(links.every(a=>a.href.startsWith('chrome-extension://')||a.href.startsWith('http://localhost:5173/?scan=')));
 assert(f.shadow.querySelector('section').textContent.includes('What to do next'));assert(f.shadow.querySelector('section').textContent.includes('Use it as a guide, not proof.'));
});
test('language can change a saved result without rescanning',async()=>{
 const f=await fixture(result);await f.shadow.querySelector('button.primary').onclick();
 const select=f.shadow.querySelector('select');select.value='hi';await select.onchange();
 assert(f.shadow.querySelector('section').textContent.includes('Yeh check poora nahi hua'));assert.equal(f.calls.filter(c=>c.action==='SCAN').length,1);
});
