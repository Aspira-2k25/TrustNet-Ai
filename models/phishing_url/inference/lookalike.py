"""Data-backed visual collision detection, not a domain verdict lookup."""
import json,unicodedata
from pathlib import Path
from functools import lru_cache

@lru_cache(maxsize=1)
def reference():
    value=json.loads((Path(__file__).resolve().parents[1]/'configs/domain_reference.json').read_text(encoding='utf-8'))
    return value

def skeleton(domain,mapping):
    try:domain=domain.encode('ascii').decode('idna')
    except (UnicodeError,UnicodeEncodeError):pass
    # UTS39 mappings plus common font ambiguity between i, l and digit 1.
    text=''.join(mapping.get(c,c) for c in unicodedata.normalize('NFD',domain))
    return unicodedata.normalize('NFD',text).casefold().translate(str.maketrans({'i':'l','1':'l'}))

@lru_cache(maxsize=1)
def index():
    refs=reference();groups={}
    for domain,rank in refs['domains'].items():
        if len(domain.split('.')[0])<5:continue
        groups.setdefault(skeleton(domain,refs['confusables']),[]).append((rank,domain))
    return groups

def compare(domain):
    refs=reference()
    candidates=index().get(skeleton(domain,refs['confusables']),[])
    rank=refs['domains'].get(domain,float('inf'))
    matches=[(r,d) for r,d in candidates if d!=domain and r*10<rank]
    if not matches:return None
    target_rank,target=min(matches)
    return {'actual_domain':domain,'resembles_domain':target,'reference_rank':target_rank,
            'reference_version':refs['version'],'reference_retrieved_at':refs['retrieved_at'],
            'reference_prefix_sha256':refs.get('ranking_prefix_sha256'),'confusables_sha256':refs.get('confusables_sha256'),
            'method':'Unicode confusable skeleton with i/l/1 font ambiguity; reference must be at least 10 times higher ranked.',
            'definition':'Visual similarity is an impersonation risk, not proof of malicious ownership or current phishing content.'}
