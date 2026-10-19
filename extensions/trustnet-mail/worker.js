/* Only fixed local gateway routes. Tokens stay in trusted extension session storage. */
const ALLOWED = new Set(['http://localhost:8000','http://127.0.0.1:8000']);
const inflight = new Map();
const selectedScans = new Map();
chrome.storage.session.setAccessLevel({accessLevel:'TRUSTED_CONTEXTS'});
const mailSender = sender => !!sender.tab && /^https:\/\/mail\.google\.com\//.test(sender.url || '');
const trustedSender = sender => sender.id===chrome.runtime.id && (sender.url || '').startsWith(chrome.runtime.getURL(''));
function validMessage(m) {
  if (!m || m.message_type!=='email' || typeof m.text!=='string' || !m.text.trim() || Array.from(m.text).length>10000 || m.optional_analysis!==false) return false;
  if (Object.keys(m).some(k => !['message_type','text','subject','claimed_sender','reply_to','displayed_links','optional_analysis'].includes(k))) return false;
  for (const [k,max] of [['subject',500],['claimed_sender',320],['reply_to',320]]) if(typeof m[k]!=='string'||m[k].length>max||m[k].includes('\0')) return false;
  return Array.isArray(m.displayed_links) && m.displayed_links.length<=50 && m.displayed_links.every(l=>l&&Object.keys(l).every(k=>['text','href'].includes(k))&&typeof l.text==='string'&&l.text.length<=500&&typeof l.href==='string'&&l.href.length<=2048);
}
async function handle(req,sender) {
  if (!req || typeof req.action!=='string') throw new Error('Invalid extension message');
  const trusted=trustedSender(sender), mail=mailSender(sender);
  if (!trusted && !mail) throw new Error('Unsupported sender');
  const saved=await chrome.storage.session.get(['origin','token']);
  const origin=ALLOWED.has(saved.origin)?saved.origin:'http://localhost:8000';
  if(req.action==='CONNECT') {
    if(!trusted || !ALLOWED.has(req.origin)||typeof req.email!=='string'||req.email.length>254||typeof req.password!=='string'||req.password.length>256) throw new Error('Invalid connection request');
    const response=await fetch(req.origin+'/api/v1/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:req.email,password:req.password}),signal:AbortSignal.timeout(10000)});
    if(!response.ok) throw new Error('Login failed. Check the local server and existing TrustNet account.');
    const data=(await response.json()).data;
    if(typeof data?.access_token!=='string'||data.access_token.length>8192) throw new Error('Invalid login response');
    await chrome.storage.session.set({origin:req.origin,token:data.access_token});
    return {connected:true};
  }
  if(req.action==='DISCONNECT') {if(!trusted) throw new Error('Invalid disconnect');await chrome.storage.session.clear();selectedScans.clear();return {connected:false};}
  if(req.action==='STATUS') {
    const response=await fetch(origin+'/health',{signal:AbortSignal.timeout(3000)});
    return {connected:response.ok && !!saved.token,backend:response.ok,login_required:!saved.token};
  }
  if(req.action==='CANCEL') {
    if(!mail || typeof req.id!=='string') throw new Error('Invalid cancellation');
    inflight.get(sender.tab.id+':'+req.id)?.abort(); return {cancelled:true};
  }
  const inspect=req.action==='INSPECT_LINK';
  const selected=mail?selectedScans.get(sender.tab.id):null;
  if(inspect && (Object.keys(req).some(k=>!['action','id','scanId','linkIndex'].includes(k)) || !selected || req.scanId!==selected.id || !Number.isInteger(req.linkIndex) || req.linkIndex<0 || req.linkIndex>=Math.min(8,selected.links))) throw new Error('Scan this selected email first, then inspect one of its saved links.');
  if((req.action!=='SCAN'&&!inspect)||!mail||!saved.token||typeof req.id!=='string'||!/^[a-zA-Z0-9-]{1,80}$/.test(req.id)||(!inspect&&!validMessage(req.message))) throw new Error('Connect in the extension settings and select a supported message.');
  const key=sender.tab.id+':'+req.id;
  if([...inflight.keys()].some(k=>k.startsWith(sender.tab.id+':'))) throw new Error('One scan is already in progress. Cancel or wait.');
  const controller=new AbortController();inflight.set(key,controller);
  const timer=setTimeout(()=>controller.abort(),45000);
  try {
    const endpoint=inspect?`/api/v1/scans/${encodeURIComponent(req.scanId)}/links/${req.linkIndex}/inspection`:'/api/v1/scans/scam/analyze';
    const response=await fetch(origin+endpoint,{method:'POST',headers:{'Authorization':'Bearer '+saved.token,'Content-Type':'application/json'},body:inspect?'{}':JSON.stringify(req.message),signal:controller.signal});
    if(response.status===401) {await chrome.storage.session.remove('token');throw new Error('Session expired. Sign in again in extension settings.');}
    if(!response.ok) throw new Error(response.status===409?'This URL inspection is already running. Try again shortly.':response.status===429?'Backend is busy; retry later.':response.status===422?'Unsupported input. Use manual paste and check language/length.':`Local request failed (${response.status}); no new verdict is available.`);
    const data=(await response.json()).data;
    if(data?.status!=='SUCCESS'||data?.result?.module!=='scam_message'||data?.result?.status!=='SUCCESS'||!Number.isFinite(data.result.risk_score)) throw new Error('Invalid backend assessment; no verdict is available.');
    if(inspect && data.id!==req.scanId) throw new Error('Mismatched inspection response');
    if(!inspect)selectedScans.set(sender.tab.id,{id:data.id,links:(data.result.metadata?.links || []).length});
    return {id:req.id,scan:{id:data.id,result:data.result}};
  } finally {clearTimeout(timer);inflight.delete(key);}
}
chrome.runtime.onMessage.addListener((req,sender,reply)=>{
  handle(req,sender).then(value=>reply({ok:true,...value}),error=>reply({ok:false,error:error.name==='AbortError'?'Cancelled or timed out. No verdict is available.':error.name==='TypeError'?'Local backend disconnected. Start TrustNet and retry.':error.message}));
  return true;
});
