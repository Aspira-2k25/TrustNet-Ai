import { useResultLanguage } from '../../services/resultLanguage.ts';
import { useEffect, useState } from 'react';
import { Upload } from 'lucide-react';
import type { ScanRecord } from '../../types';
import { scanApi } from '../../services/api/scan.api';
import { httpClient } from '../../services/api/client';

interface Props { onScanCompleted: (scan: ScanRecord) => void; onViewReport: (scan: ScanRecord) => void }

export function ImageScanView({onScanCompleted,onViewReport}:Props) {
  const {t}=useResultLanguage();
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
  useEffect(()=>{
    const handlePaste=(e:ClipboardEvent)=>{
      if(busy)return;
      const items=e.clipboardData?.items;
      if(!items)return;
      for(let i=0;i<items.length;i++){
        if(items[i].type.startsWith('image/')){
          const pasted=items[i].getAsFile();
          if(pasted){select(pasted);break;}
        }
      }
    };
    window.addEventListener('paste',handlePaste);
    return ()=>window.removeEventListener('paste',handlePaste);
  },[busy]);
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
    <div className="input-heading"><h2 id="image-heading">{t('Check an image','Image check karein')}</h2><p>{t('Look for signs of AI generation and editing. Some changes can be missed.','AI aur editing ke sanket dekhein. Kuch edits miss ho sakte hain.')}</p></div>
    <div className="upload-surface" onDragOver={e=>e.preventDefault()} onDrop={e=>{e.preventDefault();if(!busy)select(e.dataTransfer.files[0]);}}>
      {preview?<img className="upload-preview" src={preview} alt="Selected original image"/>:<Upload size={30} strokeWidth={1.4} aria-hidden="true"/>}
      <label className="file-picker">{file?'Replace image':'Choose an image'}<input type="file" accept="image/jpeg,image/png,image/webp" disabled={busy} onChange={e=>select(e.target.files?.[0])}/></label>
      <p>{file?`${file.name} · ${(file.size/1024).toFixed(0)} KB`:'Or drop a file here'}</p>
      <small>JPEG, PNG or WebP, up to 10 MB. The original upload bytes remain intact.</small>
    </div>
    <label className="attention-option"><input type="checkbox" checked={includeAttention} disabled={busy} onChange={e=>setIncludeAttention(e.target.checked)}/> {t('Show where the model looked','Model ne kahan dekha dikhayein')}</label>
    <p>{t('Where the model looked (not where the edit is). This can add a few seconds.','Model ne kahan dekha (yeh edit ki jagah nahi hai). Ismein kuch seconds aur lag sakte hain.')}</p>
    {error&&<p role="alert" className="error-message">{error}</p>}
    <div className="input-actions"><p>{t('Small or heavily compressed images may not give a clear answer.','Chhoti ya compressed image se saaf jawab nahi mil sakta.')}</p><button className="primary-button" disabled={!file||busy} onClick={analyze}>{busy?'Examining image…':'Analyze image'}</button></div>
    {busy&&<p role="status" className="loading-message">{t('Checking the original image for AI and editing signs. A check that cannot finish will be shown as incomplete.','Original image mein AI aur editing ke sanket check ho rahe hain. Adhura check saaf bataya jayega.')}</p>}
  </section>;
}
