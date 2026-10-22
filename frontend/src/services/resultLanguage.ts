import { createContext, useContext } from 'react';
import type { ScanRecord } from '../types';
import catalog from '../../../shared/presentation/translations.json';
export const resultWords=catalog;

export type ResultLanguage = 'en' | 'hi';
export const LanguageContext = createContext<{language:ResultLanguage;setLanguage:(value:ResultLanguage)=>void}>({language:'en',setLanguage:()=>{}});
export function useResultLanguage(){
  const context=useContext(LanguageContext);
  return {...context,t:(key:string,hinglish?:string)=>(catalog[context.language] as Record<string,string>)[key]||(context.language==='hi'?hinglish||key:key)};
}
export function storedLanguage():ResultLanguage{return localStorage.getItem('trustnet-language')==='hi'?'hi':'en';}
export const notice=(language:ResultLanguage)=>catalog[language].notice;
export function resultView(scan:ScanRecord,language:ResultLanguage='en') {
  const view=scan.result?.presentation;
  const locale=view?.locales?.[language];
  return locale ? {...view,...locale} : {
    verdict_key:'incomplete' as const,headline:catalog[language].incomplete,
    reasons:[],next_steps:[],level:{},limits:[],details:{},
  };
}
export function simpleResult(scan:ScanRecord,language:ResultLanguage='en') {
  const view=resultView(scan,language);
  return {title:view.headline,why:view.reasons.map(r=>r.text).join(' '),next:view.next_steps.join(' '),
    tone: (['looks_ai','looks_edited','scam','risky'].includes(view.verdict_key)?'warning':['no_clear_signs','looks_real'].includes(view.verdict_key)?'low':'unsure') as 'warning'|'low'|'unsure'};
}
