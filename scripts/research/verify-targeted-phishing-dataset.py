"""Validate frozen dataset integrity and independence; never score test URLs."""
import argparse
from collections import Counter,defaultdict
import csv
import hashlib
import io
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit
import zipfile

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from models.phishing_url.datasets.targeted import registered_domain


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for part in iter(lambda:f.read(1024*1024),b''):h.update(part)
    return h.hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--revision',choices=['v1','v2'],default='v2');args=parser.parse_args()
    root=ROOT/('models/phishing_url/data/targeted_20261018_'+args.revision)
    manifest=json.loads((root/'dataset_manifest.json').read_text())
    for relative,expected in manifest['files'].items():
        path=(root/relative).resolve()
        if not path.is_relative_to(root.resolve()) or digest(path)!=expected:raise ValueError('Frozen file mismatch: '+relative)
    domains=defaultdict(set);ids=defaultdict(set);counts={};exported_labels={}
    roles=['train','calibration','validation','historical_regression','regression_reference','sealed_test']
    for role in roles:
        path=root/('sealed_test/url_labels.csv' if role=='sealed_test' else role+'.csv')
        if not path.exists():continue
        labels=Counter()
        with path.open(encoding='utf-8',newline='') as f:
            reader=csv.DictReader(f)
            if reader.fieldnames!=['url','label']:raise ValueError('Not a two-column URL/label file')
            for row in reader:
                if row['label'] not in {'0','1'}:raise ValueError('Unknown binary label')
                parsed=urlsplit(row['url']);host=parsed.hostname
                if parsed.scheme not in {'https','http'} or not host:raise ValueError('Malformed exported URL')
                rid=hashlib.sha256(row['url'].encode()).hexdigest()
                if rid in ids[role]:raise ValueError('Duplicate within split')
                if rid in exported_labels and exported_labels[rid]!=int(row['label']):raise ValueError('Conflicting exported labels')
                exported_labels[rid]=int(row['label'])
                ids[role].add(rid);domains[role].add(registered_domain(host));labels[row['label']]+=1
        counts[role]=dict(labels)
        if dict(labels)!=manifest['split_counts'][role]:raise ValueError('Split count mismatch')
        print(json.dumps({'stage':'verified_split','split':role,'rows':sum(labels.values())}),flush=True)
    learning=['train','calibration','validation','sealed_test']
    for i,a in enumerate(learning):
        for b in learning[i+1:]:
            if domains[a]&domains[b] or ids[a]&ids[b]:raise ValueError('Cross-split domain/URL leakage')
    # Scan *all raw historical URL sources*, including records previously excluded
    # for conflicts, to strengthen independence beyond the development cache.
    test_domains=domains['sealed_test'];historical_collisions=set();label_conflicts=set();matching_records=0
    def check(url,label):
        nonlocal matching_records
        try:
            p=urlsplit(url);host=(p.hostname or '').rstrip('.').encode('idna').decode('ascii').lower()
            d=registered_domain(host)
            if d in test_domains:historical_collisions.add(d)
            if len(url)<=2048 and p.username is None:
                authority='['+host+']' if ':' in host else host
                port=p.port
                if port and port!=(443 if p.scheme=='https' else 80):authority+=':'+str(port)
                canonical=p._replace(netloc=authority,path=p.path or '/').geturl()
                rid=hashlib.sha256(canonical.encode()).hexdigest()
                if rid in exported_labels:
                    matching_records+=1
                    if exported_labels[rid]!=label:label_conflicts.add(rid)
        except (ValueError,UnicodeError):pass
    with (ROOT/'models/phishing_url/data/primary/prepared/prepared.csv').open(encoding='utf-8') as f:
        for row in csv.DictReader(f):check(row['url'],int(row['label']))
    with zipfile.ZipFile(ROOT/'models/phishing_url/data/phiusiil/source.zip') as z:
        with io.TextIOWrapper(z.open('PhiUSIIL_Phishing_URL_Dataset.csv'),encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):check(row['URL'],1-int(row['label']))
    if historical_collisions:raise ValueError('Reserved test domains appeared in raw historical sources')
    if label_conflicts:raise ValueError('Normalized labels conflict with original source records')
    prior_domains=set()
    with (ROOT/'models/phishing_url/data/improvement_20261018/fresh_holdout_v2/holdout.csv').open(encoding='utf-8') as f:
        for row in csv.DictReader(f):prior_domains.add(registered_domain(urlsplit(row['url']).hostname))
    prior_domains.update(json.loads((ROOT/'models/phishing_url/research/masked_candidate.json').read_text())['challenge_domains_excluded_from_fit'])
    if test_domains&prior_domains:raise ValueError('Previously evaluated challenge domain entered new test')
    # Verify that every exported row has a matching provenance entry without
    # importing metadata/source/labels as model input features.
    provenance_ids=defaultdict(set);group_sets=defaultdict(set)
    for name in ('provenance.jsonl','sealed_test/provenance.jsonl'):
        with (root/name).open(encoding='utf-8') as f:
            for line in f:
                row=json.loads(line);role=row['split'];provenance_ids[role].add(row['row_id']);group_sets[role].add(row['group_id'])
    for role in roles:
        if provenance_ids[role]!=ids[role]:raise ValueError('Missing or unmatched provenance rows')
    for i,a in enumerate(learning):
        for b in learning[i+1:]:
            if group_sets[a]&group_sets[b]:raise ValueError('Known group shared across learning/test splits')
    summary={'dataset_revision':manifest['dataset_revision'],'dataset_manifest_sha256':digest(root/'dataset_manifest.json'),'file_hashes_verified':True,'csv_counts_verified':True,
             'provenance_complete':True,'learning_domain_overlap':0,'learning_url_overlap':0,'known_group_overlap':0,
             'test_raw_historical_domain_overlap':0,'test_previous_challenge_domain_overlap':0,
             'test_status':'sealed_not_evaluated','model_predictions_generated':0,
             'minimum_research_test_coverage_met':manifest['minimum_research_test_coverage_met'],
             'not_production_acceptance':'Data integrity verified; labels retain source/reference uncertainty and no accuracy has been measured.'}
    (root/'verification.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    public=ROOT/('models/phishing_url/research/targeted_dataset_verification_20261018_'+args.revision+'.json')
    public.write_text(json.dumps(summary,indent=2),encoding='utf-8')
    audit={'exported_urls':len(exported_labels),'historical_matching_records':matching_records,'normalized_label_conflicts':len(label_conflicts),
           'method':'Compare canonical full URL labels against both complete original URL sources, including excluded records; no model predictions.'}
    (root/'normalization_label_audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    (ROOT/('models/phishing_url/research/targeted_label_audit_20261018_'+args.revision+'.json')).write_text(json.dumps(audit,indent=2),encoding='utf-8')
    print(json.dumps(summary),flush=True)

if __name__=='__main__':main()
