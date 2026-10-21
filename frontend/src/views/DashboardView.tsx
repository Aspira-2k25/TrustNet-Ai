import { HistoryThumbnail } from '../components/HistoryThumbnail';
import { useResultLanguage } from '../services/resultLanguage.ts';
import { useState } from 'react';
import type { ScanRecord } from '../types';
import { assessmentVerdict } from '../services/verdict';

interface Props {scans:ScanRecord[];onSelectScan:(scan:ScanRecord)=>void;onNewScan:()=>void}
export function DashboardView({scans,onSelectScan,onNewScan}:Props){
 const {t}=useResultLanguage();
 const [query,setQuery]=useState('');const [kind,setKind]=useState('all');
 const shown=scans.filter(s=>(kind==='all'||s.content_type===kind)&&`${s.id} ${s.filename||''} ${s.content_type}`.toLowerCase().includes(query.toLowerCase()));
 return <section className="workspace-page">
  <div className="report-heading"><div><h1>{t('Scan history','Pichhle checks')}</h1><p>Reopen the evidence recorded for your account. Historical results retain their original model version.</p></div><button className="primary-button" onClick={onNewScan}>{t('New check','Naya check')}</button></div>
  <div className="history-filters"><label>Find a scan<input type="search" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Filename or scan ID"/></label><label>Content<select value={kind} onChange={e=>setKind(e.target.value)}><option value="all">All content</option><option value="image">Images</option><option value="url">URLs</option><option value="text">Messages</option></select></label><p>{shown.length} saved assessment{shown.length===1?'':'s'}</p></div>
  {shown.length?<div className="history-list">{shown.map(scan=><button key={scan.id} onClick={()=>onSelectScan(scan)} className="history-item">{scan.content_type==='image'&&<HistoryThumbnail scanId={scan.id}/>}<div><strong>{scan.filename||`${scan.content_type==='text'?'Message':scan.content_type==='url'?'URL':'Image'} assessment`}</strong><p>{new Date(scan.created_at).toLocaleString()} · {scan.content_type}</p><code>{scan.id}</code></div><span>{assessmentVerdict(scan)}</span></button>)}</div>:<div className="empty-state"><h2>{t('No saved checks to show','Koi saved check nahi mila')}</h2><p>Run a new check, sign in to load saved reports, or adjust your filters. A missing result does not indicate safety.</p></div>}
 </section>;
}
