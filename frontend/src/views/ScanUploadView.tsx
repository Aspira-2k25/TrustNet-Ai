import { useState } from 'react';
import { Image, Link, MessageSquare, ScanLine } from 'lucide-react';
import type { ScanRecord } from '../types';
import { ImageScanView } from './image/ImageScanView';
import { ScamMessageScanView } from './scam_message/ScamMessageScanView';
import { PhishingScanView } from './phishing_url/PhishingScanView';

export type ModalityType = 'image' | 'phishing' | 'scam_message';
interface Props { onScanCompleted: (scan: ScanRecord) => void; onViewReport: (scan: ScanRecord) => void }

export function ScanUploadView({ onScanCompleted, onViewReport }: Props) {
  const [selected, setSelected] = useState<ModalityType>('image');
  const modules = [
    { id: 'image' as const, name: 'Image', icon: Image },
    { id: 'phishing' as const, name: 'URL', icon: Link },
    { id: 'scam_message' as const, name: 'Message', icon: MessageSquare },
  ];
  return <div className="workspace-page checker-page">
    <div className="checker-intro"><div className="page-intro"><h1>A closer look.<br/>A clearer decision.</h1><p>Check a photo, message or link before you trust it. Get a clear assessment, the reasons behind it and the limits of each check.</p></div><div className="workspace-principle"><ScanLine size={52} strokeWidth={1.2} aria-hidden="true"/><p>Evidence you can inspect.<br/><strong>Uncertainty you can see.</strong></p></div></div>
    <div className="module-switch" role="group" aria-label="Content type">
      {modules.map(({id,name,icon:Icon}) => <button key={id} aria-pressed={selected===id} onClick={()=>setSelected(id)}><Icon size={18} aria-hidden="true"/>{name}</button>)}
    </div>
    {selected === 'image' && <ImageScanView onScanCompleted={onScanCompleted} onViewReport={onViewReport}/>}
    {selected === 'phishing' && <PhishingScanView onScanCompleted={onScanCompleted} onViewReport={onViewReport}/>}
    {selected === 'scam_message' && <ScamMessageScanView onScanCompleted={onScanCompleted} onViewReport={onViewReport}/>}
  </div>;
}
