/* Gmail adapter. Message content is read and sent only after an explicit click. */
(() => {
  'use strict';
  const P=globalThis.TrustNetPresentation,E=globalThis.TrustNetExtract;
  if(!P||!E)return;
  const installed=new Map();let language='en',timer;
  const rpc=request=>chrome.runtime.sendMessage(request);
  const t=(en,hi)=>P.text(language,en,hi);
  function el(tag,text='',className=''){const node=document.createElement(tag);node.textContent=text;node.className=className;return node;}
  const css=`:host{display:block;margin:16px 0;font-family:TrustNetPlex,'IBM Plex Sans',sans-serif;color:#252a27;font-size:14px;line-height:1.55}*{box-sizing:border-box}[hidden]{display:none!important}section{background:#faf9f5;border:1px solid #cbd1c8;border-radius:14px;padding:18px}header,.actions{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap}h2{font-size:18px;line-height:1.4;margin:18px 0 8px}h3{font-size:14px;margin:16px 0 4px}p{margin:6px 0;overflow-wrap:anywhere}button,select,a{font:inherit}button,select{border:1px solid #9aa79b;border-radius:8px;background:#fff;padding:7px 11px;color:#252a27;cursor:pointer}button.primary{background:#24695b;color:#fff;border-color:#24695b}button:disabled{opacity:.6;cursor:wait}button:focus-visible,select:focus-visible,a:focus-visible,summary:focus-visible{outline:3px solid #24695b;outline-offset:3px}a{color:#24695b;text-underline-offset:3px}summary{cursor:pointer;color:#24695b}details{border-top:1px solid #d5d8cf;margin-top:14px;padding-top:10px}.warning h2{color:#9d342e}.unsure h2{color:#795514}.low h2{color:#24695b}.notice{font-size:13px;border-top:1px solid #d5d8cf;margin-top:16px;padding-top:12px}.link{border-top:1px solid #d5d8cf;padding:12px 0}.address{font-family:monospace;word-break:break-all}.status{color:#4c584f}.loading{color:#24695b}pre{white-space:pre-wrap;word-break:break-word;font:12px/1.6 monospace}mark{background:#f8dfaa;color:#252a27}`;
  function attach(message){
    if(installed.has(message))return;
    const host=el('div');host.dataset.trustnetControl='true';
    const shadow=host.attachShadow({mode:'open'}),style=el('style',css),box=el('section');
    const header=el('header'),brand=el('strong','TrustNet'),actions=el('div','','actions');
    const languageSelect=el('select');languageSelect.setAttribute('aria-label','Result language');
    for(const [value,label] of [['en','English'],['hi','Hindi / Hinglish']]){const option=el('option',label);option.value=value;languageSelect.append(option);}languageSelect.value=language;
    const scanButton=el('button','','primary'),cancelButton=el('button'),settings=el('a');settings.href=chrome.runtime.getURL('options.html');settings.target='_blank';settings.rel='noopener noreferrer';
    const status=el('p','','status');status.setAttribute('role','status');status.setAttribute('aria-live','polite');
    const results=el('div'),notice=el('p','','notice');cancelButton.hidden=true;
    actions.append(languageSelect,scanButton,cancelButton);header.append(brand,actions);box.append(header,status,settings,results,notice);shadow.append(style,box);
    const body=message.querySelector('.a3s')||(message.classList?.contains('a3s')?message:null);
    if(!body?.parentElement)return;body.parentElement.insertBefore(host,body);
    const state={host,id:'',busy:false,identity:'',scan:null,render:null};installed.set(message,state);
    function words(){scanButton.textContent=t('Scan message','Message check karein');cancelButton.textContent=t('Cancel','Rokein');settings.textContent=t('Connect / settings','Connect / settings');notice.textContent=P.notice(language);languageSelect.value=language;}
    words();status.textContent=t('Click to check this opened message. Nothing is sent until you click.','Is message ko check karne ke liye click karein. Click se pehle kuch send nahi hota.');
    function cancel(){if(state.id)rpc({action:'CANCEL',id:state.id}).catch(()=>{});state.id='';state.busy=false;scanButton.disabled=false;cancelButton.hidden=true;box.removeAttribute('aria-busy');}
    state.cancel=cancel;
    cancelButton.onclick=()=>{cancel();status.textContent=t('Check cancelled. No new result is available.','Check rok diya. Naya result nahi hai.');results.replaceChildren();state.scan=null;};
    languageSelect.onchange=async()=>{language=languageSelect.value==='hi'?'hi':'en';await rpc({action:'SET_LANGUAGE',language});for(const value of installed.values())value.render?.();};
    function stillCurrent(id,identity){try{return state.id===id&&message.isConnected&&E.fingerprint(E.extract(message))===identity;}catch{return false;}}
    function render(){
      words();results.replaceChildren();if(!state.scan)return;
      const result=state.scan.result,meta=result.metadata||{},summary=P.summary(result,language);
      const banner=el('div','',summary.tone);banner.append(el('h2',summary.icon+' '+summary.title),el('h3',t('Why','Kyun')),el('p',summary.why),el('h3',t('What to do next','Ab kya karein')),el('p',summary.next));results.append(banner);
      if(summary.linksFound)results.append(el('p',t(`Message and links checked together. ${summary.linksChecked} of ${summary.linksFound} links checked.`,`Message aur links saath check hue. ${summary.linksFound} mein se ${summary.linksChecked} links check hue.`)));
      for(const [index,link] of (meta.links||[]).entries()){
        const card=el('div','','link');card.append(el('p',String(link.url||''),'address'),el('p',P.linkLabel(link,language)));
        if(index<8&&/^(?:https?:\/\/|www\.)/i.test(link.url||'')){
          const inspect=el('button',t('Check this website','Website check karein'));
          const note=el('p',t('Only on click, TrustNet contacts this website. It does not run scripts or submit forms.','Click karne par hi TrustNet website ko contact karega. Scripts ya forms nahi chalenge.'));
          const outcome=el('p');card.append(inspect,note,outcome);
          inspect.onclick=async()=>{
            if(state.busy)return;const identity=state.identity;if(E.fingerprint(E.extract(message))!==identity){state.scan=null;state.identity='';render();status.textContent=t('Message changed. Check it again.','Message badal gaya. Dobara check karein.');return;}const id=crypto.randomUUID();
            state.busy=true;state.id=id;inspect.disabled=true;scanButton.disabled=true;cancelButton.hidden=false;box.setAttribute('aria-busy','true');outcome.textContent=t('Checking website...','Website check ho rahi hai...');
            try{const response=await rpc({action:'INSPECT_LINK',id,scanId:state.scan.id,linkIndex:index});if(!stillCurrent(id,identity)){if(state.id===id)status.textContent=t('Message changed. Check it again.','Message badal gaya. Dobara check karein.');return;}if(!response.ok)throw new Error(response.error);const snapshot=response.scan.result.metadata?.links?.[index]?.inspection;state.scan=response.scan;render();status.textContent=snapshot?.status==='COMPLETED'?t('Website check saved. Missing checks remain listed in the full report.','Website check save hua. Jo check nahi hue woh full report mein hain.'):t('Could not check this link','Yeh link check nahi hua');}
            catch(error){if(state.id===id){outcome.textContent=t('Could not check this link','Yeh link check nahi hua');status.textContent=error.message;}}
            finally{if(state.id===id)cancel();inspect.disabled=false;}
          };
        }
        results.append(card);
      }
      const full=el('a',t('Open full report','Puri report kholein'));full.href=P.reportUrl(state.scan.id);full.target='_blank';full.rel='noopener noreferrer';results.append(full);
      const details=el('details'),label=el('summary',t('Details for experts','Experts ke liye details'));details.append(label,el('p',t('Technical records are kept in English.','Technical records English mein hain.')),el('p',`Warning index: ${result.risk_score}/100. Not a probability.`),el('p',result.explanation||''));
      for(const link of meta.links||[])details.append(el('p',String(link.reason||'')));
      const text=Array.from(meta.assessed_text||''),spans=(meta.spans||[]).filter(s=>Number.isInteger(s.start)&&Number.isInteger(s.end)&&s.start>=0&&s.end<=text.length&&s.start<s.end);
      const points=[...new Set([0,text.length,...spans.flatMap(s=>[s.start,s.end])])].sort((a,b)=>a-b),annotated=el('p');
      for(let i=0;i<points.length-1;i++){const start=points[i],end=points[i+1],active=spans.filter(s=>s.start<=start&&s.end>=end);const highlighted=active.some(s=>s.kind==='rule'||s.kind==='context'||(s.kind==='model'&&s.contribution>=.015));const fragment=el(highlighted?'mark':'span',text.slice(start,end).join(''));fragment.title=active.map(s=>s.note||'').join('; ');annotated.append(fragment);}details.append(annotated);results.append(details);
    }
    state.render=render;
    scanButton.onclick=async()=>{
      if(state.busy)return;let input;try{input=E.extract(message);}catch(error){status.textContent=error.message;return;}
      const id=crypto.randomUUID(),identity=E.fingerprint(input);state.id=id;state.identity=identity;state.busy=true;state.scan=null;results.replaceChildren();scanButton.disabled=true;cancelButton.hidden=false;box.setAttribute('aria-busy','true');status.textContent=t('Checking message and links...','Message aur links check ho rahe hain...');
      try{const response=await rpc({action:'SCAN',id,message:input});if(!stillCurrent(id,identity)){if(state.id===id)status.textContent=t('Message changed. Check it again.','Message badal gaya. Dobara check karein.');return;}if(!response.ok)throw new Error(response.error);if(response.id!==id)throw new Error('Mismatched response; try again.');state.scan=response.scan;render();status.textContent=t('Check saved.','Check save ho gaya.');}
      catch(error){if(state.id===id){results.replaceChildren();status.textContent=t('Check failed. This does not mean it is safe. ','Check fail hua. Iska matlab safe nahi hai. ')+(error.message||'Try again.');}}
      finally{if(state.id===id)cancel();}
    };
  }
  function refresh(){
    const opened=new Set(E.opened());
    for(const [message,state] of installed){
      let changed=false;
      if(state.identity){try{changed=E.fingerprint(E.extract(message))!==state.identity;}catch{changed=true;}}
      if(!opened.has(message)||!message.isConnected||changed){state.cancel();state.host.remove();installed.delete(message);}
    }
    for(const message of opened)attach(message);
  }
  new MutationObserver(records=>{if(records.every(r=>r.target.closest?.('[data-trustnet-control]')))return;clearTimeout(timer);timer=setTimeout(refresh,250);}).observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:['aria-hidden','class','style']});
  addEventListener('hashchange',()=>{for(const state of installed.values()){state.cancel();state.scan=null;state.identity='';state.render();}refresh();});addEventListener('popstate',refresh);
  rpc({action:'GET_LANGUAGE'}).then(response=>{if(response.ok){language=response.language==='hi'?'hi':'en';for(const state of installed.values())state.render?.();}}).catch(()=>{});
  refresh();
})();
