"""One-shot test of frozen rescue policy against the currently deployed model."""
import csv
import importlib.util
from pathlib import Path
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('recall_training',ROOT/'scripts/research/improve-phishing-recall.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
t=r.t
from models.phishing_url.inference.recall_model import RecallModel
from models.phishing_url.inference.regional_model import region
from models.phishing_url.datasets.targeted import normalize,campaign_signature
TEST=ROOT/'models/phishing_url/data/recall_independent_20261018_v2'
REPORT=ROOT/'models/phishing_url/research/recall_independent_20261018.json'


def main():
    development=t.json.loads(r.REPORT.read_text())
    if not development.get('eligible') or not all(development['gates'].values()):raise SystemExit('Development failed; test stays sealed')
    if REPORT.exists():raise SystemExit('Completed independent comparison is immutable')
    selected=development['selection'];path=r.OUT/'manifest.json'
    if t.r.digest(path)!=selected['manifest_sha256']:raise ValueError('Frozen rescue candidate changed')
    if t.r.digest(r.ACTIVE/'manifest.json')!=development['protocol']['active_manifest_sha256']:raise ValueError('Active comparator changed')
    manifest=t.json.loads(path.read_text());model=RecallModel(r.OUT,manifest)
    data=t.json.loads((TEST/'manifest.json').read_text())
    if not data['minimum_coverage_met'] or data['model_predictions_generated']!=0:raise ValueError('Invalid independent reservation')
    if t.r.digest(TEST/'sealed_test/url_labels.csv')!=data['url_labels_sha256'] or t.r.digest(TEST/'sealed_test/provenance.jsonl')!=data['provenance_sha256']:
        raise ValueError('Independent inputs changed')
    exclusions_path=ROOT/'models/phishing_url/data/recall_independent_20261018_v1/exclusions.json'
    if t.r.digest(exclusions_path)!=data['exclusions_sha256']:raise ValueError('Exclusion proof changed')
    exclusions=t.json.loads(exclusions_path.read_text());known=set(exclusions['domains']);campaigns=set(exclusions['campaigns'])
    protocol={'candidate_manifest_sha256':selected['manifest_sha256'],'active_manifest_sha256':development['protocol']['active_manifest_sha256'],
              'test_manifest_sha256':t.r.digest(TEST/'manifest.json'),
              'acceptance':{'accuracy_strictly_improves':True,'recall_strictly_improves':True,
                            'maximum_fpr_increase':.01,'no_additional_query_false_positives':True,'brier_must_not_increase':True},
              'no_test_based_tuning':True,'automatic_promotion':False,
              'label_caveat':'Provider reports and verified operator reference pages; not independent content adjudication.',
              'query_negative_coverage_limited':data['query_coverage_limited']}
    consumption=TEST/'sealed_test/consumption.json'
    with consumption.open('x',encoding='utf-8') as f:t.json.dump({'status':'evaluation_started','protocol':protocol},f,indent=2)
    t.r.dump(r.OUT/'independent_protocol.json',protocol)
    with (TEST/'sealed_test/url_labels.csv').open(encoding='utf-8',newline='') as f:rows=list(csv.DictReader(f))
    provenance=[t.json.loads(line) for line in (TEST/'sealed_test/provenance.jsonl').read_text().splitlines()]
    if len(rows)!=len(provenance):raise ValueError('Missing provenance')
    wires=set()
    for row,evidence in zip(rows,provenance):
        url,wire,domain=normalize(row['url']);sig=campaign_signature(url)
        if domain in known or (sig and sig in campaigns) or wire in wires:raise ValueError('Independent separation failed')
        if evidence['url']!=row['url'] or evidence['label']!=int(row['label']):raise ValueError('Label/provenance mismatch')
        if row['label']=='0' and (not evidence['evidence'].get('tls_validated') or evidence['evidence'].get('http_status')!=200):raise ValueError('Reference evidence missing')
        wires.add(wire)
    urls=[row['url'] for row in rows];y=t.np.asarray([int(row['label']) for row in rows]);pred,_,_,_=model.expert_predictions(urls)
    primary=[];old_thresholds=[];candidate=[];thresholds=[];rescued=[]
    for i,u in enumerate(urls):
        shape=region(u);route=manifest['routing'][shape];p=float(pred[route['expert']][i]);th=route['threshold']
        primary.append(p);old_thresholds.append(th);rule=manifest['rescue'][shape];used=False
        if p<th and rule is not None and pred[rule['expert']][i]>=rule['threshold']:
            p=float(pred[rule['expert']][i]);th=rule['threshold'];used=True
        candidate.append(p);thresholds.append(th);rescued.append(used)
    primary=t.np.asarray(primary);old_thresholds=t.np.asarray(old_thresholds);candidate=t.np.asarray(candidate);thresholds=t.np.asarray(thresholds)
    before=t.r.metrics(y,primary,old_thresholds);after=t.r.metrics(y,candidate,thresholds)
    bp=primary>=old_thresholds;cp=candidate>=thresholds;query=t.np.asarray([bool(urlsplit(u).query) for u in urls])
    added_query_fp=int(sum((~bp)&cp&(y==0)&query))
    gates={'accuracy_improved':after['accuracy']>before['accuracy'],'recall_improved':after['recall']>before['recall'],
           'fpr_increase_bounded':after['fpr']<=before['fpr']+.01,'no_extra_query_false_positives':added_query_fp==0,
           'brier_not_worse':after['brier']<=before['brier'],'primary_alerts_preserved':bool(t.np.all(cp|~bp))}
    paired={'additional_phishing_caught':int(sum((~bp)&cp&(y==1))),
            'additional_false_alerts':int(sum((~bp)&cp&(y==0))),'additional_query_false_alerts':added_query_fp}
    report={'protocol':protocol,'rows':len(rows),'class_counts':data['counts'],'baseline':before,'candidate':after,
            'gates':gates,'paired_changes':paired,'comparison_passed':all(gates.values()),'independent_test_consumed':True,
            'domain_overlap':0,'known_campaign_overlap':0,'promoted':False,
            'limitations':['Small convenience test; source labels uncertain.','Only 13 novel benign query references across five domains.','No temporal/campaign guarantee; no full live forensic/browser benchmark.']}
    t.r.dump(REPORT,report)
    t.r.dump(consumption,{'status':'evaluated_consumed','protocol':protocol,'report':str(REPORT.relative_to(ROOT)),
                        'comparison_passed':report['comparison_passed'],'do_not_reuse_as_fresh_acceptance':True})
    t.r.log('recall_independent_complete',baseline=before,candidate=after,gates=gates,paired=paired)


if __name__=='__main__':main()
