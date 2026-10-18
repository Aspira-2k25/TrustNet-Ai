"""One-shot independent comparison, gated on frozen development acceptance."""
import csv
import importlib.util
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('targeted_base',ROOT/'scripts/research/train-targeted-phishing.py')
t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)
from models.phishing_url.inference.regional_model import RegionalModel,region
MODEL=ROOT/'models/phishing_url/checkpoints/research_v17'
REPORT=ROOT/'models/phishing_url/research/regional_independent_20261018.json'


def wilson(errors,n):
    z=1.959963984540054;p=errors/n;d=1+z*z/n
    middle=(p+z*z/(2*n))/d;radius=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return [max(0,middle-radius),min(1,middle+radius)]


def main():
    development=t.json.loads((ROOT/'models/phishing_url/research/regional_expanded_20261018.json').read_text())
    if not development['eligible_for_independent_evaluation'] or not all(development['gates'].values()):
        raise SystemExit('Development gates failed; independent test stays sealed')
    if REPORT.exists():raise SystemExit('Completed independent evaluation is immutable')
    if t.r.digest(MODEL/'manifest.json')!=development['selection']['manifest_sha256']:raise ValueError('Frozen selection changed')
    manifest=t.json.loads((MODEL/'manifest.json').read_text());model=RegionalModel(MODEL,manifest)
    dataset=t.json.loads((t.DATA/'dataset_manifest.json').read_text());path=t.DATA/'sealed_test/url_labels.csv'
    if t.r.digest(path)!=dataset['files']['sealed_test/url_labels.csv']:raise ValueError('Frozen independent test changed')
    protocol={'model_manifest_sha256':development['selection']['manifest_sha256'],
              'dataset_manifest_sha256':t.r.digest(t.DATA/'dataset_manifest.json'),
              'criteria':'No increase in independent FPR or FNR, with fewer total errors; fixed routing/thresholds. No test-based tuning.',
              'uncertainty':'Wilson 95% intervals by class; small provider/reference-labeled test cannot establish population noninferiority or production calibration.',
              'automatic_promotion':False}
    # Exclusive reservation is written BEFORE opening any independent examples.
    consumption=t.DATA/'sealed_test/consumption.json'
    with consumption.open('x',encoding='utf-8') as f:t.json.dump({'status':'evaluation_started','protocol':protocol},f,indent=2)
    t.r.dump(MODEL/'independent_protocol.json',protocol)
    with path.open(encoding='utf-8',newline='') as f:rows=list(csv.DictReader(f))
    urls=[r['url'] for r in rows];y=t.np.asarray([int(r['label']) for r in rows]);pred,_,_,_=model.expert_predictions(urls)
    candidate=[];thresholds=[]
    for i,u in enumerate(urls):
        route=manifest['routing'][region(u)];candidate.append(pred[route['expert']][i]);thresholds.append(route['threshold'])
    candidate=t.np.asarray(candidate);thresholds=t.np.asarray(thresholds)
    baseline=t.r.metrics(y,pred['baseline'],.7);score=t.r.metrics(y,candidate,thresholds)
    comparison=all(score[m]<=baseline[m] for m in ('fpr','fnr')) and sum(score['confusion_matrix'][i][1-i] for i in (0,1))<sum(baseline['confusion_matrix'][i][1-i] for i in (0,1))
    intervals={}
    for name,value in [('baseline',baseline),('candidate',score)]:
        matrix=value['confusion_matrix'];intervals[name]={'fpr_95':wilson(matrix[0][1],sum(matrix[0])),
                                                        'fnr_95':wilson(matrix[1][0],sum(matrix[1]))}
    bp=pred['baseline']>=.7;cp=candidate>=thresholds
    paired={'baseline_wrong_candidate_correct':int(sum((bp!=y)&(cp==y))),
            'baseline_correct_candidate_wrong':int(sum((bp==y)&(cp!=y)))}
    report={'protocol':protocol,'rows':len(rows),'baseline':baseline,'candidate':score,'wilson_intervals':intervals,
            'paired_changes':paired,'relative_comparison_passed':comparison,'independent_test_consumed':True,
            'promoted':False,'calibration_of_routed_system_established':False}
    t.r.dump(REPORT,report)
    t.r.dump(consumption,{'status':'evaluated_consumed','protocol':protocol,'report':str(REPORT.relative_to(ROOT)),
                        'relative_comparison_passed':comparison,'do_not_reuse_as_fresh_acceptance':True})
    t.r.log('regional_independent_complete',baseline=baseline,candidate=score,comparison_passed=comparison,paired=paired)


if __name__=='__main__':main()
