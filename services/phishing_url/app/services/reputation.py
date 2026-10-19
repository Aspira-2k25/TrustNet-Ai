"""Rate-bounded live reputation lookup. A missing match is never a clean verdict.

Only the hostname is sent to PhishStats; exact URL matching happens locally.
No URL is submitted for a new third-party scan.
"""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import time
from contextlib import closing
from datetime import datetime, timezone
from urllib.parse import urlsplit
import httpx
from models.phishing_url.preprocessing.url_parser import parse_url

ENDPOINT = 'https://api.phishstats.info/api/phishing'
TTL = 5400  # Provider recommends no polling more often than its 90-minute refresh.

def match_key(url):
    p = parse_url(url)
    host = '['+p.hostname+']' if ':' in p.hostname else p.hostname
    port = p.parts.port
    if port and port != (443 if p.parts.scheme == 'https' else 80):
        host += ':'+str(port)
    return p.parts._replace(netloc=host, path=p.parts.path or '/').geturl()

def lookup(url):
    parsed = urlsplit(url)
    base = {'provider': 'PhishStats', 'status': 'UNAVAILABLE', 'matched': False,
            'checked_at': datetime.now(timezone.utc).isoformat(),
            'definition': 'Exact URL match against provider reports. No match is not evidence of safety.'}
    if parsed.username is not None:
        return {**base, 'reason': 'Credential-bearing URLs are not sent to a reputation provider.'}
    host = parse_url(url).hostname
    directory = Path(os.getenv('PHISHING_CACHE_DIR', str(Path(tempfile.gettempdir())/'trustnet-phishing-cache')))
    directory.mkdir(parents=True, exist_ok=True)
    now = time.time()
    key = hashlib.sha256(('host-substring-v2:'+host).encode()).hexdigest()
    with closing(sqlite3.connect(directory/'reputation.sqlite3', timeout=3)) as db, db:
        db.execute('CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, expires REAL, body TEXT)')
        db.execute('CREATE TABLE IF NOT EXISTS quota (day TEXT PRIMARY KEY, requests INTEGER)')
        cached = db.execute('SELECT body FROM cache WHERE key=? AND expires>?', (key, now)).fetchone()
        if cached:
            data = json.loads(cached[0])
            cached_result = True
        else:
            if db.execute('SELECT 1 FROM cache WHERE key=? AND expires>?', ('__provider_backoff__', now)).fetchone():
                return {**base, 'status': 'RATE_LIMITED', 'reason': 'Provider retry window is active.'}
            day = datetime.now(timezone.utc).strftime('%Y-%m-%d')
            db.execute('BEGIN IMMEDIATE')
            count = db.execute('SELECT requests FROM quota WHERE day=?', (day,)).fetchone()
            if count and count[0] >= int(os.getenv('PHISHING_REPUTATION_DAILY_LIMIT', '45')):
                return {**base, 'status': 'RATE_LIMITED', 'reason': 'Local daily reputation budget reached.'}
            db.execute('INSERT INTO quota VALUES (?,1) ON CONFLICT(day) DO UPDATE SET requests=requests+1', (day,))
            db.commit()
            headers = {'User-Agent': 'TrustNet-Phishing/2.0 (URL reputation research)'}
            if os.getenv('PHISHSTATS_API_KEY'):
                headers['X-API-Key'] = os.environ['PHISHSTATS_API_KEY']
            try:
                response = httpx.get(ENDPOINT, params={'_where': f'(host,eq,{host})', '_size': 100, '_sort': '-date'}, headers=headers, timeout=httpx.Timeout(8,connect=3))
                if response.status_code == 429:
                    try: retry = max(60, min(86400, float(response.headers.get('Retry-After','60'))))
                    except (ValueError,TypeError): retry = 60
                    db.execute('INSERT OR REPLACE INTO cache VALUES (?,?,?)', ('__provider_backoff__', now+retry, '{}'))
                    db.execute('INSERT OR REPLACE INTO cache VALUES (?,?,?)', (key, now+TTL, json.dumps({'rate_limited': True})))
                    return {**base, 'status': 'RATE_LIMITED', 'reason': 'Provider quota reached.'}
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, list): raise ValueError('Unexpected provider response')
                db.execute('INSERT OR REPLACE INTO cache VALUES (?,?,?)', (key, now+TTL, json.dumps(data)))
                db.execute('DELETE FROM cache WHERE expires<?', (now,))
                cached_result = False
            except (httpx.HTTPError, ValueError) as exc:
                return {**base, 'reason': 'Reputation service did not return a usable response.',
                        'error_type': type(exc).__name__, 'http_status': getattr(getattr(exc,'response',None),'status_code',None)}
    if isinstance(data, dict):
        return {**base, 'status': 'RATE_LIMITED', 'reason': 'Provider retry is deferred.'}
    matches = []
    for item in data[:100]:
        try:
            if match_key(item.get('url')) == match_key(url):
                matches.append({'id': item.get('id'), 'reported_at': item.get('date'), 'provider_score': item.get('score')})
        except (ValueError, AttributeError):
            continue
    fresh = False
    for report in matches:
        try:
            date = datetime.fromisoformat(report['reported_at'].replace('Z','+00:00'))
            age = (datetime.now(timezone.utc)-date).total_seconds()
            fresh = fresh or (0 <= age <= 7*86400 and float(report['provider_score']) >= 7)
        except (ValueError, TypeError, AttributeError):
            continue
    return {**base, 'status': 'OBSERVED', 'matched': bool(matches), 'fresh_match': fresh, 'reports': matches,
            'cached': cached_result, 'cache_ttl_seconds': TTL, 'search_may_be_truncated': len(data) >= 100}

