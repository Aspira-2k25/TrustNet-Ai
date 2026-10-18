import type { ScanRecord } from '../../types';
import { codePoint, domainDifference, reportOpinion, urlReportSummary } from './reportInsights';

const percent = (value: unknown) => typeof value === 'number' && Number.isFinite(value) ? `${(value * 100).toFixed(1)}%` : 'Unavailable';
const labels: Record<string, string> = {
  VISUAL_DOMAIN_IMPERSONATION: 'Lookalike destination', MISLEADING_AUTHORITY: 'Disguised destination',
  REPUTATION_MATCH: 'Reported phishing URL', PASSWORD_HTTP: 'Unencrypted password submission',
  PASSWORD_EXTERNAL: 'Password sent to another domain', CROSS_DOMAIN_REDIRECT: 'Destination changed',
  TLS_VALIDATION_FAILED: 'Certificate verification failed', EMBEDDED_DOMAIN: 'Domain hidden in a subdomain',
};

export function PhishingAnalysis({ scan }: { scan: ScanRecord }) {
  const result = scan.result;
  const meta = result?.metadata || {};
  const forensic = meta.forensics || {};
  const signals = forensic.network?.signals || {};
  const findings: Array<{ code: string; severity: string; reason: string }> = forensic.findings || [];
  const components = meta.score_components || {};
  const diagnostic = meta.diagnostic_model || {};
  const model = components.model_probability;
  const current = meta.assessment_policy === 'dynamic-v2' && meta.link_analysis_version === 'links-v1';
  const assessed = current && !!result && ['SUCCESS', 'PARTIAL_SUCCESS'].includes(result.status);
  const suspicious = assessed && result?.verdict === 'SUSPICIOUS';
  const low = assessed && result?.verdict === 'NO_STRONG_INDICATORS';
  const color = suspicious ? 'border-rose-400/50 bg-rose-950/30 text-rose-100' : low ? 'border-emerald-400/50 bg-emerald-950/30 text-emerald-100' : 'border-amber-400/50 bg-amber-950/30 text-amber-100';
  const observed = Object.values(signals).filter((v) => (v as { status?: string }).status?.toLowerCase() === 'observed').length;
  const checks = ['dns', 'tls', 'http', 'html', 'registration', 'reputation'];
  const available = checks.filter(name => signals[name]?.status?.toLowerCase() === 'observed').length;
  const opinion = reportOpinion(scan);
  const summary = urlReportSummary(scan);
  const match = forensic.visual_domain_match;
  const differences = match ? domainDifference(String(match.actual_domain || ''), String(match.resembles_domain || '')) : [];
  const reputation = signals.reputation;
  let parsed: URL | undefined;
  try { parsed = new URL(meta.assessed_url || scan.raw_input || ''); } catch { /* Invalid and bare inputs use recorded hostname below. */ }
  const part = (code: string) => {
    if (code === 'VISUAL_DOMAIN_IMPERSONATION') return forensic.visual_domain_match?.observed_url || forensic.visual_domain_match?.actual_domain || forensic.registered_domain;
    if (['PATH_TRAVERSAL', 'DOUBLE_ENCODED_PATH', 'ENCODING', 'NAVIGATION_PARAMETER'].includes(code)) return forensic.path_analysis?.path || parsed?.pathname;
    if (code.startsWith('PASSWORD')) return (signals.html?.password_forms || []).map((f: { action?: string }) => f.action || '(current page)').join(', ');
    if (['CROSS_DOMAIN_REDIRECT', 'HTTPS_DOWNGRADE', 'MULTI_DOMAIN_NAVIGATION'].includes(code)) return signals.http?.final_url || 'See recorded navigation hops';
    if (code.startsWith('REPUTATION')) return signals.reputation?.match_scope === 'redirect_destination' ? signals.http?.final_url : meta.assessed_url;
    return forensic.hostname || parsed?.hostname;
  };
  return <div className="space-y-5">
    <div className={`rounded-2xl border p-6 ${color}`} role="status">
      <p className="text-xs font-semibold uppercase tracking-wider">URL detection verdict</p>
      <h2 className="mt-2 text-2xl font-bold">{suspicious ? 'Suspected phishing — avoid interacting' : low ? 'Likely legitimate — low phishing risk' : assessed ? 'Uncertain — review before proceeding' : 'Not enough evidence for a verdict'}</h2>
      <p className="mt-3 text-sm">{suspicious ? 'The model or strong forensic evidence triggered a phishing alert. Do not enter passwords or payment information until you verify the destination independently.' : low ? 'The URL model did not trigger an alert and the implemented forensic rules found no strong warning. Authenticity and ownership have not been verified.' : 'The available checks cannot confidently establish whether this destination is legitimate. Verify it through an independent source.'}</p>
      <p className="mt-3 text-xs">{available}/6 core live checks returned observations. {summary.confidenceReason}</p>
      <div className="mt-3 flex gap-1" aria-label={`${available} of 6 core checks observed`}>{checks.map(name => <span key={name} title={`${name}: ${signals[name]?.status || 'not collected'}`} className={`h-2 flex-1 rounded ${signals[name]?.status?.toLowerCase() === 'observed' ? 'bg-sky-400' : 'bg-slate-600'}`} />)}</div>
      <div className="mt-4 rounded-xl border border-current/20 p-4"><p className={`font-bold ${opinion.tone === 'positive' ? 'text-emerald-200' : opinion.tone === 'danger' ? 'text-rose-200' : 'text-amber-200'}`}>{opinion.title}</p><p className="text-sm mt-2">{opinion.reason}</p><p className="text-xs mt-2 opacity-75">A qualitative reading of the same evidence; it does not replace the verdict or add a second model vote.</p></div>
    </div>
    <section className="rounded-2xl border border-slate-700 bg-[#0b132b] p-6 space-y-4">
      <h2 className="text-xl font-bold">What we found for this URL</h2>
      <p className="text-sm text-slate-400">Each finding below describes this scan’s recorded evidence, including checks we could not complete.</p>
      <div className="grid md:grid-cols-2 gap-3">{summary.cards.map(card => <article key={card.title} className={`rounded-xl border-l-4 bg-slate-900 p-4 ${card.tone === 'warn' ? 'border-rose-400' : card.tone === 'good' ? 'border-emerald-400' : card.tone === 'missing' ? 'border-amber-400' : 'border-sky-400'}`}><h3 className="font-semibold">{card.title}</h3><p className="text-sm text-slate-300 mt-2 break-words">{card.text}</p></article>)}</div>
      <div className="rounded-xl border border-violet-400/30 bg-violet-950/20 p-4"><h3 className="font-semibold">What the model found</h3><p className="text-sm mt-2">{summary.modelText}</p></div>
      <div className="rounded-xl bg-slate-900 p-4"><h3 className="font-bold">Our conclusion for {forensic.hostname || 'this link'}</h3><p className="mt-2 text-sm">{opinion.title}. {opinion.reason}</p>{findings.filter(f=>f.severity !== 'info').slice(0,3).map((f,i)=><p key={i} className="text-sm text-slate-300 mt-2">{f.reason}</p>)}<p className="mt-3 text-sm font-semibold text-sky-200">{suspicious ? 'Recommended action: do not enter credentials or make payments through this link.' : low ? 'Recommended action: check that this is the domain you intended, especially before signing in or paying.' : 'Recommended action: use the organization’s independently verified website rather than this link until the concerns are resolved.'}</p></div>
    </section>
    {reputation && <section className={`rounded-2xl border p-6 space-y-3 ${reputation.status?.toLowerCase() === 'observed' && reputation.fresh_match ? 'border-rose-400/50 bg-rose-950/30' : 'border-slate-700 bg-[#0b132b]'}`}>
      <h2 className="text-lg font-bold">Threat intelligence · {reputation.provider || 'Provider'}</h2>
      <p className="font-semibold">{reputation.status?.toLowerCase() !== 'observed' ? 'Provider check unavailable' : reputation.fresh_match ? 'Known reported phishing — recent exact URL match' : reputation.matched ? 'Historical report — current threat not established' : 'No exact URL report found'}</p>
      <p className="text-sm text-slate-300">{reputation.fresh_match ? 'A recent provider report met the configured freshness and score requirements. Avoid this URL. This is a provider-backed detection, not a claim of infallibility.' : 'An absent match does not authenticate the site. New phishing pages and unreported campaigns may not appear in a feed.'}</p>
      <p className="text-xs text-slate-400">Scope: {reputation.match_scope === 'redirect_destination' ? 'Observed redirect destination' : 'Submitted exact URL'} · Checked: {reputation.checked_at || 'Not recorded'} · {reputation.cached ? 'Cached provider response (up to 90 minutes)' : 'Provider response'}</p>
      {reputation.reason && <p className="text-sm">{reputation.reason}</p>}
      {(reputation.reports || []).map((report: {id?: number; reported_at?: string; provider_score?: number}, i: number) => <div key={i} className="rounded-xl bg-slate-900 p-3 text-sm">Report ID: {report.id ?? 'Not recorded'} · Reported: {report.reported_at || 'Unknown'} · Provider score: {report.provider_score ?? 'Unknown'}</div>)}
      {reputation.search_may_be_truncated && <p className="text-xs text-amber-200">The provider result limit was reached; the lookup may not include every report.</p>}
    </section>}
    <section className="rounded-2xl border border-slate-700 bg-[#0b132b] p-6 space-y-4">
      <h2 className="text-lg font-bold">Where the evidence points</h2>
      <p className="text-sm text-slate-400">These are recorded observations, not proof of malicious ownership. Addresses below are displayed as text and are not opened.</p>
      <dl className="grid gap-3 sm:grid-cols-2 text-sm">
        {Object.entries({ 'Submitted address': meta.original_input || scan.raw_input, 'Actual hostname': forensic.hostname, 'Registered domain': forensic.registered_domain, 'Inspected path': forensic.path_analysis?.path, 'Final observed destination': signals.http?.final_url }).map(([name, value]) => <div key={name} className="rounded-xl bg-slate-900 p-3"><dt className="text-slate-400">{name}</dt><dd className="mt-1 font-mono break-all">{String(value || 'Not established')}</dd></div>)}
      </dl>
      {forensic.visual_domain_match && <div className="rounded-xl border border-rose-400/40 p-4"><p className="font-bold text-rose-200">Different domain, similar appearance</p><p className="mt-2 font-mono break-all"><mark className="bg-rose-900 text-rose-100 px-1">{forensic.visual_domain_match.actual_domain}</mark> → resembles <span className="text-sky-200">{forensic.visual_domain_match.resembles_domain}</span></p><p className="text-sm text-slate-400 mt-2">{forensic.visual_domain_match.method}</p></div>}
      {differences.length > 0 && <div className="rounded-xl bg-slate-900 p-4 space-y-4">
        <h3 className="font-bold">Character-by-character domain comparison</h3>
        <p className="text-xs text-slate-400">Highlighted characters differ. Positions count from 1 in the recorded canonical domain; ∅ marks an insertion or missing character.</p>
        <div className="overflow-x-auto pb-2"><div className="flex w-max gap-1">{differences.map((cell, i) => <div key={i} className={`flex flex-col items-center gap-2 rounded p-2 font-mono ${cell.changed ? 'bg-rose-950 border border-rose-400 text-rose-100' : 'bg-slate-800 text-slate-400'}`}><span title="Actual destination">{cell.actual || '∅'}</span><span className="text-xs">↓</span><span title="Reference domain">{cell.reference || '∅'}</span></div>)}</div></div>
        <p className="text-xs text-slate-400">Top: actual destination · Bottom: similar reference domain. The reference is a comparison candidate, not verified ownership or affiliation.</p>
        {differences.filter(cell => cell.changed).map((cell, i) => <p key={i} className="text-sm">At destination position {cell.actualPosition}: {cell.actual && cell.reference ? `“${cell.actual}” (${codePoint(cell.actual)}) appears instead of “${cell.reference}” (${codePoint(cell.reference)}).` : cell.actual ? `extra “${cell.actual}” (${codePoint(cell.actual)}).` : `reference character “${cell.reference}” (${codePoint(cell.reference)}) is missing.`}</p>)}
        <p className="text-sm text-amber-100">Why it matters: visually similar spelling can direct you to a different registered domain. This supports an impersonation warning; the changed letters alone do not prove malicious content.</p>
      </div>}
      {findings.length === 0 ? <p className="text-sm text-slate-300">No forensic warning was recorded by the implemented rules. This is an absence of detected indicators, not a safety certificate.</p> : findings.map((finding, i) => <article key={`${finding.code}-${i}`} className={`rounded-xl border-l-4 bg-slate-900 p-4 ${finding.severity === 'high' ? 'border-rose-400' : finding.severity === 'medium' ? 'border-amber-400' : 'border-sky-400'}`}>
        <div className="flex flex-wrap gap-2 items-center"><h3 className="font-semibold">{labels[finding.code] || finding.code.toLowerCase().replaceAll('_', ' ')}</h3><span className="text-xs uppercase text-slate-400">{finding.severity === 'info' ? 'Context only' : `${finding.severity} concern`}</span></div>
        <p className="text-sm mt-2">{finding.reason}</p>
        {part(finding.code) && <p className="text-xs mt-3 text-slate-400">Relevant location: <code className="text-slate-200 break-all">{part(finding.code)}</code></p>}
        <p className="text-xs mt-2 text-slate-400">Rule: {finding.code} · {components.evidence_updates?.some((u: { code: string }) => u.code === finding.code) ? 'Included in the combined risk index' : 'Reported as context; no direct policy weight applied'}</p>
      </article>)}
    </section>
    <details className="rounded-2xl border border-slate-700 bg-[#0b132b] p-6 space-y-4">
      <summary className="cursor-pointer font-bold">Advanced model diagnostics and measured inputs</summary>
      <div className="grid sm:grid-cols-3 gap-3">{[['URL structure', meta.branch_probabilities?.structural], ['URL text patterns', meta.branch_probabilities?.url_text], [meta.configuration === 'regional_v1' ? 'Selected URL expert' : 'Calibrated ensemble', model]].map(([name, value]) => <div key={String(name)} className="rounded-xl bg-slate-900 p-3"><p className="text-sm text-slate-400">{name}</p><p className="text-xl font-bold mt-1">{percent(value)}</p><div className="h-2 rounded bg-slate-700 mt-2 overflow-hidden"><div className="h-full bg-violet-400" style={{ width: typeof value === 'number' ? `${Math.max(0, Math.min(100, value * 100))}%` : '0%' }} /></div></div>)}</div>
      <p className="text-xs text-slate-400">Branch values are diagnostic estimates, not independent votes or final confidence. Exact character-level model attribution is unavailable; an observed URL feature does not establish what caused the learned prediction.</p>
      <details className="text-sm space-y-3"><summary className="cursor-pointer font-semibold text-sky-200">Inspect model inputs and score calculation</summary>
        <p className="mt-3">Model: {result?.model_version || 'Unavailable'} · Original model label: {diagnostic.label || 'Unavailable'} · Alert threshold: {percent(meta.threshold)}.</p>
        {meta.configuration === 'regional_v1' && <p>URL shape: {String(meta.url_region || 'Unavailable')} · Selected expert: {String(meta.selected_expert || 'Unavailable')}. The alert boundary is selected for this URL shape. Routed-system probability calibration has not been established.</p>}
        <p>Model alert: {typeof model === 'number' && typeof meta.threshold === 'number' ? model >= meta.threshold ? 'Threshold crossed' : 'Below threshold' : 'Not available'}. Strong forensic findings can independently trigger the alert.</p>
        <p className="font-mono break-all">{components.formula || 'No combined score calculation recorded.'}</p>
        <p>Evidence weights are policy settings, not measured likelihoods. Combined calibration validated: {components.combined_calibration_validated === true ? 'Yes' : 'No'}.</p>
        {(components.evidence_updates || []).map((u: { code: string; policy_weight: number }) => <p key={u.code}>{u.code}: weight {u.policy_weight}</p>)}
        <div className="overflow-x-auto"><table className="w-full text-left text-xs"><caption className="text-left py-2 text-slate-400">Observed structural inputs — measurements, not causal attributions</caption><thead><tr><th className="p-2">Feature</th><th className="p-2">Value</th></tr></thead><tbody>{Object.entries(meta.structural_features || {}).map(([name, value]) => <tr key={name} className="border-t border-slate-700"><td className="p-2 font-mono">{name}</td><td className="p-2">{String(value)}</td></tr>)}</tbody></table></div>
      </details>
      <p className="text-xs text-slate-400">{observed ? `Evidence recorded at ${forensic.network?.observed_at || result?.timestamp || scan.created_at}.` : 'No live evidence was observed.'} Static inspection does not execute JavaScript or establish website ownership.</p>
    </details>
  </div>;
}
