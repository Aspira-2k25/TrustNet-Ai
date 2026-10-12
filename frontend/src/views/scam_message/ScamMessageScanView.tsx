import React, {useState} from 'react';
import {ArrowRight,RotateCcw,MessageSquare} from 'lucide-react';
import type {ScanRecord} from '../../types';
import {scanApi} from '../../services/api/scan.api';
import {ScamResult} from '../../components/scam_message/ScamResult';
interface Props {onScanCompleted:(scan:ScanRecord)=>void;onViewReport:(scan:ScanRecord)=>void}
const examples=['Your account will be blocked today. Send your OTP immediately.','Your OTP is 482193. Do not share it with anyone.','Reminder: your appointment is tomorrow at 10 AM.','Pay a processing fee to claim your prize.','This is a warning about a scam message asking people to send OTPs.'];
export const ScamMessageScanView:React.FC<Props>=({onScanCompleted,onViewReport})=>{
 const [messageText,setMessageText]=useState('');const [isProcessing,setIsProcessing]=useState(false);const [error,setError]=useState('');const [scan,setScan]=useState<ScanRecord|null>(null);
 const [mode,setMode]=useState<'sms'|'email'>('sms'); const [subject,setSubject]=useState(''); const [sender,setSender]=useState(''); const [reply,setReply]=useState(''); const [html,setHtml]=useState(false); const [optional,setOptional]=useState(false);
 const handleAnalyze=async()=>{
  if(!messageText.trim()||isProcessing)return;
  if(Array.from(messageText).length+(mode==='email'?Array.from(subject).length+2:0)>10000){setError('Subject and message exceed 10,000 characters. Shorten explicitly; content is never silently discarded.');return;}
  setIsProcessing(true);setError('');setScan(null);
  try{const result=await scanApi.analyzeScam(messageText,mode==='email'?{message_type:mode,subject,claimed_sender:sender,reply_to:reply,text_format:html?'html':'plain',optional_analysis:optional}:{message_type:mode,optional_analysis:optional});setScan(result);onScanCompleted(result);}
  catch(e){setError(e instanceof Error?e.message:'Message analysis failed');}
  finally{setIsProcessing(false);}
 };
 return <div className="space-y-6"><div className="rounded-2xl border border-[#1e3a5f] bg-[#0b132b] p-6 md:p-8 space-y-5 shadow-3d-card"><h2 className="font-bold text-xl flex gap-3 items-center"><MessageSquare className="text-sky-400"/>Check a message</h2>
 <p className="text-sm text-slate-400">English SMS/email screening separates fraud signals from spam. Evaluation covers limited labelled collections; modern inbox reliability, sender identity, linked sites and AI authorship are not established.</p>
 <label className="block text-sm">Input type <select disabled={isProcessing} value={mode} onChange={e=>{setMode(e.target.value as 'sms'|'email');setScan(null);}} className="bg-[#111d38] p-2 rounded"><option value="sms">Text message</option><option value="email">Selected email</option></select></label>
 {mode==='email'&&<div className="grid gap-3 md:grid-cols-2">{[['Subject',subject,setSubject,500],['Claimed sender',sender,setSender,320],['Reply-to (if available)',reply,setReply,320]].map(([label,value,setter,max])=><label key={String(label)} className="text-sm">{String(label)}<input value={String(value)} maxLength={Number(max)} disabled={isProcessing} onChange={e=>(setter as (v:string)=>void)(e.target.value)} className="block w-full bg-[#111d38] p-2 rounded mt-1"/></label>)}<label className="text-sm"><input type="checkbox" checked={html} disabled={isProcessing} onChange={e=>setHtml(e.target.checked)}/> Body contains HTML (decoded as text; never executed)</label></div>}
 <label className="block text-sm">Message<textarea value={messageText} onChange={e=>setMessageText(e.target.value)} disabled={isProcessing} rows={8} placeholder="Paste a message to analyze…" className="block mt-2 w-full rounded-xl p-4 bg-[#111d38] border border-[#1e3a5f] resize-y focus:outline-sky-500"/></label>
 <div className="flex justify-between text-xs text-slate-400"><span>All accepted text windows are processed. Highlight offsets refer to decoded text including the subject.</span><span>{Array.from(messageText).length+(mode==='email'?Array.from(subject).length+2:0)}/10000</span></div>
 <label className="block text-xs text-slate-300"><input type="checkbox" disabled={isProcessing} checked={optional} onChange={e=>setOptional(e.target.checked)}/> Optional Groq evidence summary: sends up to ten bounded evidence fragments and local notes to Groq. Full body and sender are not sent. Requires backend opt-in/key; local scanning always remains available.</label>
 <details><summary className="text-sm cursor-pointer text-sky-300">Try an example (not benchmark results)</summary><div className="flex flex-wrap gap-2 pt-3">{examples.map((t,i)=><button key={t} disabled={isProcessing} onClick={()=>setMessageText(t)} className="text-xs px-3 py-2 bg-[#16254a] rounded-lg">Example {i+1}</button>)}</div></details>
 {error&&<p role="alert" className="text-red-300 bg-red-950 p-3 rounded-lg">{error}</p>}
 <div className="flex flex-wrap justify-end gap-3"><button disabled={isProcessing} onClick={()=>{setMessageText('');setScan(null);setError('');}} className="flex gap-2 items-center px-4 py-2 text-sm"><RotateCcw size={14}/>Clear</button><button onClick={handleAnalyze} disabled={!messageText.trim()||isProcessing} className="bg-[#0077b6] disabled:opacity-50 px-6 py-3 rounded-xl text-sm font-bold flex items-center gap-2">{isProcessing?'Analyzing message…':'Analyze message'}<ArrowRight size={14}/></button></div>
 {isProcessing&&<p role="status" className="text-sm text-sky-300">Waiting for model inference and saved assessment…</p>}
 </div>{scan&&<><ScamResult scan={scan}/><button onClick={()=>onViewReport(scan)} className="text-sky-300">Open saved report</button></>}</div>;
};
