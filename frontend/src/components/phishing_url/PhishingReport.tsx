import { useResultLanguage } from '../../services/resultLanguage.ts';
import { ResultSummary } from '../results/ResultSummary';
import type { ScanRecord } from '../../types';
import { exportForensicPDFReport } from '../../services/pdfExporter';
import { PhishingAnalysis } from './PhishingAnalysis';

export function PhishingReport({scan,onBack}:{scan:ScanRecord;onBack:()=>void}) {
  const {t}=useResultLanguage();
  const url=scan.result?.metadata?.assessed_url||scan.raw_input||'';
  return <section className="max-w-5xl mx-auto p-6 space-y-5">
    <button onClick={onBack} className="secondary-button">{t('Back to history','History par wapas')}</button>
    <ResultSummary scan={scan}><PhishingAnalysis scan={scan}/></ResultSummary>
    <p className="break-all font-mono">{url}</p>
    <button onClick={()=>exportForensicPDFReport(scan)} className="primary-button">{t('Download report','Report download karein')}</button>
  </section>;
}
