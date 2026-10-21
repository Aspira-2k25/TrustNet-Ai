import { useState, type ReactNode } from 'react';
import { LanguageContext,storedLanguage,type ResultLanguage } from '../services/resultLanguage.ts';
export function ResultLanguageProvider({children}:{children:ReactNode}) {
 const [language,setValue]=useState<ResultLanguage>(storedLanguage);
 const setLanguage=(value:ResultLanguage)=>{localStorage.setItem('trustnet-language',value);setValue(value);};
 return <LanguageContext.Provider value={{language,setLanguage}}>{children}</LanguageContext.Provider>;
}
