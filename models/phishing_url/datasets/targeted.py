"""Label-preserving URL normalization and grouped, deterministic data reservation."""
import hashlib
import csv
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from functools import lru_cache
import tldextract
from models.phishing_url.preprocessing.url_parser import parse_url

VERSION='targeted-url-data-v1'
SUFFIX=tldextract.TLDExtract(suffix_list_urls=(),cache_dir=None,include_psl_private_domains=True)


@lru_cache(maxsize=300000)
def registered_domain(host):
    return SUFFIX(host).top_domain_under_public_suffix or host


def normalize(url):
    """Preserve case-sensitive paths/queries, escape sequences and full-length identity."""
    p=parse_url(url)
    if len(url)>2048:raise ValueError('exceeds_runtime_input_limit')
    host=p.hostname
    if ':' in host:host='['+host+']'
    if p.parts.username is not None:raise ValueError('credential_bearing_authority')
    port=p.parts.port
    if port and port!=(443 if p.parts.scheme=='https' else 80):host+=':'+str(port)
    normalized=p.parts._replace(netloc=host,path=p.parts.path or '/').geturl()
    # Fragments are retained in the input; conflicting labels on the same wire URL
    # are quarantined rather than guessed from client-side behavior.
    wire=p.parts._replace(netloc=host,path=p.parts.path or '/',fragment='').geturl()
    return normalized,wire,registered_domain(p.hostname)


def tags(url):
    p=urlsplit(url);path=p.path or '/';host=p.hostname or ''
    found=[]
    if path=='/':found.append('root_path')
    if len(path)>=30:found.append('long_path')
    if p.query:found.append('query_parameters')
    if re.search(r'(?:^|[/_.?=&-])(?:login|log-in|sign.?in|sign.?up|accounts?|password|payment|billing|checkout|auth|authentication|oauth|register|verify)(?:$|[/_.?=&-])',path+'?'+p.query,re.I):found.append('authentication_account_payment')
    if 'xn--' in host or any(ord(c)>127 for c in url):found.append('internationalized')
    if any(s in host for s in ('.github.io','.pages.dev','.vercel.app','.netlify.app','.workers.dev','.blogspot.')):found.append('shared_hosting')
    if '%' in url:found.append('encoded_characters')
    if p.query and re.search(r'(?:^|&)(?:url|redirect|next|continue|return|destination)=',p.query,re.I):found.append('navigation_parameter')
    return found or ['other']


def campaign_signature(url):
    """Conservative near-duplicate path grouping, never a phishing label.

    Generic /login paths are not enough to group unrelated sites. Unknown root-path
    campaigns remain unknown; this is not a guarantee of campaign independence.
    """
    p=urlsplit(url)
    path=re.sub(r'[0-9a-f]{12,}','<hex>',p.path.lower())
    path=re.sub(r'\d+','<n>',path)
    words=re.findall('[a-z]{4,}',path)
    generic={'login','signin','signup','account','accounts','password','verify','secure','index','html','https','http','auth','oauth','home','users','profile'}
    distinctive={word for word in words if word not in generic}
    if len(path)<30 or sum(map(len,distinctive))<16:return ''
    return hashlib.sha256(path.encode()).hexdigest()


class Groups:
    def __init__(self):self.parents={}
    def find(self,key):
        self.parents.setdefault(key,key)
        trail=[]
        while self.parents[key]!=key:trail.append(key);key=self.parents[key]
        for old in trail:self.parents[old]=key
        return key
    def union(self,a,b):
        a,b=self.find(a),self.find(b)
        if a!=b:self.parents[max(a,b)]=min(a,b)


def bucket(group,salt='targeted-20261018-v1'):
    return int(hashlib.sha256((salt+':'+group).encode()).hexdigest()[:8],16)%100


def private_or_tokenized(url):
    p=urlsplit(url)
    # Public sign-in pages can embed session/CSRF values; do not retain these.
    return bool(re.search(r'(?:^|&)(?:access_token|id_token|token|code|session|sessionid|csrf|csrf_token|samlresponse)=',p.query,re.I))


def development_rows(root,split):
    """Allow only development inputs; the independent test is not a training split."""
    if split not in {'train','calibration','validation'}:raise ValueError('Only development splits can be loaded for fitting/selection')
    root=Path(root);manifest=json.loads((root/'dataset_manifest.json').read_text())
    if not manifest['minimum_research_test_coverage_met']:raise ValueError('Independent test coverage gate has not been met')
    proof=json.loads((root/'verification.json').read_text())
    label_audit=json.loads((root/'normalization_label_audit.json').read_text())
    manifest_hash=hashlib.sha256((root/'dataset_manifest.json').read_bytes()).hexdigest()
    if not proof.get('file_hashes_verified') or proof.get('dataset_manifest_sha256')!=manifest_hash or label_audit.get('normalized_label_conflicts')!=0:
        raise ValueError('Dataset integrity/label verification is incomplete')
    path=root/(split+'.csv');digest=hashlib.sha256()
    with path.open('rb') as f:
        for part in iter(lambda:f.read(1024*1024),b''):digest.update(part)
    if digest.hexdigest()!=manifest['files'][path.name]:raise ValueError('Frozen development split changed')
    with path.open(encoding='utf-8',newline='') as f:
        reader=csv.DictReader(f)
        if reader.fieldnames!=['url','label']:raise ValueError('Unexpected training schema')
        for row in reader:yield row['url'],int(row['label'])
