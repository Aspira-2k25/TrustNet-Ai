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
      storage:{session:{async setAccessLevel(){},async get(){return store;},async set(value){Object.assign(store,value);},
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
