import type { ScanRecord } from '../../types';

/** A presentation opinion, never a new detector verdict or probability. */
export function reportOpinion(scan: ScanRecord) {
  const meta = scan.result?.metadata || {};
  const findings: Array<{severity: string}> = meta.forensics?.findings || [];
  const signals = meta.forensics?.network?.signals || {};
  const model = meta.score_components?.model_probability;
  const threshold = meta.threshold;
  const current = meta.assessment_policy === 'dynamic-v2' && meta.link_analysis_version === 'links-v1';
  if (!current || !scan.result || !['SUCCESS', 'PARTIAL_SUCCESS'].includes(scan.result.status))
    return { title: 'No defensible leaning yet', reason: 'Too little usable evidence is available. An unavailable check is not evidence that a link is safe.', tone: 'neutral' };
  if (findings.some(f => f.severity === 'high') || (typeof model === 'number' && typeof threshold === 'number' && model >= threshold))
    return { title: 'Our assessment leans phishing', reason: 'A strong forensic indicator or the model alert threshold supports avoiding this destination. This is an evidence-based warning, not proof of the operator’s intent.', tone: 'danger' };
  const medium = findings.filter(f => f.severity === 'medium').length;
  const live = ['dns', 'tls', 'http', 'html', 'registration', 'reputation'].filter(k => signals[k]?.status?.toLowerCase() === 'observed').length;
  if (typeof model === 'number' && typeof threshold === 'number' && threshold > 0 && model < threshold / 2 && medium === 0 && live >= 3)
    return { title: 'Our assessment leans legitimate', reason: 'The model estimate is well below its alert threshold, no medium or strong forensic warning was recorded, and several live checks were observed. This does not authenticate the site.', tone: 'positive' };
  if (medium > 0)
    return { title: 'Our assessment leans suspicious', reason: `${medium} forensic concern${medium === 1 ? '' : 's'} need review even though the model did not trigger a phishing alert. Treat the link cautiously; these indicators can also occur on legitimate sites.`, tone: 'caution' };
  if (typeof model !== 'number' || !Number.isFinite(model) || typeof threshold !== 'number' || !Number.isFinite(threshold))
    return { title: 'No defensible leaning yet', reason: 'A usable model estimate and sufficient decisive forensic evidence are unavailable. We cannot responsibly infer authenticity.', tone: 'neutral' };
  if (Math.abs(model-threshold) <= 0.05)
    return { title: 'Borderline — authenticity remains uncertain', reason: 'The estimate is very close to the model alert boundary. Being just below it is not strong evidence that the URL is legitimate; verify the destination before interacting.', tone: 'neutral' };
  return { title: 'Weak leaning toward legitimate URL patterns', reason: 'The model is below its alert threshold and no strong forensic indicator was recorded, but limited evidence or a borderline estimate prevents a confident recommendation.', tone: 'neutral' };
}

/** Edit alignment preserves insertions/deletions and Unicode code points. */
export function domainDifference(actual: string, reference: string) {
  const a = Array.from(actual), b = Array.from(reference);
  // Recorded domains are bounded; refuse oversized untrusted report values.
  if (a.length > 253 || b.length > 253) return [];
  const d = Array.from({length: a.length + 1}, () => Array<number>(b.length + 1).fill(0));
  for (let i = 0; i <= a.length; i++) d[i][0] = i;
  for (let j = 0; j <= b.length; j++) d[0][j] = j;
  for (let i = 1; i <= a.length; i++) for (let j = 1; j <= b.length; j++)
    d[i][j] = Math.min(d[i-1][j]+1, d[i][j-1]+1, d[i-1][j-1]+(a[i-1] === b[j-1] ? 0 : 1));
  const rows: Array<{actual: string; reference: string; changed: boolean; actualPosition: number}> = [];
  let i = a.length, j = b.length;
  while (i || j) {
    if (i && j && d[i][j] === d[i-1][j-1] + (a[i-1] === b[j-1] ? 0 : 1)) {
      rows.push({actual:a[i-1], reference:b[j-1], changed:a[i-1] !== b[j-1], actualPosition:i}); i--; j--;
    } else if (i && d[i][j] === d[i-1][j]+1) {
      rows.push({actual:a[i-1], reference:'', changed:true, actualPosition:i}); i--;
    } else { rows.push({actual:'', reference:b[j-1], changed:true, actualPosition:i+1}); j--; }
  }
  return rows.reverse();
}

