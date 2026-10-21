import { useEffect, useState } from 'react';
import { Upload } from 'lucide-react';
import type { ScanRecord } from '../../types';
import { scanApi } from '../../services/api/scan.api';
import { httpClient } from '../../services/api/client';

interface Props { onScanCompleted: (scan: ScanRecord) => void; onViewReport: (scan: ScanRecord) => void }

export function ImageScanView({onScanCompleted,onViewReport}:Props) {
  const [file,setFile] = useState<File|null>(null);
  const [preview,setPreview] = useState('');
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState('');
  const [includeAttention,setIncludeAttention] = useState(true);
  useEffect(()=>{
    if(!file){setPreview('');return;}
    const url=URL.createObjectURL(file);setPreview(url);
    return ()=>URL.revokeObjectURL(url);
  },[file]);
  const select=(value?:File)=>{
    if(!value)return;
    setError('');
    if(!['image/jpeg','image/png','image/webp'].includes(value.type)){setError('Choose a JPEG, PNG or WebP image.');return;}
    if(value.size>10*1024*1024){setError('This image exceeds 10 MB. Choose a smaller original file.');return;}
    setFile(value);
  };
  async function analyze(){
    if(!file)return;
    if(!httpClient.getToken()){setError('Sign in using the button above before running an assessment.');return;}
    setBusy(true);setError('');
    try{
      const scan=await scanApi.uploadImageScan(file,includeAttention);
      onScanCompleted(scan);onViewReport(scan);
    }catch(e){setError(e instanceof Error?e.message:'Image assessment failed. Try again.');}
    finally{setBusy(false);}
  }
  return <section className="input-workspace" aria-labelledby="image-heading">
    <div className="input-heading"><h2 id="image-heading">Image assessment</h2><p>Separate origin clues, AI generation evidence and localized editing evidence.</p></div>
    <div className="upload-surface" onDragOver={e=>e.preventDefault()} onDrop={e=>{e.preventDefault();if(!busy)select(e.dataTransfer.files[0]);}}>
      {preview?<img className="upload-preview" src={preview} alt="Selected original image"/>:<Upload size={30} strokeWidth={1.4} aria-hidden="true"/>}
      <label className="file-picker">{file?'Replace image':'Choose an image'}<input type="file" accept="image/jpeg,image/png,image/webp" disabled={busy} onChange={e=>select(e.target.files?.[0])}/></label>
      <p>{file?`${file.name} · ${(file.size/1024).toFixed(0)} KB`:'Or drop a file here'}</p>
      <small>JPEG, PNG or WebP, up to 10 MB. The original upload bytes remain intact.</small>
    </div>
    <label className="attention-option"><input type="checkbox" checked={includeAttention} disabled={busy} onChange={e=>setIncludeAttention(e.target.checked)}/> Include model attention (Grad-CAM)</label>
    <p>Shows where the classifier found signal. This adds processing time and is separate from an edited-region mask.</p>
    {error&&<p role="alert" className="error-message">{error}</p>}
    <div className="input-actions"><p>Small or heavily compressed images may be inconclusive.</p><button className="primary-button" disabled={!file||busy} onClick={analyze}>{busy?'Examining image…':'Analyze image'}</button></div>
    {busy&&<p role="status" className="loading-message">Models are examining the original image. Pixel localization can take longer than a quick classification.</p>}
  </section>;
}
