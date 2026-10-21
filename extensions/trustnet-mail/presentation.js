/* Pure presentation contract. No network, mailbox access or HTML interpolation. */
var TrustNetPresentation = (() => {
  const text=(language,en,hi)=>language==='hi'?hi:en;
  const words=typeof module!=='undefined'?require('./translations.js'):TrustNetWords;
  const notice=language=>words[language==='hi'?'hi':'en'].notice;
  function summary(result,language='en') {
    const catalog=words[language==='hi'?'hi':'en'];
    const view=result?.presentation?.locales?.[language]||result?.presentation;
    const known=view&&['looks_ai','looks_edited','scam','risky','no_clear_signs','not_sure','incomplete'].includes(view.verdict_key);
    const warning=known&&['looks_ai','looks_edited','scam','risky'].includes(view.verdict_key);
    const low=known&&view.verdict_key==='no_clear_signs';
    const links=result?.metadata?.links||[];
    return {title:known?view.headline:catalog.incomplete,
      why:known?(view.reasons||[]).map(r=>r.text).join(' '):catalog.failed,
      next:known?(view.next_steps||[]).join(' '):catalog.next_text,
      limits:known?view.limits:[],
      tone:warning?'warning':low?'low':'unsure',icon:warning?'!':low?'✓':'?',
      linksFound:result?.metadata?.fusion?.links_found??links.length,
      linksChecked:result?.metadata?.fusion?.links_assessed??links.filter(l=>['SUCCESS','PARTIAL_SUCCESS'].includes(l.status)).length};
  }
  function linkLabel(link,language='en') {
    return link?.presentation?.locales?.[language]?.headline||link?.presentation?.headline||words[language==='hi'?'hi':'en']["Could not check this link"];
  }
  function reportUrl(id){if(typeof id!=='string'||!/^[A-Za-z0-9_-]{1,100}$/.test(id))throw new Error('Invalid saved report ID');return 'http://localhost:5173/?scan='+encodeURIComponent(id);}
  function errorMessage(error,language='en'){
    const message=String(error?.message||error||'');
    if(/session|sign in|connect in/i.test(message))return words[language==='hi'?'hi':'en']["Sign in again in Connect / settings."];
    if(/backend|offline|disconnected|fetch/i.test(message))return words[language==='hi'?'hi':'en']["Local server is offline. Start TrustNet and retry."];
    if(/10,000|length|exceed/i.test(message))return words[language==='hi'?'hi':'en']["This message is too long. Paste a shorter section on the website."];
    if(/collapsed|readable|expand/i.test(message))return words[language==='hi'?'hi':'en']["Open and expand the email, then try again."];
    if(/busy|progress/i.test(message))return words[language==='hi'?'hi':'en']["Another check is running. Wait or cancel it."];
    return words[language==='hi'?'hi':'en']["The check could not finish. Try again."];
  }
  return {words,text,notice,summary,linkLabel,reportUrl,errorMessage};
})();
if(typeof globalThis!=='undefined')globalThis.TrustNetPresentation=TrustNetPresentation;
if(typeof module!=='undefined')module.exports=TrustNetPresentation;
