"""Explainable URL forensics. Offline by default; observations are not probabilities."""
import ipaddress
import re
from functools import lru_cache
from urllib.parse import unquote, urljoin

from models.phishing_url.preprocessing.url_parser import parse_url

POLICY_VERSION = 'dynamic-v2'

@lru_cache(maxsize=1)
def suffix_parser():
    import tldextract
    return tldextract.TLDExtract(suffix_list_urls=(), cache_dir=None, include_psl_private_domains=True)

def registered_domain(host):
    try:
        ipaddress.ip_address(host)
        return host
    except ValueError:
        value = suffix_parser()(host)
        return value.top_domain_under_public_suffix or host

def canonical_url(url):
    from models.phishing_url.preprocessing.link_input import inspect_input
    link=inspect_input(url)
    if link['kind']!='web':raise ValueError('The trained URL model applies to website links only.')
    parsed = parse_url(link['normalized'])
    # Inference policy only: do not alter frozen training feature extraction.
    return parsed.parts._replace(path=parsed.parts.path or '/').geturl()

def analyze(url, observations=None):
    from models.phishing_url.preprocessing.link_input import inspect_input
    link=inspect_input(url)
    if link['kind']!='web':
        if link['hostname']:
            from urllib.parse import urlsplit
            parts=urlsplit(link['normalized'])
            destination=parts._replace(scheme='https',path='/',query='',fragment='').geturl() if parts.netloc else 'https://'+link['hostname']+'/'
            report=analyze(destination)
        else:
            report={'version':POLICY_VERSION,'hostname':None,'registered_domain':None,'registration_boundary_known':False,
                    'outcome':'REVIEW','findings':[],'network':{'status':'NOT_COLLECTED','reason':'Non-web links are never fetched or executed.'},
                    'path_analysis':{},'definition':'Offline link inspection only; website ownership and content are not verified.'}
        report['input']=link
        report['network']={'status':'NOT_COLLECTED','reason':'Non-web links are never fetched or executed.'}
        report['path_analysis']={}
        report['findings'].append({'code':'NON_WEB_SCHEME','severity':'info',
            'reason':f"This is a {link['scheme']} link. Its destination can be inspected where present, but the website model and live page checks do not apply. The link was not opened or executed."})
        return report
    url=link['normalized']
    parsed = parse_url(url)
    host, parts = parsed.hostname, parsed.parts
    domain = registered_domain(host)
    findings = []
    def add(code, severity, reason):
        findings.append({'code': code, 'severity': severity, 'reason': reason})
    from .lookalike import compare
    try:visual_match=compare(domain)
    except (OSError,ValueError,KeyError):
        visual_match=None
        add('LOOKALIKE_CHECK_UNAVAILABLE','info','The visual-domain reference could not be loaded; no lookalike conclusion was made.')
    if visual_match:
        add('VISUAL_DOMAIN_IMPERSONATION','high',f"The actual registered domain is {domain}, which visually resembles {visual_match['resembles_domain']} but is a different domain. Similar-looking characters such as i, l or 1 can conceal the difference. This is an impersonation risk; affiliation and malicious ownership are not established.")
    try:
        decoded_host = host.encode('ascii').decode('idna')
    except UnicodeError:
        decoded_host = host
        add('INVALID_IDN', 'medium', 'The hostname contains an invalid internationalised-name encoding; its identity cannot be established.')
    if parts.username is not None:
        add('USERINFO', 'medium', f'Text before @ is login information, not the destination. The actual hostname is {host}.')
        apparent = unquote(parts.username).lower().rstrip('.')
        try:
            apparent_host = parse_url(apparent if '://' in apparent else 'https://' + apparent).hostname
            if suffix_parser()(apparent_host).suffix and registered_domain(apparent_host) != domain:
                add('MISLEADING_AUTHORITY', 'high', f'The domain {apparent_host} is placed before @, but the request goes to {host}. The apparent domain is not the destination.')
        except ValueError:
            pass
    if parsed.is_ip:
        ip = ipaddress.ip_address(host)
        add('IP_DESTINATION', 'medium', 'The destination is a numeric IP address; this alone does not establish phishing.')
        if not ip.is_global:
            add('NON_PUBLIC_DESTINATION', 'medium', 'The address targets a local or non-public network. Online collection is blocked.')
    if 'xn--' in host:
        add('IDN', 'info', f'The internationalised hostname decodes to {decoded_host}. Internationalised names are not inherently malicious.')
        import unicodedata
        mixed = False
        for label in decoded_host.split('.'):
            scripts = set()
            for char in label:
                name = unicodedata.name(char, '')
                scripts.update(script for script in ('LATIN', 'CYRILLIC', 'GREEK') if script in name)
            mixed = mixed or len(scripts) > 1
        if mixed:
            add('MIXED_SCRIPT', 'medium', 'The hostname mixes writing systems, which can disguise lookalike letters.')
    if parts.port and parts.port not in (80, 443):
        add('UNUSUAL_PORT', 'medium', f'The URL uses port {parts.port}, outside standard web ports. This can also be legitimate.')
    if parts.scheme == 'http':
        add('UNENCRYPTED', 'info', 'The URL uses HTTP; data sent to this address is not protected by HTTPS.')
    # Inspect hostname only: brand names in ordinary page paths are not impersonation.
    subdomain = host[:-len(domain)].rstrip('.') if host != domain else ''
    boundary_known = not parsed.is_ip and bool(suffix_parser()(host).suffix)
    if not boundary_known and not parsed.is_ip and host.count('.') >= 2:
        # Unknown/reserved suffix: inspect misleading prefixes without claiming
        # that a registration boundary is known.
        subdomain = host.rsplit('.', 2)[0]
    labels = subdomain.split('.')
    for end in range(2, len(labels)+1):
        apparent = '.'.join(labels[:end])
        if suffix_parser()(apparent).suffix and registered_domain(apparent) != domain:
            add('EMBEDDED_DOMAIN', 'medium', f'The hostname contains the separate domain-like prefix {apparent}, while the actual destination is {host}. Affiliation is unverified.')
            break
    if re.search(r'%(?:25)?(?:2f|40|2e)', parts.netloc, re.I):
        add('ENCODED_AUTHORITY', 'medium', 'Encoded separators appear in the authority section and may obscure the destination.')
    if '%' in parts.path or '%' in parts.query:
        add('ENCODING', 'info', 'The path or query contains encoded characters. Encoding alone is normal and is not evidence of phishing.')
    network = {'status': 'NOT_COLLECTED', 'reason': 'Optional isolated collector is not configured.'}
    from .navigation import inspect_path
    path_analysis = inspect_path(url)
    if path_analysis['dot_segments']:
        add('PATH_TRAVERSAL', 'medium', 'The path contains dot segments or their encoded forms, which can obscure navigation. This is not proof of phishing.')
    if path_analysis['double_encoding']:
        add('DOUBLE_ENCODED_PATH', 'info', 'The path changes after a second decoding pass. Different servers may interpret it differently.')
    if any(t['external_hostname'] for t in path_analysis['navigation_parameters']):
        add('NAVIGATION_PARAMETER', 'info', 'A navigation parameter names another hostname. It was recorded, not followed; sign-in redirects can be legitimate.')
    if observations is not None:
        signals = observations.get('signals', {})
        network = {'status': 'OBSERVED' if any(str(v.get('status', '')).lower() == 'observed' for v in signals.values()) else 'UNAVAILABLE',
                   'signals': signals, 'observed_at': observations.get('observed_at'),
                   'domain_age_days': observations.get('domain_age_days')}
        age = observations.get('domain_age_days')
        if isinstance(age, (int, float)) and 0 <= age < 30:
            add('RECENT_REGISTRATION', 'medium', f'The observed registration age is {age:g} days. New domains can also be legitimate.')
        http = signals.get('http', {})
        observed_urls=[h.get('url') for h in signals.get('navigation',{}).get('hops',[])[:4]]
        if http.get('status')=='observed':observed_urls.append(http.get('final_url'))
        for observed_url in observed_urls:
            if not observed_url:continue
            try:
                observed_domain=registered_domain(parse_url(observed_url).hostname)
                match=compare(observed_domain) if observed_domain!=domain else None
            except (ValueError,OSError,KeyError):continue
            if match and not visual_match:
                visual_match={**match,'match_scope':'observed_navigation','observed_url':observed_url}
                add('VISUAL_DOMAIN_IMPERSONATION','high',f"An observed navigation destination uses {observed_domain}, which visually resembles {match['resembles_domain']} but is a different registered domain. This is an impersonation risk; affiliation is not established.")
        if http.get('status') == 'observed' and http.get('final_url'):
            final = parse_url(http['final_url'])
            if registered_domain(final.hostname) != domain:
                add('CROSS_DOMAIN_REDIRECT', 'medium', f'The request redirects from {domain} to {registered_domain(final.hostname)}. Redirects can be legitimate.')
            if parts.scheme == 'https' and final.parts.scheme == 'http':
                add('HTTPS_DOWNGRADE', 'medium', 'The redirect chain ends on unencrypted HTTP.')
        html = signals.get('html', {})
        tls = signals.get('tls', {})
        certificate = tls.get('analysis') or {}
        if tls.get('validated') is False:
            add('TLS_VALIDATION_FAILED','medium','The certificate failed TLS verification: '+str(tls.get('reason','verification error'))+'. The page was not fetched insecurely; this can also be a site configuration problem.')
        if certificate.get('weak_signature_hash') or certificate.get('weak_public_key'):
            add('WEAK_CERTIFICATE','medium','The validated certificate uses a weak signature hash or public key. This concerns transport security and does not alone establish phishing.')
        if isinstance(certificate.get('expires_in_days'),int) and certificate['expires_in_days']<=7:
            add('CERTIFICATE_EXPIRING','info','The observed TLS certificate expires within seven days. Automatic renewal is common; expiry proximity is not a phishing verdict.')
        hops = signals.get('navigation',{}).get('hops',[])[:4]
        schemes=[h.get('scheme') for h in hops]
        if any(a=='https' and b=='http' for a,b in zip(schemes,schemes[1:])) and not any(f['code']=='HTTPS_DOWNGRADE' for f in findings):
            add('HTTPS_DOWNGRADE','medium','An intermediate redirect moved from HTTPS to unencrypted HTTP, even if a later hop returned to HTTPS.')
        hop_domains=[]
        for hop in hops:
            try:hop_domains.append(registered_domain(parse_url(hop['url']).hostname))
            except (KeyError,ValueError):continue
        if sum(a!=b for a,b in zip(hop_domains,hop_domains[1:]))>=2:
            add('MULTI_DOMAIN_NAVIGATION','medium','The observed redirect chain crosses registered-domain boundaries more than once. Ad networks and identity providers can also do this.')
        reputation = signals.get('reputation', {})
        if str(reputation.get('status', '')).lower() == 'observed' and reputation.get('fresh_match'):
            subject = 'The final redirect destination' if reputation.get('match_scope') == 'redirect_destination' else 'This exact URL'
            add('REPUTATION_MATCH', 'high', f'{subject} has a phishing report in {reputation.get("provider", "the reputation provider")}; the report date is recorded in the evidence.')
        elif reputation.get('matched'):
            add('REPUTATION_HISTORY', 'info', 'A historical URL report exists, but its freshness or provider score is insufficient for a current phishing alert.')
        for form in html.get('password_forms', [])[:20]:
            try:
                action = parse_url(urljoin(http.get('final_url') or url, form['action']))
                page = parse_url(http.get('final_url') or url)
            except (ValueError, KeyError):
                continue
            if action.parts.scheme == 'http':
                add('PASSWORD_HTTP', 'high', 'A password form submits to HTTP, exposing credentials without transport encryption.')
            if registered_domain(action.hostname) != registered_domain(page.hostname):
                add('PASSWORD_EXTERNAL', 'medium', f'A password form submits to another registered domain, {registered_domain(action.hostname)}. This can be an identity provider; affiliation is unverified.')
    # Weak signals are never summed into a high-risk verdict.
    high = any(f['severity'] == 'high' for f in findings)
    medium = any(f['severity'] == 'medium' for f in findings)
    return {'version': POLICY_VERSION, 'hostname': host, 'registered_domain': domain if boundary_known else None,
            'registration_boundary_known': boundary_known,
            'outcome': 'SUSPICIOUS' if high else 'REVIEW' if medium else 'NO_STRONG_INDICATORS',
            'findings': findings, 'network': network, 'path_analysis':path_analysis, 'input':link, 'visual_domain_match':visual_match,
            'definition': 'Observable indicators; absence of findings does not establish safety. Rules are not a calibrated probability.'}

def apply_policy(result, url, threshold=None, observations=None):
    from .dynamic_policy import apply
    return apply(result, url, threshold, observations)
