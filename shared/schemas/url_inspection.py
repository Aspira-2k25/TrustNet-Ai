"""Plain-language evidence shared by the website, extension and PDF report."""
import math


def _mapping(value):
    return value if isinstance(value, dict) else {}


def inspection_summary(result):
    meta = _mapping(result.metadata)
    forensic = _mapping(meta.get('forensics'))
    network = _mapping(forensic.get('network'))
    signals = _mapping(network.get('signals'))
    observations, missing = [], []

    def add(title, observed, meaning, status='observed'):
        observations.append(dict(title=title, observed=observed, why_it_matters=meaning, status=status))

    def observed(name):
        signal = _mapping(signals.get(name))
        if str(signal.get('status', '')).lower() == 'observed':
            return signal
        missing.append(dict(check=name, reason=str(signal.get('reason') or 'No usable observation was returned.')[:500]))
        return None

    host = forensic.get('hostname')
    if host:
        add('Destination domain', f"Hostname: {host}. Registered domain: {forensic.get('registered_domain') or 'not established'}.",
            'The destination hostname identifies where the request goes. A familiar name elsewhere in the URL does not establish ownership.')
    else:
        missing.append(dict(check='domain', reason='A website hostname was not established.'))
    dns = observed('dns')
    if dns:
        add('Public IP addresses', ', '.join(str(v) for v in dns.get('addresses', [])[:32]) or 'DNS returned no recorded addresses.',
            'DNS maps the domain to network addresses. A shared hosting address does not prove phishing or identify the site owner.')
    tls = observed('tls')
    if tls:
        cert = _mapping(tls.get('analysis'))
        failed = tls.get('validated') is False
        detail = (f"Certificate validation failed. {tls.get('reason', '')}" if failed else
                  f"HTTPS certificate validated. Issuer: {cert.get('issuer') or 'not recorded'}. Expiry: {cert.get('not_after') or 'not recorded'}." if tls.get('certificate') else
                  'A TLS observation was returned, but a valid certificate was not established.')
        add('HTTPS and certificate', detail, 'A valid certificate protects transport, not business legitimacy. A failed validation is a connection warning.', 'warning' if failed else 'observed')
    http = observed('http')
    if http:
        add('Page response and redirects', f"HTTP {http.get('status_code', 'unknown')}. Redirects: {http.get('redirects', 0)}. Final URL: {http.get('final_url') or 'not recorded'}.",
            'Redirects can change the destination. Receiving a page, including an error page, does not establish that it is legitimate.')
    html = observed('html')
    if html:
        forms = html.get('password_forms')
        if isinstance(forms, list):
            detail = ('Password form destinations: ' + '; '.join(str(_mapping(f).get('action', 'not recorded')) for f in forms[:20]) if forms else
                      'No password form was found in the inspected static HTML.')
        else:
            detail = 'A response was collected, but password forms could not be assessed as HTML.'
        add('Page forms', detail, 'A form that sends a password to another domain or over HTTP needs attention. A password form alone is normal on many legitimate sites.')
        if html.get('truncated'):
            missing.append(dict(check='complete_html', reason='Only the bounded first part of the response was inspected.'))
    registration = observed('registration')
    if registration:
        add('Domain registration', f"Registration date: {registration.get('registration_date') or 'not recorded'}. Age in days: {network.get('domain_age_days') if network.get('domain_age_days') is not None else 'not established'}.",
            'Domain history provides context. A new domain is not automatically fraudulent, and an old domain is not automatically safe.')
    reputation = observed('reputation')
    if reputation:
        add('Threat reports', 'A recent qualifying exact URL report was returned.' if reputation.get('fresh_match') else
            'A historical report was returned.' if reputation.get('matched') else 'No exact URL report was returned by this lookup.',
            'A recent report supports a warning. No report does not establish safety, and provider reports may contain errors.')
    for finding in (forensic.get('findings') or [])[:30]:
        finding = _mapping(finding)
        if finding.get('severity') in ('medium', 'high'):
            add(str(finding.get('code', 'Recorded warning')).replace('_', ' ').title(), str(finding.get('reason', ''))[:1500],
                'This is a recorded rule finding. Consider it with the other observations rather than treating it as proof of malicious ownership.', 'warning')
    missing.append(dict(check='javascript', reason='JavaScript was not executed. Dynamic forms, downloads and browser behaviour were not inspected.'))
    probability = _mapping(meta.get('score_components')).get('model_probability')
    threshold = meta.get('threshold')
    usable = isinstance(probability, (float, int)) and math.isfinite(probability) and isinstance(threshold, (float, int)) and math.isfinite(threshold)
    model = (f"The URL model estimate was {probability * 100:.1f} against its alert boundary of {threshold * 100:.1f}. "
             f"It {'triggered' if probability >= threshold else 'did not trigger'} the primary model alert. " if usable else 'No primary URL model estimate was available. ')
    if meta.get('rescue_applied'):
        model += 'A separate expert triggered the additional warning rule. '
    model += 'This describes learned URL patterns. It is not an observed malicious action or a prediction-confidence percentage.'
    live = sum(str(_mapping(signals.get(k)).get('status', '')).lower() == 'observed' for k in ('dns', 'tls', 'http', 'html', 'registration', 'reputation'))
    return dict(version='url-evidence-v1', observations=observations, model_assessment=model, missing_checks=missing,
                live_checks_observed=live, live_checks_total=6,
                scope='A separate inspection snapshot. The original quick message and URL warning remains unchanged.')
