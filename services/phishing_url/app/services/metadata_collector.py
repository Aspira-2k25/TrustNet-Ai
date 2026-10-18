"""Optional observed metadata; never insert missing age zero or fake TLS claims."""
from datetime import datetime, timezone
import json
from urllib.parse import quote
from .safe_fetch import fetch, public_addresses
from models.phishing_url.preprocessing.url_parser import parse_url
from models.phishing_url.inference.forensics import registered_domain
from html.parser import HTMLParser
from .reputation import lookup
from time import monotonic

class PasswordForms(HTMLParser):
    """Static evidence only; never executes scripts, follows form actions or submits data."""
    def __init__(self):
        super().__init__()
        self.forms, self.current, self.base_url, self.owners = [], None, None, []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'base' and self.base_url is None:
            self.base_url = attrs.get('href')
        if tag == 'form':
            self.current = {'action': attrs.get('action', ''), 'password': False, 'id': attrs.get('id')}
            self.forms.append(self.current)
        if tag == 'input' and attrs.get('type', '').lower() == 'password':
            if attrs.get('form'):
                self.owners.append(attrs['form'])
            elif self.current is not None:
                self.current['password'] = True
    def handle_endtag(self, tag):
        if tag == 'form':
            self.current = None

def password_forms(body, page_url):
    from urllib.parse import urljoin
    parser = PasswordForms()
    parser.feed(body.decode('utf-8', errors='replace'))
    for form in parser.forms:
        if form['id'] in parser.owners:
            form['password'] = True
    base = urljoin(page_url, parser.base_url) if parser.base_url else page_url
    return [{'action': urljoin(base, f['action']) if f['action'] else page_url}
            for f in parser.forms if f['password']][:20]

def collect(url, include_html=False):
    collection_started=monotonic()
    from concurrent.futures import ThreadPoolExecutor
    observed = datetime.now(timezone.utc).isoformat()
    parsed = parse_url(url)
    signals = {}
    try:
        signals['dns'] = {'status':'observed','addresses':public_addresses(parsed.hostname, parsed.parts.port or 443)}
    except Exception as exc:
        signals['dns'] = {'status':'unavailable','reason':type(exc).__name__}
    def website():
        import ssl
        try:
            response = fetch(url, timeout=8, max_bytes=262144 if include_html else 8192)
            value = {'tls':{'status':'observed' if response['certificate'] else 'not_observed','certificate':response['certificate'],
                            'analysis':response.get('certificate_details')},
                     'navigation':{'status':'observed','hops':response.get('navigation',[])},
                     'http':{'status':'observed','status_code':response['status'],'redirects':response['redirects'],'final_url':response['final_url']}}
            if include_html:
                value['html'] = {'status':'observed','bytes':len(response['body']),'content_type':response['content_type'],
                                 'truncated':response.get('truncated',False)}
                if 'text/html' in response['content_type'].lower():
                    value['html']['password_forms'] = password_forms(response['body'],response['final_url'])
            return value
        except ssl.SSLCertVerificationError as exc:
            return {'tls':{'status':'observed','validated':False,'verification_code':exc.verify_code,
                           'reason':exc.verify_message},
                    'navigation':{'status':'observed' if getattr(exc,'navigation',[]) else 'unavailable','hops':getattr(exc,'navigation',[])},
                    'http':{'status':'unavailable','reason':'Certificate verification failed; insecure retry is disabled.'}}
        except Exception as exc:
            return {'http':{'status':'unavailable','reason':type(exc).__name__},
                    'navigation':{'status':'observed' if getattr(exc,'navigation',[]) else 'unavailable','hops':getattr(exc,'navigation',[])}}
    def registration():
        try:
            if parsed.is_ip: raise ValueError('Not a registered domain')
            response = fetch('https://rdap.org/domain/'+quote(registered_domain(parsed.hostname),safe=''),timeout=8,max_bytes=131072)
            if response['status'] != 200: raise ValueError('Registration lookup failed')
            data = json.loads(response['body'])
            event = next((e['eventDate'] for e in data.get('events',[]) if e.get('eventAction')=='registration'),None)
            age = None
            if event:
                created = datetime.fromisoformat(event.replace('Z','+00:00'))
                days = (datetime.now(timezone.utc)-created).days
                age = days if days >= 0 else None
            return {'registration':{'status':'observed' if age is not None else 'unavailable','registration_date':event,'protocol':'RDAP'},'domain_age_days':age}
        except Exception as exc:
            return {'registration':{'status':'unavailable','reason':type(exc).__name__},'domain_age_days':None}
    def reputation():
        try:
            from models.phishing_url.inference.forensics import suffix_parser
            public_name = not parsed.is_ip and bool(suffix_parser()(parsed.hostname).suffix)
            permitted = signals['dns']['status']=='observed' or (public_name and signals['dns'].get('reason')!='FetchBlocked')
            return lookup(url) if permitted else {'status':'UNAVAILABLE','matched':False,'reason':'Private or unrecognised destination; reputation lookup skipped.'}
        except Exception:
            return {'status':'UNAVAILABLE','matched':False,'reason':'Reputation lookup unavailable.'}
    with ThreadPoolExecutor(max_workers=3) as pool:
        page, rdap, rep = pool.submit(website), pool.submit(registration), pool.submit(reputation)
        signals.update(page.result())
        registration_result = rdap.result()
        signals['registration'] = registration_result['registration']
        signals['reputation'] = rep.result()
    final_url = signals.get('http',{}).get('final_url')
    reputation_paused=signals['reputation'].get('status')=='RATE_LIMITED'
    if final_url and final_url != url and not signals['reputation'].get('fresh_match'):
        try:
            final_reputation = lookup(final_url)
            reputation_paused=final_reputation.get('status')=='RATE_LIMITED'
            if final_reputation.get('fresh_match'):
                final_reputation['match_scope'] = 'redirect_destination'
                signals['reputation'] = final_reputation
        except Exception:
            pass  # Keep the original provider observation; no invented final verdict.
    # Inspect observed intermediate hops too: a benign final page cannot erase
    # an earlier reported destination. Never follow guessed query parameters.
    checked={url,final_url}
    additional=0
    for hop in signals.get('navigation',{}).get('hops',[])[:4]:
        hop_url=hop.get('url')
        if signals['reputation'].get('fresh_match') or additional>=2:break
        if reputation_paused:break
        if not hop_url or hop_url in checked:continue
        # Optional enrichment must leave time for the worker's 30-second RPC.
        if monotonic()-collection_started>12:break
        checked.add(hop_url)
        try:
            destination=parse_url(hop_url)
            if destination.parts.username is not None:continue
            public_addresses(destination.hostname,destination.parts.port or (443 if destination.parts.scheme=='https' else 80))
            if monotonic()-collection_started>12:break
            additional+=1
            hop_reputation=lookup(hop_url)
            if hop_reputation.get('fresh_match'):
                hop_reputation.update(match_scope='redirect_hop',matched_url=hop_url)
                signals['reputation']=hop_reputation
            elif hop_reputation.get('status')=='RATE_LIMITED':
                break
        except Exception:
            continue
    return {'observed_at':observed,'domain_age_days':registration_result['domain_age_days'],'signals':signals}