def prefetch(urls):
    """Warm up to ten requested public-host lookups in ONE provider request.

    This stores provider responses, never caller-supplied labels or verdicts.
    Intended for bulk scans/audits; ordinary scans use the same per-host cache.
    """
    hosts = sorted({parse_url(url).hostname for url in urls if urlsplit(url).username is None})
    if not hosts or len(hosts)>10:
        raise ValueError('Batch requires 1–10 distinct hosts')
    directory=Path(os.getenv('PHISHING_CACHE_DIR',str(Path(tempfile.gettempdir())/'trustnet-phishing-cache')))
    directory.mkdir(parents=True,exist_ok=True)
    now=time.time()
    with closing(sqlite3.connect(directory/'reputation.sqlite3',timeout=3)) as db, db:
        db.execute('CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, expires REAL, body TEXT)')
        db.execute('CREATE TABLE IF NOT EXISTS quota (day TEXT PRIMARY KEY, requests INTEGER)')
        hosts = [h for h in hosts if not db.execute('SELECT 1 FROM cache WHERE key=? AND expires>?',
                 (hashlib.sha256(('host-substring-v2:'+h).encode()).hexdigest(),now)).fetchone()]
        if not hosts:
            return {'status':'OBSERVED','cached':True,'hosts':0}
        if db.execute('SELECT 1 FROM cache WHERE key=? AND expires>?',('__provider_backoff__',now)).fetchone():
            return {'status':'RATE_LIMITED'}
        day=datetime.now(timezone.utc).strftime('%Y-%m-%d')
        db.execute('BEGIN IMMEDIATE')
        count=db.execute('SELECT requests FROM quota WHERE day=?',(day,)).fetchone()
        if count and count[0]>=int(os.getenv('PHISHING_REPUTATION_DAILY_LIMIT','45')):
            return {'status':'RATE_LIMITED'}
        db.execute('INSERT INTO quota VALUES (?,1) ON CONFLICT(day) DO UPDATE SET requests=requests+1',(day,))
        db.commit()
        headers={'User-Agent':'TrustNet-Phishing/2.0 (URL reputation research)'}
        if os.getenv('PHISHSTATS_API_KEY'):headers['X-API-Key']=os.environ['PHISHSTATS_API_KEY']
        try:
            response=httpx.get(ENDPOINT,params={'_where':'~or'.join(f'(host,eq,{host})' for host in hosts),'_size':100,'_sort':'-date'},headers=headers,timeout=httpx.Timeout(12,connect=3))
            response.raise_for_status()
            rows=response.json()
            if not isinstance(rows,list):raise ValueError('Unexpected response')
            for host in hosts:
                matches=[]
                for item in rows:
                    try:
                        if parse_url(item['url']).hostname==host:matches.append(item)
                    except (ValueError,KeyError,TypeError):continue
                # A truncated combined result cannot establish a per-host miss.
                if len(rows)<100:
                    key=hashlib.sha256(('host-substring-v2:'+host).encode()).hexdigest()
                    db.execute('INSERT OR REPLACE INTO cache VALUES (?,?,?)',(key,now+TTL,json.dumps(matches)))
            return {'status':'OBSERVED','hosts':len(hosts),'provider_records':len(rows)}
        except (httpx.HTTPError,ValueError) as exc:
            if isinstance(exc,httpx.HTTPStatusError) and exc.response.status_code==429:
                db.execute('INSERT OR REPLACE INTO cache VALUES (?,?,?)',('__provider_backoff__',now+TTL,'{}'))
            return {'status':'UNAVAILABLE','error_type':type(exc).__name__,'http_status':getattr(getattr(exc,'response',None),'status_code',None)}
