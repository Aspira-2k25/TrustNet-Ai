import { useEffect, useRef, useState } from 'react';
import { httpClient } from '../../services/api/client';
import type { ScanRecord } from '../../types';

export interface InspectionSummary {
  observations: Array<{title: string; observed: string; why_it_matters: string; status: string}>;
  model_assessment: string;
  missing_checks: Array<{check: string; reason: string}>;
  live_checks_observed: number;
  live_checks_total: number;
  scope: string;
}

export interface SavedInspection {
  status: string;
  updated_at: string;
  reason?: string;
  summary?: InspectionSummary;
  result?: {risk_score: number; verdict?: string; status?: string};
}

export function LinkInspection({scanId, index, saved, onUpdated}: {
  scanId: string; index: number; saved?: SavedInspection; onUpdated: (scan: ScanRecord) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const active = useRef<AbortController | null>(null);
  useEffect(() => () => active.current?.abort(), [scanId]);
  const inspect = async () => {
    if (busy) return;
    const controller = new AbortController();
    active.current?.abort(); active.current = controller;
    setBusy(true); setError('');
    const timeout = window.setTimeout(() => controller.abort(), 45000);
    try {
      const response = await httpClient.request<{data: ScanRecord}>(
        `/api/v1/scans/${encodeURIComponent(scanId)}/links/${index}/inspection`,
        {method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}', signal: controller.signal},
      );
      if (response.data.id !== scanId || response.data.result?.module !== 'scam_message') throw new Error('Unexpected inspection response');
      onUpdated(response.data);
    } catch (reason) {
      if (active.current === controller) setError(controller.signal.aborted ? 'Inspection timed out or was cancelled. The quick assessment is unchanged.' : reason instanceof Error ? reason.message : 'Inspection unavailable');
    } finally {
      window.clearTimeout(timeout);
      if (active.current === controller) setBusy(false);
    }
  };
  const summary = saved?.summary;
  return <section className="mt-4 space-y-3 border-t border-slate-700 pt-4" aria-label="Detailed URL inspection">
    {saved?.status !== 'COMPLETED' && <>
      <button type="button" onClick={inspect} disabled={busy} className="rounded-lg bg-sky-700 px-4 py-2 text-white disabled:opacity-50">{busy ? 'Inspecting website...' : 'Inspect this URL'}</button>
      <p className="text-xs text-slate-600">On request, the backend contacts the URL destination for bounded DNS, HTTPS and static page checks. Scripts are not run and forms are not submitted.</p>
    </>}
    {error && <p role="alert" className="text-sm text-amber-900">{error}</p>}
    {saved && <>
      <p className="text-sm">Inspection: {saved.status.replaceAll('_', ' ')}. Snapshot: {new Date(saved.updated_at).toLocaleString()}.</p>
      {saved.reason && <p className="text-sm text-amber-900">{saved.reason}</p>}
      {summary && <>
        <p className="text-xs text-slate-600">{summary.scope} {summary.live_checks_observed}/{summary.live_checks_total} live checks returned observations.</p>
        {saved.result && ['SUCCESS', 'PARTIAL_SUCCESS'].includes(saved.result.status || '') && (
          <div className="flex items-center gap-2 p-2.5 rounded-lg border font-medium text-sm" style={{
            background: (saved.result.risk_score >= 50 || saved.result.verdict === 'SUSPICIOUS') ? 'rgba(239, 68, 68, 0.08)' : 'rgba(16, 185, 129, 0.08)',
            borderColor: (saved.result.risk_score >= 50 || saved.result.verdict === 'SUSPICIOUS') ? 'rgba(239, 68, 68, 0.3)' : 'rgba(16, 185, 129, 0.3)',
            color: (saved.result.risk_score >= 50 || saved.result.verdict === 'SUSPICIOUS') ? '#991b1b' : '#065f46'
          }}>
            <span>{(saved.result.risk_score >= 50 || saved.result.verdict === 'SUSPICIOUS') ? '⚠️ Phishing / Risky Website' : '✓ Safe / Legitimate Website'}</span>
            <span className="text-xs opacity-75">({saved.result.risk_score.toFixed(1)}/100 risk score — {saved.result.verdict?.replaceAll('_', ' ')})</span>
          </div>
        )}
        <h4 className="font-semibold">What we observed and why it matters</h4>
        <div className="grid gap-3 md:grid-cols-2">{summary.observations.map((item, i) => <article key={`${item.title}-${i}`} className={`rounded-lg border p-3 ${item.status === 'warning' ? 'border-amber-600' : 'border-slate-700'}`}>
          <h5 className="font-semibold">{item.title}</h5>
          <p className="mt-1 break-words text-sm">{item.observed}</p>
          <p className="mt-2 text-xs text-slate-600">Why it matters: {item.why_it_matters}</p>
        </article>)}</div>
        <div className="rounded-lg border border-violet-700 p-3"><h4 className="font-semibold">Model assessment</h4><p className="mt-1 text-sm">{summary.model_assessment}</p></div>
        <div className="rounded-lg border border-slate-700 p-3"><h4 className="font-semibold">What we could not check</h4>{summary.missing_checks.map(item => <p key={item.check} className="mt-1 text-sm text-slate-700">{item.check.replaceAll('_', ' ')}: {item.reason}</p>)}</div>
      </>}
    </>}
  </section>;
}
