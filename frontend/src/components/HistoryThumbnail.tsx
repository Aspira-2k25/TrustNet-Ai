import { useEffect,useRef,useState } from 'react';
import { Image as ImageIcon } from 'lucide-react';
import { API_BASE_URL,httpClient } from '../services/api/client';

/** Owner-protected images load only when a history row approaches the viewport. */
export function HistoryThumbnail({scanId}:{scanId:string}){
 const element=useRef<HTMLSpanElement>(null);const [source,setSource]=useState('');
 useEffect(()=>{
  if(!/^[A-Za-z0-9_-]{1,100}$/.test(scanId))return;
  const controller=new AbortController();let owned='';let requested=false;
  const observer=new IntersectionObserver(entries=>{
   if(requested||!entries.some(entry=>entry.isIntersecting))return;
   requested=true;observer.disconnect();
   fetch(`${API_BASE_URL}/api/v1/scans/${encodeURIComponent(scanId)}/image/original`,{headers:httpClient.getHeaders(),signal:controller.signal})
    .then(response=>{if(!response.ok)throw Error('Thumbnail unavailable');return response.blob();})
    .then(blob=>{if(!controller.signal.aborted){owned=URL.createObjectURL(blob);setSource(owned);}}).catch(()=>{});
  },{rootMargin:'100px'});
  if(element.current)observer.observe(element.current);
  return()=>{controller.abort();observer.disconnect();if(owned)URL.revokeObjectURL(owned);};
 },[scanId]);
 return <span ref={element} className="history-thumbnail" aria-hidden="true">{source?<img src={source} alt=""/>:<ImageIcon size={24}/>}</span>;
}
