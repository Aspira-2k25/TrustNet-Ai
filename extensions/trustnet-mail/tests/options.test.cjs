const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {parseHTML}=require('linkedom');
function fixture(connectReply={ok:true,connected:true},hung=false){
 const root=path.resolve(__dirname,'..'),html=fs.readFileSync(path.join(root,'options.html'),'utf8');
 const {document}=parseHTML(html),calls=[],timers=new Map();let next=0,connected=false;
 const context={document,console,Promise,setTimeout:fn=>{const id=++next;timers.set(id,fn);return id;},clearTimeout:id=>timers.delete(id),chrome:{runtime:{sendMessage:async request=>{
  calls.push(request);
  if(request.action==='GET_LANGUAGE')return {ok:true,language:'en'};
  if(request.action==='CONNECT'){if(hung)return new Promise(()=>{});connected=connectReply.ok;return connectReply;}
  return {ok:true,connected,backend:true};
 }}}};
 vm.createContext(context);
 for(const script of document.querySelectorAll('script[src]'))vm.runInContext(fs.readFileSync(path.join(root,script.getAttribute('src')),'utf8'),context);
 return {document,calls,timers};
}
const settle=()=>new Promise(resolve=>setImmediate(resolve));
test('actual options HTML loads translations before presentation and login completes',async()=>{
 const f=fixture();await settle();
 f.document.getElementById('email').value='qa@example.com';f.document.getElementById('password').value='synthetic-test-password';
 await f.document.getElementById('connect').onsubmit({preventDefault(){}});
 assert.match(f.document.getElementById('status').textContent,/Connected/);
 assert.equal(f.document.getElementById('connect-button').disabled,false);
 assert.equal(f.document.getElementById('password').value,'');
 assert.equal(f.calls.filter(c=>c.action==='CONNECT').length,1);
});
test('failed login restores controls and reports the backend failure',async()=>{
 const f=fixture({ok:false,error:'Login failed. Check the local server and existing TrustNet account.'});await settle();
 await f.document.getElementById('connect').onsubmit({preventDefault(){}});
 assert.match(f.document.getElementById('status').textContent,/Login failed/);
 assert.equal(f.document.getElementById('connect-button').disabled,false);
});
test('an unresponsive extension cannot leave Connect loading forever',async()=>{
 const f=fixture(undefined,true);await settle();
 const pending=f.document.getElementById('connect').onsubmit({preventDefault(){}});await settle();
 assert.equal(f.document.getElementById('connect-button').disabled,true);
 for(const fire of [...f.timers.values()])fire();await pending;
 assert.match(f.document.getElementById('status').textContent,/timed out/);
 assert.equal(f.document.getElementById('connect-button').disabled,false);
});