export const codePoint = (char: string) => char ? `U+${char.codePointAt(0)!.toString(16).toUpperCase().padStart(4,'0')}` : 'absent';

export function urlReportSummary(scan: ScanRecord) {
  const meta = scan.result?.metadata || {}, f = meta.forensics || {}, s = f.network?.signals || {};
  const observed = (name: string) => s[name]?.status?.toLowerCase() === 'observed';
  const current = meta.assessment_policy === 'dynamic-v2' && meta.link_analysis_version === 'links-v1';
  const assessed = current && ['SUCCESS','PARTIAL_SUCCESS'].includes(scan.result?.status || '');
  const raw = scan.trust_score?.trust_risk_score ?? scan.result?.risk_score;
  const risk = assessed && typeof raw === 'number' && Number.isFinite(raw) ? Math.min(100,Math.max(0,raw)) : null;
  const trust = risk === null ? null : Math.round((100-risk)*10)/10;
  const branches = meta.branch_probabilities || {};
  const disagree = typeof branches.structural === 'number' && typeof branches.url_text === 'number' && Math.abs(branches.structural-branches.url_text) >= 0.4;
  const p = meta.score_components?.model_probability, threshold = meta.threshold;
  const borderline = typeof p === 'number' && typeof threshold === 'number' && Math.abs(p-threshold) <= 0.05;
  const coverage = ['dns','tls','http','html','registration','reputation'].filter(observed).length;
  const reported = observed('reputation') && s.reputation.fresh_match === true;
  const confidence = !assessed ? 'Unavailable' : reported ? 'Strong supporting evidence' : disagree || borderline || coverage < 4 ? 'Limited' : 'Moderate';
  const confidenceReason = !assessed ? 'This check did not produce a reliable assessment.' : reported ? 'A recent exact-URL phishing report supports the warning. Provider reports can still contain errors.' : disagree ? 'The URL text and structure models disagree substantially, so the prediction needs caution.' : borderline ? 'The model estimate is close to the alert boundary; a small change could change its label.' : coverage < 4 ? `Only ${coverage} of 6 core live checks returned observations.` : 'Several live checks returned observations and the model is not near its alert boundary.';
  const cards: Array<{title:string; text:string; tone:'neutral'|'good'|'warn'|'missing'}> = [];
  const add = (title:string,text:string,tone:'neutral'|'good'|'warn'|'missing'='neutral') => cards.push({title,text,tone});
  try {
    const address = new URL(meta.assessed_url || scan.raw_input || '');
    add('Address structure',`The link uses ${address.protocol.replace(':','').toUpperCase()}${address.port ? ` on port ${address.port}` : ''}. ${address.username ? 'It contains login text before @; that text is not the destination hostname.' : 'No login text before @ was present.'} ${address.search ? `Its query has ${Array.from(address.searchParams).length} parameter(s), inspected locally for recognized navigation targets.` : 'No query parameters were present.'} ${address.hash ? 'A fragment is present; it is not sent in the HTTP request.' : 'No fragment was present.'}`);
  } catch { add('Address structure','A complete web address could not be parsed; see the recorded input-handling details.','missing'); }
  add('Destination identity',f.hostname ? `This link targets ${f.hostname}. ${f.registered_domain ? `Its registered domain is ${f.registered_domain}.` : 'A registered domain boundary could not be established.'} ${f.visual_domain_match ? `It resembles ${f.visual_domain_match.resembles_domain}, but these are different domains.` : 'No lookalike-domain match was recorded by the implemented comparison.'}` : 'No website hostname was established for this input.',f.visual_domain_match?'warn':'neutral');
  const path = f.path_analysis;
  add('Path and hidden destinations',path?.path ? `We inspected “${path.path}” (${path.segments ?? 0} path segments). ${path.dot_segments ? 'Dot segments can obscure the route.' : 'No dot-segment navigation pattern was recorded.'} ${path.double_encoding ? 'The path changes when decoded twice.' : ''} ${(path.navigation_parameters || []).length ? `Navigation parameters reference: ${path.navigation_parameters.map((t:{parameter:string;hostname:string})=>`${t.parameter} → ${t.hostname}`).join('; ')}. These targets were not followed.` : 'No recognized parameter naming another website was recorded.'}` : 'No web-path analysis was available for this link.',path?.dot_segments?'warn':'neutral');
  add('DNS lookup',observed('dns') ? `The hostname resolved to ${(s.dns.addresses || []).join(', ') || 'a recorded public address'}. DNS resolution establishes reachability, not ownership.` : `We could not resolve and validate public destination addresses. ${s.dns?.reason || 'No DNS observation was recorded.'}`,observed('dns')?'neutral':'missing');
  const tls = s.tls || {}, cert = tls.analysis;
  const validated = observed('tls') && tls.validated !== false && !!tls.certificate;
  add('Connection security',tls.validated === false ? `Certificate verification failed. ${tls.reason || ''} We did not retry over an insecure connection.` : validated ? `An HTTPS certificate was validated for the destination. ${cert?.issuer ? `Issuer: ${cert.issuer}.` : ''} ${cert?.not_after ? `Expires: ${cert.not_after}.` : ''} Encryption does not verify that the business or page is legitimate.` : 'No verified HTTPS certificate was recorded. This check cannot establish transport security.',tls.validated===false?'warn':validated?'good':'missing');
  add('Page and redirects',observed('http') ? `The server returned HTTP ${s.http.status_code}. We observed ${s.http.redirects ?? 0} redirect(s); the final destination was ${s.http.final_url || 'not recorded'}. ${s.http.status_code >= 400 ? 'The returned page was an error response, which limits content assessment.' : 'A page response alone does not establish safety.'}` : `We could not inspect a final page response. ${s.http?.reason || 'The live page check was unavailable.'}`,observed('http')?'neutral':'missing');
  const forms = s.html?.password_forms;
  add('Password collection',observed('html') && Array.isArray(forms) ? forms.length ? `The inspected HTML contains ${forms.length} password form(s). Recorded submission destination(s): ${forms.map((form:{action:string})=>form.action).join('; ')}. See warning findings for any insecure or cross-domain submission.` : 'No password form was found in the inspected HTML. JavaScript-generated forms were not checked.' : 'Password forms could not be assessed from HTML. No absence-of-form conclusion was made.',observed('html') && Array.isArray(forms)?'neutral':'missing');
  if (s.html?.truncated) add('Page inspection limit','The HTML response was truncated at the collection limit; additional content may not have been inspected.','missing');
  add('Domain history',f.network?.domain_age_days != null ? `The recorded registration age is ${f.network.domain_age_days} days${s.registration?.registration_date ? ` (registered ${s.registration.registration_date})` : ''}. Age alone does not prove legitimacy.` : `Domain registration age was not established. ${s.registration?.reason || ''}`,f.network?.domain_age_days != null?'neutral':'missing');
  add('Known phishing reports',observed('reputation') ? reported ? `${s.reputation.provider || 'The provider'} returned a recent qualifying report for ${s.reputation.match_scope === 'redirect_destination' ? 'the observed redirect destination' : 'this exact URL'}. Avoid this destination.` : s.reputation.matched ? 'A historical report exists, but it did not meet the current alert requirements.' : `${s.reputation.provider || 'The provider'} returned no exact URL match in this lookup. This does not clear the URL as safe.` : `The threat-source lookup was unavailable. ${s.reputation?.reason || 'No current reputation evidence was recorded.'}`,reported?'warn':observed('reputation')?'neutral':'missing');
  const rescueText = meta.rescue_applied === true && typeof meta.primary_model_probability === 'number' && typeof meta.primary_model_threshold === 'number' ? `The first URL expert was below its alert boundary (${(meta.primary_model_probability*100).toFixed(1)} versus ${(meta.primary_model_threshold*100).toFixed(1)}). A second expert crossed its stricter warning boundary, so the additional check triggered this alert. These estimates are not prediction-confidence percentages.` : '';
  const modelText = typeof p !== 'number' || typeof threshold !== 'number' ? 'No usable website-model estimate was available for this link.' : `For this URL, the selected model estimate was ${(p*100).toFixed(1)} against an alert boundary of ${(threshold*100).toFixed(1)}. ${borderline ? 'This is a borderline result, not a clear legitimate classification.' : p >= threshold ? 'It triggered the model’s phishing alert.' : 'It did not trigger the model alert.'} ${disagree ? 'The text pattern appears suspicious to one branch while the structure appears less suspicious to the other; this disagreement lowers confidence.' : ''} ${rescueText} The model cannot identify an exact malicious character or verify ownership.`;
  return {risk,trust,confidence,confidenceReason,cards,modelText,disagree,borderline,coverage};
}
