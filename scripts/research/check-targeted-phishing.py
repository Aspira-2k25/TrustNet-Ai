"""Read-only fresh-cohort diagnostics for frozen v8; no independent-test access."""
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
spec = importlib.util.spec_from_file_location('targeted_experiment',ROOT/'scripts/research/train-targeted-phishing.py')
t = importlib.util.module_from_spec(spec)
spec.loader.exec_module(t)
from models.phishing_url.inference.modern_model import meta_features
from models.phishing_url.preprocessing.structural_features import extract


def main():
    report = json.loads(t.REPORT.read_text())
    selection = report['selection']
    for name,digest in selection['artifact_hashes'].items():
        if t.r.digest(t.OUT/name) != digest:
            raise ValueError('Frozen candidate artifact changed')
    manifest = json.loads((t.r.BASE/'manifest.json').read_text())
    base = t.ModernModel(t.r.BASE,manifest)
    for name,entry in manifest['components'].items():
        if t.r.digest(t.r.BASE/entry['artifact']) != report['protocol']['baseline_hashes'][name]:
            raise ValueError('Baseline changed')
    models = {n:t.joblib.load(t.OUT/(n+'.joblib')) for n in ('structural','fusion','calibrator')}
    results = {}
    for split in ('validation',):
        # Verify the complete split through the guarded loader, then select its
        # frozen targeted subset. Never accept cohort-file rows outside it.
        development = dict(t.development_rows(t.DATA,split))
        path = t.DATA/('targeted_'+split+'.csv')
        dataset_manifest = json.loads((t.DATA/'dataset_manifest.json').read_text())
        if t.r.digest(path) != dataset_manifest['files'][path.name]:
            raise ValueError('Targeted cohort file changed')
        rows = t.r.readrows(path)
        if any(development.get(v['url']) != int(v['label']) for v in rows):
            raise ValueError('Cohort is outside frozen development split')
        urls = [v['url'] for v in rows]; y = t.np.asarray([int(v['label']) for v in rows])
        x = t.np.asarray([list(extract(u).values()) for u in urls],dtype=t.np.float32)
        mp = base.models['text'].predict_proba(urls)[:,1]
        bp = base.models['calibrator'].predict(base.models['fusion'].predict_proba(meta_features(x,mp,base.models['structural'].predict_proba(x)[:,1]))[:,1])
        cp = models['calibrator'].predict(models['fusion'].predict_proba(meta_features(x,mp,models['structural'].predict_proba(x)[:,1]))[:,1])
        results[split] = {'rows':len(rows),'baseline':t.r.metrics(y,bp,.7),
                          'candidate':t.r.metrics(y,cp,selection['threshold'])}
    result = {'role':'Development diagnostic only; not independent acceptance.',
              'candidate_artifact_hashes':selection['artifact_hashes'],'results':results,
              'independent_test_read':False,'threshold_changed':False}
    destination = ROOT/'models/phishing_url/research/targeted_cohort_20261018.json'
    if destination.exists():
        raise ValueError('Completed diagnostic is immutable')
    t.r.dump(destination,result)
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
