"""Freeze local research-only labels; never visit URLs from the threat feed.

Official-page links are reference negatives, not independently certified safe pages.
OpenPhish data stays under ignored data/ and is not used for a runtime blacklist.
"""
import csv
import hashlib
import json
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'models/phishing_url/data/improvement_20261018/fresh_holdout_v2'
SOURCES = [
    'https://docs.python.org/3/', 'https://developer.mozilla.org/en-US/docs/Web',
    'https://www.w3.org/standards/', 'https://docs.djangoproject.com/en/stable/',
    'https://www.postgresql.org/docs/current/', 'https://www.sqlite.org/docs.html',
    'https://doc.rust-lang.org/book/', 'https://go.dev/doc/',
    'https://www.gov.uk/', 'https://www.nasa.gov/',
    'https://www.gnu.org/manual/manual.html', 'https://www.kernel.org/doc/html/latest/',
    'https://www.cloudflare.com/learning/', 'https://www.mozilla.org/en-US/',
    'https://www.who.int/', 'https://www.khanacademy.org/',
]


class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.links = []
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            value = dict(attrs).get('href')
            if value: self.links.append(value)


def fetch(client, url):
    # Fixed trusted collection sources only; redirects never leave the source host.
    expected = urlsplit(url).hostname
    for _ in range(4):
        with client.stream('GET', url) as response:
            if response.is_redirect:
                target = urljoin(url, response.headers['location'])
                if urlsplit(target).hostname != expected or urlsplit(target).scheme != 'https':
                    raise ValueError('Source redirect changed host or transport')
                url = target; continue
            response.raise_for_status()
            body = bytearray()
            for chunk in response.iter_bytes():
                body.extend(chunk)
                if len(body) > 4_000_000: raise ValueError('Source size limit exceeded')
            return bytes(body), url
    raise ValueError('Source redirect limit exceeded')


def main():
    if (OUT/'manifest.json').exists():
        raise SystemExit('Frozen holdout already exists; use a new version to collect again.')
    OUT.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    rows, events, seen = [], [], set()
    def add(url, label, source, label_basis):
        try:
            p = urlsplit(url)
            if p.scheme not in {'http','https'} or not p.hostname or p.username: return
            normalized = p._replace(fragment='', path=p.path or '/').geturl()
            if len(normalized)>2048 or normalized in seen: return
            seen.add(normalized)
            rows.append({'url':normalized,'label':label,'source':source,'label_basis':label_basis,'collected_at':now})
        except ValueError: return
    with httpx.Client(timeout=httpx.Timeout(12,connect=5),headers={'User-Agent':'TrustNet-Academic-Research/1.0'},follow_redirects=False) as client:
        url = 'https://raw.githubusercontent.com/openphish/public_feed/refs/heads/main/feed.txt'
        try:
            body, _ = fetch(client,url)
            (OUT/'openphish-feed.txt').write_bytes(body)
            events.append({'source':url,'sha256':hashlib.sha256(body).hexdigest(),'status':'collected','terms':'https://openphish.com/terms.html','usage':'Local noncommercial research only; do not redistribute feed or URLs.'})
            for line in body.decode('utf-8').splitlines(): add(line.strip(),1,'openphish_community','provider_report_not_independent_adjudication')
        except Exception as exc: events.append({'source':url,'status':'unavailable','reason':str(exc)[:200]})
        print(json.dumps({'stage':'threat_feed','rows':len(rows)}),flush=True)
        for source in SOURCES:
            try:
                body, final = fetch(client,source)
                parser=Links();parser.feed(body.decode('utf-8',errors='replace'))
                urls={final}
                for href in parser.links:
                    target=urljoin(final,href)
                    p=urlsplit(target)
                    if p.hostname==urlsplit(final).hostname and p.scheme=='https' and not p.query:
                        urls.add(p._replace(fragment='').geturl())
                # Deterministic path sample, including homepage without inventing URLs.
                chosen=sorted(urls,key=lambda u:hashlib.sha256(u.encode()).hexdigest())[:40]
                for target in chosen:add(target,0,source,'same_host_link_from_official_page_reference_negative')
                events.append({'source':source,'status':'collected','sha256':hashlib.sha256(body).hexdigest(),'reference_negatives':len(chosen)})
            except Exception as exc: events.append({'source':source,'status':'unavailable','reason':str(exc)[:200]})
            print(json.dumps({'stage':'reference_source','source':source,'rows':len(rows)}),flush=True)
    path=OUT/'holdout.csv'
    with path.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=['url','label','source','label_basis','collected_at']);writer.writeheader();writer.writerows(rows)
    manifest={'collected_at':now,'rows':len(rows),'class_counts':{str(y):sum(r['label']==y for r in rows) for y in (0,1)},
              'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'sources':events,
              'role':'Frozen research challenge, not training data. Exclude historical fit domains for strict subset.',
              'limitations':['Provider labels and official-page reference negatives are not independently adjudicated.','Collection time is not attack creation time; not a proven temporal benchmark.','Small nonrandom convenience sample; do not claim deployment accuracy.','Do not open threat URLs or redistribute proprietary feed data.']}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps({'stage':'frozen','rows':len(rows),'classes':manifest['class_counts'],'sha256':manifest['sha256']}),flush=True)

if __name__=='__main__': main()
