import { createContext, useContext } from 'react';
import type { ScanRecord } from '../types';

export type ResultLanguage = 'en' | 'hi';
export const LanguageContext = createContext<{language:ResultLanguage;setLanguage:(value:ResultLanguage)=>void}>({language:'en',setLanguage:()=>{}});
export function useResultLanguage(){
  const context=useContext(LanguageContext);
  return {...context,t:(english:string,hinglish:string)=>context.language==='hi'?hinglish:english};
}
export function storedLanguage():ResultLanguage{return localStorage.getItem('trustnet-language')==='hi'?'hi':'en';}
export const notice=(language:ResultLanguage)=>language==='hi'?'Yeh tool galti kar sakta hai. Ise madad ke liye use karein, saboot na maanein.':'This tool can make mistakes. Use it as a guide, not proof.';
export function level(value:unknown,language:ResultLanguage='en') {
  if(typeof value!=='number'||!Number.isFinite(value))return language==='hi'?'Check poora nahi hua':'Not fully checked';
  const word=value>=.7?'High':value>=.3?'Medium':'Low';
  return language==='hi'?{High:'Zyada',Medium:'Madhyam',Low:'Kam'}[word]:word;
}
export function imageAiLevel(scan:ScanRecord,language:ResultLanguage='en') {
  const image=scan.result?.metadata?.image_analysis||{};
  if(image.quality?.adequate===false)return language==='hi'?'Reading bharosemand nahi hai':'Reading not reliable';
  if(image.ai_checks_disagree===true||(image.reasons||[]).some((reason:string)=>reason.includes('does not corroborate')))
    return language==='hi'?'Checks aapas mein sehmat nahi hain':'Checks disagree';
  return level(image.ai_generated_prob,language);
}
export function simpleResult(scan:ScanRecord,language:ResultLanguage='en') {
  const hi=language==='hi',r=scan.result,m=r?.metadata||{},image=m.image_analysis||{};
  const valid=!!r&&['SUCCESS','PARTIAL_SUCCESS'].includes(r.status)&&['SUCCESS','PARTIAL_SUCCESS'].includes(scan.status);
  let tone:'warning'|'low'|'unsure'='unsure';
  let title=hi?'Hum pakka nahi keh sakte':'We are not sure';
  let why=hi?'Saare zaroori checks se saaf jawab nahi mila.':'The available checks did not give a clear answer.';
  let next=hi?'Doosre bharosemand source se confirm karein.':'Check another trusted source before making a decision.';
  if(!valid)return {title,tone,why:hi?'Check poora nahi hua. Iska matlab safe nahi hai.':'The check did not finish. This does not mean it is safe.',next};
  if(r.module==='image_deepfake'){
    if(r.detector_id!=='image_deepfake.evidence.v2')return {title,tone,why:hi?'Yeh purana result hai. Dobara check karein.':'This is an older result. Run a new check.',next};
    if(r.verdict==='LIKELY_AI_GENERATED'){
      tone='warning';title=hi?'AI se bani lagti hai':'Looks AI-made';
      why=hi?'Image check mein AI banane ke strong sanket mile.':'The image check found strong signs of AI generation.';
    }else if(r.verdict==='LIKELY_MANIPULATED'){
      tone='warning';title=hi?'Edit ki gayi lagti hai':'Looks edited';
      why=hi?'Image check ne ek ya zyada shak wale area dikhaye.':'The image check found signs of editing in one or more areas.';
    }else if(r.verdict==='LIKELY_AUTHENTIC'){
      tone='low';title=hi?'Koi saaf sanket nahi mila (isse real hona prove nahi hota)':'No clear signs found (this does not prove it is real)';
      why=hi?'Poore hue checks mein AI ya editing ke strong sanket nahi mile.':'The completed checks found no strong signs of AI generation or editing.';
    }else if(image.quality?.adequate===false){
      why=hi?'Image ki quality se bharosemand jawab nahi mila. Compression se zaroori details kho sakti hain.':'Image quality limits a reliable answer. Compression can remove useful details.';
      if(image.analysis_complete===false||image.manipulation_prob==null)why+=hi?' Editing ka check bhi poora nahi hua.':' The edit check also did not finish or give a reliable reading.';
    }else if(image.ai_checks_disagree===true){
      why=hi?'AI checks aapas mein sehmat nahi hain. Zyada reading se photo fake prove nahi hoti.':'The AI checks disagree. A high reading does not establish that this photo is fake.';
      if(image.analysis_complete===false||image.manipulation_prob==null)why+=hi?' Editing ka check bhi poora nahi hua.':' The edit check also did not finish or give a reliable reading.';
    }else if(image.analysis_complete===false||image.manipulation_prob==null){
      why=hi?'Editing ka check poora ya bharosemand nahi tha. Chhote edits miss ho sakte hain.':'The edit check was incomplete or could not give a reliable reading. Small edits can be missed.';
    }
    next=hi?'Original file aur uske source ko check karein. Sirf is result par faisla na lein.':'Check the original file and where it came from. Do not rely on this result alone.';
  }else{
    if(r.module==='phishing'&&(m.assessment_policy!=='dynamic-v2'||m.link_analysis_version!=='links-v1'))return {title,why:hi?'Yeh purana result hai. Dobara check karein.':'This is an older result. Run a new check.',next,tone};
    const warning=['LIKELY_SCAM','SMISHING_RISK'].includes(r.verdict||'')||(r.module==='phishing'&&r.verdict==='SUSPICIOUS');
    const missing=(m.links||[]).some((link:{status?:string})=>!['SUCCESS','PARTIAL_SUCCESS'].includes(link.status||''));
    const low=r.verdict==='NO_STRONG_INDICATORS'&&!missing&&r.status==='SUCCESS';
    tone=warning?'warning':low?'low':'unsure';
    if(warning)title=hi?'Scam jaisa lagta hai':r.module==='phishing'?'This link looks risky':'Looks like a scam';
    else if(low)title=hi?'Koi saaf sanket nahi mila (isse safe hona prove nahi hota)':'No clear signs found (this does not prove it is safe)';
    const rules=m.rule_findings||[];
    const riskyLinks=(m.links||[]).some((link:{risk_score?:number})=>(link.risk_score??0)>=70);
    const ruleCode=rules[0]?.code;
    const ruleReasons:Record<string,[string,string]>={SECRET_REQUEST:['The message asks you to share an OTP, password or payment PIN.','Message aapse OTP, password ya payment PIN maang raha hai.'],PRIZE_ADVANCE_FEE:['The message asks for payment before giving a prize.','Message inaam dene se pehle paise maang raha hai.'],GUARANTEED_INVESTMENT:['The message promises guaranteed or doubled investment returns.','Message investment par guaranteed ya double return ka vaada karta hai.']};
    why=missing?(hi?'Kuch links check nahi hue. Message ka result limited hai.':'Some links could not be checked. The message result is limited.'):ruleReasons[ruleCode]?ruleReasons[ruleCode][hi?1:0]:riskyLinks?(hi?'Message ke ek link mein risk ke sanket mile.':'A link in this message showed warning signs.'):
      rules.length?(hi?'Message mein pressure, paise ya private jaankari maangne ka pattern mila.':'The message matched a warning pattern, such as pressure, payment or a request for private information.'):
      warning?(hi?'Check mein jaane pehchaane fraud patterns se milte sanket mile.':'The check found patterns that resemble known scams.'):
      low?(hi?'Poore hue checks mein strong warning nahi mili. Sender verify nahi hua.':'The completed checks found no strong warning. The sender has not been verified.'):why;
    next=hi?'OTP, password ya paise na dein. Official app ya jaane pehchaane number se confirm karein.':'Do not share an OTP, password or payment. Verify through the official app or a number you already know.';
  }
  return {title,why,next,tone};
}
