"""Create immutable two-column datasets and detailed provenance without inference.

New test components cannot contain any previously observed source domain or prior
challenge domain. Previous test/challenge data stay regression-only. No models are
loaded, predictions generated, labels invented, or runtime manifests changed.
"""
import argparse
import csv
from collections import Counter,defaultdict
from datetime import datetime,timezone
import hashlib
import json
import math
from pathlib import Path
import sys
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import joblib
from models.phishing_url.datasets.targeted import VERSION,Groups,bucket,normalize,tags,campaign_signature,private_or_tokenized

OUT=ROOT/'models/phishing_url/data/targeted_20261018_v1'
OLD=ROOT/'models/phishing_url/data/improvement_20261018'
PUBLIC=ROOT/'models/phishing_url/research/targeted_dataset_20261018.json'

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for part in iter(lambda:f.read(1024*1024),b''):h.update(part)
    return h.hexdigest()
def save(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2),encoding='utf-8')
def log(stage,**values):print(json.dumps({'stage':stage,**values}),flush=True)
def read_jsonl(path):
    with path.open(encoding='utf-8') as f:
        for line in f:
            if line.strip():yield json.loads(line)


def main():
    global OUT,PUBLIC
    # Programmatic tests supply paths directly; command-line execution may select
    # a new immutable revision without overwriting the first reservation.
    if __name__=='__main__':
        parser=argparse.ArgumentParser();parser.add_argument('--revision',choices=['v1','v2'],default='v1');args=parser.parse_args()
        OUT=ROOT/('models/phishing_url/data/targeted_20261018_'+args.revision)
        PUBLIC=ROOT/('models/phishing_url/research/targeted_dataset_20261018_'+args.revision+'.json')
    if (OUT/'dataset_manifest.json').exists():raise SystemExit('Dataset already frozen; use a new version')
    collection=json.loads((OUT/'collection_manifest.json').read_text())
    if digest(OUT/'new_evidence.jsonl')!=collection['new_evidence_sha256']:raise ValueError('Collected evidence changed')
    old=joblib.load(OLD/'prepared.joblib')
    for relative,expected in old['audit']['source_hashes'].items():
        if digest(ROOT/relative)!=expected:raise ValueError('Historical source hash changed')
    groups=old['groups'];legacy_role={}
    for role,rows in groups.items():
        for row in rows:
            if row[2] in legacy_role and legacy_role[row[2]]!=role:raise ValueError('Historical domain overlap')
            legacy_role[row[2]]=role
    seen=set(legacy_role)|{row[2] for row in old['fresh']}
    prior_challenge_domains={row[2] for row in old['fresh']}
    prior_challenge_domains.update(json.loads((ROOT/'models/phishing_url/research/masked_candidate.json').read_text())['challenge_domains_excluded_from_fit'])
    seen.update(prior_challenge_domains)
    quarantine=[];new={};conflicts=set();duplicates=0
    evidence_paths=[OUT/'new_evidence.jsonl']
    supplemental=None
    if (OUT/'supplemental_manifest.json').exists():
        supplemental=json.loads((OUT/'supplemental_manifest.json').read_text())
        if digest(OUT/'supplemental_evidence.jsonl')!=supplemental['new_evidence_sha256']:raise ValueError('Supplement evidence changed')
        evidence_paths.append(OUT/'supplemental_evidence.jsonl')
    else:
        raise ValueError('Finish both configured collection batches before building this dataset version')
    if (OUT/'additional_manifest.json').exists():
        extra=json.loads((OUT/'additional_manifest.json').read_text())
        if digest(OUT/'additional_evidence.jsonl')!=extra['new_evidence_sha256']:raise ValueError('Additional evidence changed')
        evidence_paths.append(OUT/'additional_evidence.jsonl')
    import itertools
    for raw in itertools.chain.from_iterable(read_jsonl(path) for path in evidence_paths):
        try:
            url,key,domain=normalize(raw.get('url'))
            if private_or_tokenized(url):raise ValueError('ephemeral_token_or_session')
            label=int(raw['label'])
            if label not in (0,1):raise ValueError('unknown_label')
            evidence=raw.get('evidence',{})
            if label==0:
                if raw['source']!='curated_official_page' or evidence.get('http_status')!=200 or evidence.get('tls_validated') is not True:
                    raise ValueError('negative_label_missing_operator_tls_http_evidence')
                if normalize(raw['source_url'])[2]!=domain or normalize(evidence['final_url'])[2]!=domain:
                    raise ValueError('negative_label_operator_boundary_mismatch')
            elif raw['source']=='phishstats_report':
                score=float(evidence.get('provider_score',0))
                if not math.isfinite(score) or score<7:raise ValueError('provider_score_not_usable')
            elif raw['source']!='phishtank_verified_online':raise ValueError('unapproved_positive_label_source')
            # Do not present historical reports as newly verified attacks.
            if label:
                stamp=datetime.fromisoformat(str(raw['verified_at']).replace('Z','+00:00'))
                if stamp.tzinfo is None:raise ValueError('timestamp_timezone_missing')
                age=(datetime.now(timezone.utc)-stamp).total_seconds()/86400
                if not 0<=age<=120:raise ValueError('report_not_recent_or_future_timestamp')
            record={**raw,'url':url,'key':key,'domain':domain,'tags':tags(url),'campaign_signature':campaign_signature(url),
                    'row_id':hashlib.sha256(url.encode()).hexdigest()}
            if key in new:
                if new[key]['label']!=label:conflicts.add(key)
                else:
                    duplicates+=1
                    new[key].setdefault('additional_evidence',[]).append({'source':raw['source'],'verified_at':raw.get('verified_at'),'evidence':raw['evidence']})
            else:new[key]=record
        except (ValueError,TypeError,KeyError,AttributeError) as exc:quarantine.append({'url':raw.get('url'),'reason':str(exc),'source':raw.get('source')})
    # Detect conflicts with historical records without constructing a huge second
    # URL dictionary; the canonicalization preserves case-sensitive paths/queries.
    new_keys=set(new)
    for role,rows in groups.items():
        for url,label,domain,source in rows:
            p=urlsplit(url)
            host=(p.hostname or '').lower().rstrip('.')
            if ':' in host:host='['+host+']'
            port=p.port
            if port and port!=(443 if p.scheme=='https' else 80):host+=':'+str(port)
            key=p._replace(netloc=host,path=p.path or '/',fragment='').geturl()
            if key in new_keys and new[key]['label']!=label:conflicts.add(key)
    for key in conflicts:
        quarantine.append({'url':new[key]['url'],'reason':'conflicting_labels_new_or_historical','source':new[key]['source']});new.pop(key)
    log('new_labels_cleaned',rows=len(new),conflicts=len(conflicts),duplicates=duplicates,review=len(quarantine))
    # Group related domains before reserving anything. Specific repeated paths
    # connect possible campaigns; root/generic-login campaign identity is unknown.
    components=Groups();families={}
    for row in new.values():
        components.find(row['domain'])
        signature=row['campaign_signature']
        if signature:
            if signature in families:components.union(row['domain'],families[signature])
            else:families[signature]=row['domain']
    members=defaultdict(list)
    for row in new.values():members[components.find(row['domain'])].append(row)
    # Stratify by label counts at the GROUP level, never by predictions. Prioritize
    # the predeclared minimum 50/class, then half of novel examples up to 100/class.
    novel={key:rows for key,rows in members.items() if not {r['domain'] for r in rows}&seen}
    totals=Counter();novel_domains=defaultdict(set)
    for rows in novel.values():
        by_domain=Counter((r['domain'],str(r['label'])) for r in rows)
        for (domain,label),n in by_domain.items():
            totals[label]+=min(n,12 if label=='0' else 5);novel_domains[label].add(domain)
    target_counts={label:min(totals[label],100,max(50,totals[label]//2)) for label in ('0','1')}
    target_domains={label:min(10,max(1,len(novel_domains[label])//2)) for label in ('0','1')}
    reserved=set();reserved_counts=Counter();reserved_domains=defaultdict(set)
    for key in sorted(novel,key=lambda key:hashlib.sha256(('reservation-v1:'+key).encode()).hexdigest()):
        rows=novel[key];classes={str(row['label']) for row in rows}
        if not any(reserved_counts[label]<target_counts[label] or len(reserved_domains[label])<target_domains[label] for label in classes):continue
        reserved.add(key)
        for (domain,label),n in Counter((r['domain'],str(r['label'])) for r in rows).items():
            reserved_counts[label]+=min(n,12 if label=='0' else 5);reserved_domains[label].add(domain)
    assignments={};independence_rejected=0
    for component,rows in members.items():
        domains={row['domain'] for row in rows}
        roles={legacy_role[d] for d in domains if d in legacy_role}
        if domains & prior_challenge_domains or 'test' in roles:role='regression_reference'
        elif len(roles)>1:role='review_cross_partition_campaign'
        elif roles:role=next(iter(roles))
        else:
            h=bucket(component)
            role='sealed_test' if component in reserved else 'validation' if h<20 else 'calibration' if h<40 else 'train'
        if role=='sealed_test' and domains&seen:raise ValueError('Previously observed domain entered independent test')
        if domains&seen:independence_rejected+=len(rows)
        for row in rows:assignments[row['key']]=(role,component)
    # Domain caps improve diversity instead of multiplying nearly identical URLs.
    capped=[];domain_counts=Counter();role_counts=Counter()
    ordered=sorted(new.values(),key=lambda row:(0 if 'authentication_account_payment' in row['tags'] else 1 if 'root_path' in row['tags'] else 2,hashlib.sha256(row['url'].encode()).hexdigest()))
    for row in ordered:
        role,component=assignments[row['key']]
        if role.startswith('review_'):
            quarantine.append({'url':row['url'],'reason':role,'source':row['source']});continue
        cap=12 if row['label']==0 else 5
        key=(row['domain'],row['label'])
        if domain_counts[key]>=cap:
            quarantine.append({'url':row['url'],'reason':'per_domain_diversity_cap','source':row['source']});continue
        domain_counts[key]+=1;row['split']=role;row['group_id']=component;row['cohort']='targeted_new';capped.append(row);role_counts[role]+=1
    log('reservation_fixed',new_rows=len(capped),new_splits=dict(role_counts),previously_observed_new_rows=independence_rejected)
    # The reservation is written before exporting any training dataset. It has no
    # model scores, threshold selection, or performance measurements.
    reservation={'version':VERSION,'dataset_revision':OUT.name,'created_at':datetime.now(timezone.utc).isoformat(),'seed':'targeted-20261018-v1',
        'test_groups':sorted({row['group_id'] for row in capped if row['split']=='sealed_test'}),
        'test_domains':sorted({row['domain'] for row in capped if row['split']=='sealed_test'}),
        'role':'New domains relative to all historical source partitions and previous challenges; never evaluated by a model.',
        'model_scores_used':False,'fresh_collection_sha256':collection['new_evidence_sha256'],
        'novel_class_totals_after_domain_caps':dict(totals),'target_test_counts':target_counts,'target_test_domains':target_domains,
        'supplement_sha256':supplemental['new_evidence_sha256'] if supplemental else None}
    save(OUT/'sealed_test/reservation.json',reservation)
    writers={};target_writers={};handles=[];counts=defaultdict(Counter);slice_counts=defaultdict(Counter);domain_sets=defaultdict(set);ids=defaultdict(set);new_wires={r['key'] for r in capped}
    evidence_handle=(OUT/'provenance.jsonl').open('w',encoding='utf-8');handles.append(evidence_handle)
    held_evidence=(OUT/'sealed_test/provenance.jsonl').open('w',encoding='utf-8');handles.append(held_evidence)
    def writer(role):
        if role not in writers:
            path=OUT/('sealed_test/url_labels.csv' if role=='sealed_test' else role+'.csv')
            f=path.open('w',newline='',encoding='utf-8');handles.append(f)
            writers[role]=csv.writer(f);writers[role].writerow(['url','label'])
        return writers[role]
    def emit(row):
        role=row['split'];rid=row['row_id']
        if rid in ids[role]:return False
        ids[role].add(rid);writer(role).writerow([row['url'],row['label']])
        if row['cohort']=='targeted_new' and role!='sealed_test':
            if role not in target_writers:
                f=(OUT/('targeted_'+role+'.csv')).open('w',newline='',encoding='utf-8');handles.append(f)
                target_writers[role]=csv.writer(f);target_writers[role].writerow(['url','label'])
            target_writers[role].writerow([row['url'],row['label']])
        counts[role][str(row['label'])]+=1;domain_sets[role].add(row['domain'])
        for tag in row['tags']:slice_counts[role][f'{row["label"]}:{tag}']+=1
        destination=held_evidence if role=='sealed_test' else evidence_handle
        destination.write(json.dumps(row,ensure_ascii=True)+'\n');return True
    for row in capped:emit(row)
    # Retain existing usable labels in their original roles. Old tests never become
    # new independent tests or training records. No labels are inferred from scores.
    retained=Counter();excluded=Counter()
    for role,rows in groups.items():
        destination='historical_regression' if role=='test' else role
        log('retaining_historical',split=destination,rows=len(rows))
        for url,label,old_domain,source in rows:
            try:
                normalized,key,domain=normalize(url)
                if key in conflicts:excluded['historical_label_conflict']+=1;continue
                if key in new_wires:excluded['replaced_by_current_same_label_evidence']+=1;continue
                if domain in reservation['test_domains']:raise ValueError('Reserved test domain found in history')
                if private_or_tokenized(normalized):excluded['historical_ephemeral_token']+=1;continue
                row={'url':normalized,'label':int(label),'domain':domain,'source':source,'source_url':'existing_approved_corpus',
                     'label_basis':'inherited_source_label_not_live_reverified','label_quality':'historical_source_label',
                     'verified_at':None,'collected_at':None,'cohort':'retained_historical','split':destination,
                     'row_id':hashlib.sha256(normalized.encode()).hexdigest(),'group_id':domain,'tags':tags(normalized)}
                if emit(row):retained[destination]+=1
            except ValueError as exc:excluded[str(exc)]+=1
    for f in handles:f.close()
    with (OUT/'quarantine.jsonl').open('w',encoding='utf-8') as f:
        for row in quarantine:f.write(json.dumps(row,ensure_ascii=True)+'\n')
    # Validate split-level domain isolation. Regression reference may intentionally
    # overlap historical regression, but it cannot overlap new train/cal/validation.
    learning=('train','calibration','validation','sealed_test')
    overlaps={a+'__'+b:len(domain_sets[a]&domain_sets[b]) for i,a in enumerate(learning) for b in learning[i+1:]}
    if any(overlaps.values()):raise ValueError('Exported domain leakage: '+str(overlaps))
    test_domain_labels=defaultdict(set)
    for row in capped:
        if row['split']=='sealed_test':test_domain_labels[str(row['label'])].add(row['domain'])
    test_counts=counts['sealed_test'];domain_counts={label:len(test_domain_labels[label]) for label in ('0','1')}
    complete=all(test_counts[label]>=50 and domain_counts[label]>=5 for label in ('0','1'))
    files={str(p.relative_to(OUT)).replace('\\','/'):digest(p) for p in OUT.glob('*.csv')}
    files['provenance.jsonl']=digest(OUT/'provenance.jsonl')
    for p in (OUT/'sealed_test').iterdir():
        if p.is_file():files[str(p.relative_to(OUT)).replace('\\','/')]=digest(p)
    manifest={'version':VERSION,'dataset_revision':OUT.name,'created_at':datetime.now(timezone.utc).isoformat(),'label_mapping':{'0':'legitimate_reference_or_source_label','1':'phishing_provider_or_source_label'},
        'split_counts':{k:dict(v) for k,v in counts.items()},'slice_counts':{k:dict(v) for k,v in slice_counts.items()},
        'new_targeted_counts':dict(role_counts),'retained_historical':dict(retained),'excluded_historical':dict(excluded),
        'new_label_conflicts_quarantined':len(conflicts),'new_duplicate_evidence_merged':duplicates,'quarantine_rows':len(quarantine),
        'domain_overlap':overlaps,'test_domain_counts_by_class':domain_counts,'test_status':'sealed_not_evaluated',
        'previously_seen_test_domains':len(set(reservation['test_domains'])&seen),'minimum_research_test_coverage_met':complete,
        'production_acceptance_complete':False,'retraining_started':False,'files':files,
        'lineage':{'historical_manifest_sha256':digest(OLD/'dataset_manifest.json'),'collection_manifest_sha256':digest(OUT/'collection_manifest.json')},
        'limitations':['Reference negative and provider labels are not independently adjudicated.','Small targeted test has selection/source bias; not the entire web.','Near-duplicate grouping is heuristic; campaigns with generic/root paths cannot be fully resolved.','Historical labels are inherited, not live verified; source collection dates are unavailable.','Live forensic observations are label evidence/provenance, not leaked URL-model inputs.','Test remains sealed until a candidate and threshold are frozen; no performance claim has been made.']}
    save(OUT/'dataset_manifest.json',manifest)
    # Share aggregates only. Proprietary/raw URL records stay under ignored data/.
    save(PUBLIC,{k:v for k,v in manifest.items() if k not in {'files'}})
    log('dataset_frozen',counts=manifest['split_counts'],minimum_research_test_coverage_met=complete,test_status=manifest['test_status'])

if __name__=='__main__':main()
