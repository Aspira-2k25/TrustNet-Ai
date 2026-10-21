/* Pure presentation contract. No network, mailbox access or HTML interpolation. */
var TrustNetPresentation = (() => {
  const text=(language,en,hi)=>language==='hi'?hi:en;
  const notice=language=>text(language,'This tool can make mistakes. Use it as a guide, not proof.','Yeh tool galti kar sakta hai. Ise madad ke liye use karein, saboot na maanein.');
  function summary(result,language='en') {
    const meta=result?.metadata||{},links=meta.links||[];
    const valid=result?.module==='scam_message'&&['SUCCESS','PARTIAL_SUCCESS'].includes(result.status)&&Number.isFinite(result.risk_score);
    const warning=valid&&['LIKELY_SCAM','SMISHING_RISK'].includes(result.verdict);
    const missing=links.some(link=>!['SUCCESS','PARTIAL_SUCCESS'].includes(link.status));
    // Unknown verdicts, partial results and failed link checks never default to safe.
    const low=valid&&result.status==='SUCCESS'&&result.verdict==='NO_STRONG_INDICATORS'&&!missing;
    const tone=warning?'warning':low?'low':'unsure';
    const title=warning?text(language,'Looks like a scam','Scam jaisa lagta hai'):low?text(language,'No clear signs found (this does not prove it is safe)','Koi saaf sanket nahi mila (isse safe hona prove nahi hota)'):text(language,'We are not sure','Hum pakka nahi keh sakte');
    const ruleReasons={SECRET_REQUEST:['The message asks you to share an OTP, password or payment PIN.','Message aapse OTP, password ya payment PIN maang raha hai.'],PRIZE_ADVANCE_FEE:['The message asks for payment before giving a prize.','Message inaam dene se pehle paise maang raha hai.'],GUARANTEED_INVESTMENT:['The message promises guaranteed or doubled investment returns.','Message investment par guaranteed ya double return ka vaada karta hai.']};
    const rule=ruleReasons[meta.rule_findings?.[0]?.code];
    const why=!valid?text(language,'The check did not finish. This does not mean it is safe.','Check poora nahi hua. Iska matlab safe nahi hai.'):missing?text(language,'Some links could not be checked. The message result is limited.','Kuch links check nahi hue. Message ka result limited hai.'):rule?rule[language==='hi'?1:0]:(meta.rule_findings||[]).length?text(language,'The message matched a warning pattern, such as pressure, payment or private information.','Message mein pressure, paise ya private jaankari maangne ka pattern mila.'):warning?text(language,'The check found patterns that resemble known scams.','Check mein scam jaise patterns mile.'):text(language,'The completed checks found no strong warning. The sender has not been verified.','Poore hue checks mein strong warning nahi mili. Sender verify nahi hua.');
    return {title,why,tone,icon:warning?'!':low?'✓':'?',next:text(language,'Do not share an OTP, password or payment. Verify through the official app or a number you already know.','OTP, password ya paise na dein. Official app ya jaane pehchaane number se confirm karein.'),linksFound:meta.fusion?.links_found??links.length,linksChecked:meta.fusion?.links_assessed??links.filter(l=>['SUCCESS','PARTIAL_SUCCESS'].includes(l.status)).length};
  }
  function linkLabel(link,language='en') {
    if(!link||!['SUCCESS','PARTIAL_SUCCESS'].includes(link.status)||!Number.isFinite(link.risk_score))return text(language,'Could not check this link','Yeh link check nahi hua');
    if(link.verdict==='SUSPICIOUS'||link.risk_score>=70)return text(language,'This link looks risky','Is link mein risk hai');
    return text(language,'No strong link warning found. This does not prove it is safe.','Link mein strong warning nahi mili. Safe hona prove nahi hota.');
  }
  function reportUrl(id){if(typeof id!=='string'||!/^[A-Za-z0-9_-]{1,100}$/.test(id))throw new Error('Invalid saved report ID');return 'http://localhost:5173/?scan='+encodeURIComponent(id);}
  function errorMessage(error,language='en'){
    const message=String(error?.message||error||'');
    if(/session|sign in|connect in/i.test(message))return text(language,'Sign in again in Connect / settings.','Connect / settings mein dobara sign in karein.');
    if(/backend|offline|disconnected|fetch/i.test(message))return text(language,'Local server is offline. Start TrustNet and retry.','Local server band hai. TrustNet start karke dobara karein.');
    if(/10,000|length|exceed/i.test(message))return text(language,'This message is too long. Paste a shorter section on the website.','Message bahut lamba hai. Website par chhota hissa paste karein.');
    if(/collapsed|readable|expand/i.test(message))return text(language,'Open and expand the email, then try again.','Email kholein aur expand karke dobara karein.');
    if(/busy|progress/i.test(message))return text(language,'Another check is running. Wait or cancel it.','Doosra check chal raha hai. Rukein ya cancel karein.');
    return text(language,'The check could not finish. Try again.','Check poora nahi hua. Dobara koshish karein.');
  }
  return {text,notice,summary,linkLabel,reportUrl,errorMessage};
})();
if(typeof globalThis!=='undefined')globalThis.TrustNetPresentation=TrustNetPresentation;
if(typeof module!=='undefined')module.exports=TrustNetPresentation;
