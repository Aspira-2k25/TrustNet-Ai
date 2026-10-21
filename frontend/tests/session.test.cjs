const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),ts=require('typescript');
require.extensions['.ts']=(module,filename)=>module._compile(ts.transpileModule(fs.readFileSync(filename,'utf8').replaceAll('import.meta.env','({DEV:true})'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,filename);
const saved=new Map();global.localStorage={getItem:k=>saved.get(k)||null,setItem:(k,v)=>saved.set(k,v),removeItem:k=>saved.delete(k)};
global.window=new EventTarget();const {httpClient}=require('../src/services/api/client.ts');

test('expired protected login is cleared and the UI is notified',async()=>{
 httpClient.setToken('old-session');let notifications=0;const expired=()=>notifications++;
 window.addEventListener('trustnet-session-expired',expired);
 global.fetch=async()=>new Response(JSON.stringify({detail:'Sign in again'}),{status:401});
 await assert.rejects(httpClient.request('/protected'),/Sign in again/);
 assert.equal(httpClient.getToken(),null);assert.equal(notifications,1);
 window.removeEventListener('trustnet-session-expired',expired);
});

test('a late 401 cannot clear a newer login',async()=>{
 httpClient.setToken('old-session');let complete;
 global.fetch=()=>new Promise(resolve=>{complete=resolve;});
 const pending=httpClient.request('/protected');httpClient.setToken('new-session');
 complete(new Response('{}',{status:401}));await assert.rejects(pending);
 assert.equal(httpClient.getToken(),'new-session');
});

test('caller cancellation reaches fetch and releases its timeout',async()=>{
 const caller=new AbortController();let observed;
 global.fetch=async(_url,options)=>new Promise((_resolve,reject)=>{
  observed=options.signal;options.signal.addEventListener('abort',()=>reject(new DOMException('Aborted','AbortError')),{once:true});
 });
 const pending=httpClient.request('/protected',{signal:caller.signal});caller.abort();
 await assert.rejects(pending,{name:'AbortError'});assert.equal(observed.aborted,true);
});
