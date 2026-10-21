const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const message = {message_type:'email', text:'Your receipt is ready at https://example.com/',
  subject:'Receipt', claimed_sender:'receipt@example.com', reply_to:'',
  displayed_links:[{text:'Receipt',href:'https://example.com/'}], optional_analysis:false};
const sender = {id:'fixture',tab:{id:4},url:'https://mail.google.com/mail/u/0/#inbox/fixture'};

function worker() {
  const calls=[], store={origin:'http://localhost:8000',token:'local-fixture-token'};
  const context={console,AbortController,AbortSignal,setTimeout,clearTimeout,
    fetch:async(url,options)=>{
      calls.push({url,options});
      const inspecting=url.endsWith('/inspection');
      return {ok:true,status:200,json:async()=>({data:{id:'saved-scan',status:'SUCCESS',result:{
        module:'scam_message',status:'SUCCESS',risk_score:30,metadata:{links:[{
          url:'https://example.com/',inspection:inspecting?{status:'COMPLETED',summary:{observations:[]}}:undefined,
        }]}}}})};
    },
    chrome:{runtime:{id:'fixture',getURL:p=>'chrome-extension://fixture/'+p,onMessage:{addListener(){}}},
      storage:{local:{async get(){return {language:'hi'};},async set(){}},session:{async setAccessLevel(){},async get(){return store;},async set(value){Object.assign(store,value);},
        async remove(key){delete store[key];},async clear(){for(const key of Object.keys(store))delete store[key];}}}},
  };
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(__dirname,'../worker.js'),'utf8'),context);
  return {context,calls,store};
}

test('inspection uses the selected saved scan and fixed authenticated API path',async()=>{
  const {context,calls}=worker();
  await context.handle({action:'SCAN',id:'scan-1',message},sender);
  const response=await context.handle({action:'INSPECT_LINK',id:'inspect-1',scanId:'saved-scan',linkIndex:0},sender);
  assert.equal(response.scan.result.metadata.links[0].inspection.status,'COMPLETED');
  assert.equal(calls[1].url,'http://localhost:8000/api/v1/scans/saved-scan/links/0/inspection');
  assert.equal(calls[1].options.body,'{}');
  assert.equal(calls[1].options.headers.Authorization,'Bearer local-fixture-token');
  assert(!JSON.stringify(response).includes('local-fixture-token'));
});

test('arbitrary URLs, other scans, unselected links and other tabs are rejected before fetch',async()=>{
  const {context,calls}=worker();
  await context.handle({action:'SCAN',id:'scan-1',message},sender);
  for(const payload of [
    {scanId:'saved-scan',linkIndex:0,url:'http://127.0.0.1/'},
    {scanId:'different-scan',linkIndex:0},
    {scanId:'saved-scan',linkIndex:1},
    {scanId:'saved-scan',linkIndex:-1},
    {scanId:'saved-scan',linkIndex:0.5},
  ])await assert.rejects(()=>context.handle({action:'INSPECT_LINK',id:'inspect-1',...payload},sender));
  await assert.rejects(()=>context.handle({action:'INSPECT_LINK',id:'inspect-1',scanId:'saved-scan',linkIndex:0},{...sender,tab:{id:5}}));
  assert.equal(calls.length,1);
});

test('disconnect removes inspection context and session access',async()=>{
  const {context,calls,store}=worker();
  await context.handle({action:'SCAN',id:'scan-1',message},sender);
  await context.handle({action:'DISCONNECT'},{id:'fixture',url:'chrome-extension://fixture/options.html'});
  await assert.rejects(()=>context.handle({action:'INSPECT_LINK',id:'inspect-1',scanId:'saved-scan',linkIndex:0},sender));
  assert.equal(calls.length,1); assert.equal(store.token,undefined);
});

test('an expired session is cleared and is not shown as a safe inspection',async()=>{
  const {context,store}=worker();
  await context.handle({action:'SCAN',id:'scan-1',message},sender);
  context.fetch=async()=>({ok:false,status:401});
  await assert.rejects(()=>context.handle({action:'INSPECT_LINK',id:'inspect-1',scanId:'saved-scan',linkIndex:0},sender),/Session expired/);
  assert.equal(store.token,undefined);
});


test('foreign extension senders are rejected without a network request',async()=>{
 const {context,calls}=worker();
 await assert.rejects(()=>context.handle({action:'SCAN',id:'scan-1',message},{...sender,id:'foreign'}));assert.equal(calls.length,0);
});
test('language settings do not require or expose the login token',async()=>{
 const {context,calls}=worker();const result=await context.handle({action:'GET_LANGUAGE'},sender);
 assert.equal(result.language,'hi');assert.equal(calls.length,0);assert(!JSON.stringify(result).includes('token'));
 await assert.rejects(()=>context.handle({action:'SET_LANGUAGE',language:'xx'},sender));
});
test('status checks expire a stale login instead of showing connected',async()=>{
 const {context,store}=worker();context.fetch=async url=>({ok:url.endsWith('/health'),status:url.endsWith('/health')?200:401});
 const result=await context.handle({action:'STATUS'},{id:'fixture',url:'chrome-extension://fixture/options.html'});
 assert.equal(result.connected,false);assert.equal(result.login_required,true);assert.equal(store.token,undefined);
});

test('a late expired-status response cannot erase a newer login',async()=>{
 const {context,store}=worker();let release,requested=false;
 const pending=new Promise(resolve=>release=resolve);
 context.fetch=async url=>{if(url.endsWith('/health'))return {ok:true,status:200};requested=true;return pending;};
 const status=context.handle({action:'STATUS'},{id:'fixture',url:'chrome-extension://fixture/options.html'});
 for(let i=0;i<10&&!requested;i++)await Promise.resolve();assert(requested);
 store.token='new-session-token';
 release({ok:false,status:401});
 await assert.rejects(()=>status,/Connection changed/);
 assert.equal(store.token,'new-session-token');
});
test('malformed and out-of-range results are rejected',async()=>{
 for(const score of [-1,101,NaN]){const {context}=worker();context.fetch=async()=>({ok:true,status:200,json:async()=>({data:{id:'saved-scan',status:'SUCCESS',result:{module:'scam_message',status:'SUCCESS',risk_score:score}}})});await assert.rejects(()=>context.handle({action:'SCAN',id:'scan-1',message},sender),/Invalid backend/);}
});


test('disconnect cancels an in-flight request and discards a late result',async()=>{
 const {context,store}=worker();let release,signal;
 const pending=new Promise(resolve=>release=resolve);
 context.fetch=async(url,options)=>{signal=options.signal;return pending;};
 const scan=context.handle({action:'SCAN',id:'scan-late',message},sender);
 for(let i=0;i<5&&!signal;i++)await Promise.resolve();assert(signal);
 await context.handle({action:'DISCONNECT'},{id:'fixture',url:'chrome-extension://fixture/options.html'});
 assert(signal.aborted);assert.equal(store.token,undefined);
 release({ok:true,status:200,json:async()=>({data:{id:'saved-scan',status:'SUCCESS',result:{module:'scam_message',status:'SUCCESS',risk_score:10}}})});
 await assert.rejects(()=>scan,/Session changed/);
});
