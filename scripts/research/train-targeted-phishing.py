"""Targeted-data experiment. Never deploys models or reads sealed test URLs.

Run with the phishing research environment. Artifacts and selection are immutable.
Only development labels influence fitting and threshold selection.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('OMP_NUM_THREADS', '2')
os.environ.setdefault('MKL_NUM_THREADS', '2')
import joblib
import lightgbm as lgb
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression
from threadpoolctl import threadpool_limits
from models.phishing_url.datasets.targeted import development_rows, registered_domain
from models.phishing_url.inference.modern_model import ModernModel, meta_features
from models.phishing_url.preprocessing.structural_features import extract

spec = importlib.util.spec_from_file_location('research_helpers', ROOT/'scripts/research/improve-phishing-model.py')
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
threadpool_limits(limits=2)
DATA = ROOT/'models/phishing_url/data/targeted_20261018_v2'
OUT = ROOT/'models/phishing_url/checkpoints/research_v8'
REPORT = ROOT/'models/phishing_url/research/targeted_training_20261018.json'
SEED = 20261020


def main():
    if OUT.exists() or REPORT.exists():
        raise SystemExit('Experiment already exists. Use a new experiment version.')
    start = time.monotonic()
    OUT.mkdir(parents=True)
    manifest = json.loads((r.BASE/'manifest.json').read_text())
    base = ModernModel(r.BASE, manifest)
    protocol = {'seed': SEED, 'dataset_manifest_sha256': r.digest(DATA/'dataset_manifest.json'),
                'baseline_hashes': {n: r.digest(r.BASE/e['artifact']) for n,e in manifest['components'].items()},
                'architecture': 'Frozen masked text; retrained structural LightGBM; seven-input HGB fusion; isotonic calibration.',
                'selection': 'Validation only: maximum recall under FPR <= 0.75%; choose lowest FNR, then FPR.',
                'targeted_training_weight': 20, 'independent_test_read': False,
                'promotion': 'Manual research acceptance required; this script never changes runtime configuration.'}
    r.dump(OUT/'protocol.json', protocol)
    groups = {}; matrices = {}; labels = {}; masked = {}; baseline = {}
    for split in ('train', 'calibration', 'validation'):
        rows = list(development_rows(DATA, split)); groups[split] = rows
        r.log('prepare_targeted', split=split, rows=len(rows))
        matrices[split] = np.asarray([list(extract(u).values()) for u,_ in rows], dtype=np.float32)
        labels[split] = np.asarray([y for _,y in rows])
        masked[split] = base.models['text'].predict_proba([u for u,_ in rows])[:,1]
        if split != 'train':
            sp = base.models['structural'].predict_proba(matrices[split])[:,1]
            baseline[split] = base.models['calibrator'].predict(base.models['fusion'].predict_proba(meta_features(matrices[split],masked[split],sp))[:,1])
    targeted_path = DATA/'targeted_train.csv'
    dataset_manifest = json.loads((DATA/'dataset_manifest.json').read_text())
    if r.digest(targeted_path) != dataset_manifest['files'][targeted_path.name]:
        raise ValueError('Frozen targeted training cohort changed')
    targeted = {row['url'] for row in r.readrows(targeted_path)}
    if not targeted.issubset({u for u,_ in groups['train']}):
        raise ValueError('Targeted training cohort is outside frozen training split')
    weights = np.asarray([20. if u in targeted else 1. for u,_ in groups['train']])
    structural = lgb.LGBMClassifier(n_estimators=900, learning_rate=.045, num_leaves=31,
        max_depth=8, min_child_samples=100, reg_lambda=2, n_jobs=2, verbosity=-1, random_state=SEED)
    r.log('fit_targeted_structural', targeted_rows=len(targeted))
    structural.fit(matrices['train'], labels['train'], sample_weight=weights)
    joblib.dump(structural, OUT/'structural.joblib')
    cm = meta_features(matrices['calibration'],masked['calibration'],structural.predict_proba(matrices['calibration'])[:,1])
    vm = meta_features(matrices['validation'],masked['validation'],structural.predict_proba(matrices['validation'])[:,1])
    # All rows belonging to a domain enter the same calibration half.
    part = np.asarray([int(hashlib.sha256(registered_domain(urlsplit(u).hostname).encode()).hexdigest()[:8],16)%2 for u,_ in groups['calibration']])
    candidates = []
    for leaves in (7, 15):
        fusion = HistGradientBoostingClassifier(max_iter=150, max_leaf_nodes=leaves, max_depth=4,
            min_samples_leaf=100, l2_regularization=10, random_state=SEED)
        fusion.fit(cm[part==0],labels['calibration'][part==0])
        calibrator = IsotonicRegression(out_of_bounds='clip').fit(fusion.predict_proba(cm[part==1])[:,1],labels['calibration'][part==1])
        p = calibrator.predict(fusion.predict_proba(vm)[:,1])
        threshold = r.select_threshold(labels['validation'],p,.0075)
        score = r.metrics(labels['validation'],p,threshold)
        candidates.append((score['fnr'],score['fpr'],leaves,fusion,calibrator,threshold,score))
        r.log('targeted_validation', leaves=leaves, threshold=threshold, metrics=score)
    _,_,leaves,fusion,calibrator,threshold,score = min(candidates,key=lambda c:c[:3])
    joblib.dump(fusion, OUT/'fusion.joblib'); joblib.dump(calibrator, OUT/'calibrator.joblib')
    selection = {'threshold':threshold,'leaves':leaves,'validation':score,
                 'artifact_hashes':{p.name:r.digest(p) for p in OUT.glob('*.joblib')},
                 'frozen_before_regression':True}
    r.dump(OUT/'selection.json',selection)
    def predict(urls):
        x = np.asarray([list(extract(u).values()) for u in urls],dtype=np.float32)
        mp = base.models['text'].predict_proba(urls)[:,1]
        bp = base.models['calibrator'].predict(base.models['fusion'].predict_proba(meta_features(x,mp,base.models['structural'].predict_proba(x)[:,1]))[:,1])
        cp = calibrator.predict(fusion.predict_proba(meta_features(x,mp,structural.predict_proba(x)[:,1]))[:,1])
        return bp, cp
    regression = {}
    for split in ('historical_regression','regression_reference'):
        r.log('regression',split=split)
        rows = r.readrows(DATA/(split+'.csv')); y = np.asarray([int(v['label']) for v in rows])
        bp,cp = predict([v['url'] for v in rows])
        regression[split] = {'baseline':r.metrics(y,bp,.7),'candidate':r.metrics(y,cp,threshold)}
    old = json.loads((ROOT/'models/phishing_url/research/masked_candidate.json').read_text())
    urls = ['https://'+d+'/' for d in old['challenge_domains_excluded_from_fit']]
    urls += ['https://docs.python.org/3/','https://www.google.com/','https://paypal.com/']
    bp,cp = predict(urls)
    homepages = [{'url':u,'baseline_probability':float(b),'candidate_probability':float(c),
                  'candidate_alert':bool(c>=threshold)} for u,b,c in zip(urls,bp,cp)]
    gates = {'homepages_no_alerts':not any(v['candidate_alert'] for v in homepages),
             'historical_both_error_rates_improved':all(regression['historical_regression']['candidate'][m]<regression['historical_regression']['baseline'][m] for m in ('fpr','fnr')),
             'reference_no_error_rate_regression':all(regression['regression_reference']['candidate'][m]<=regression['regression_reference']['baseline'][m] for m in ('fpr','fnr'))}
    report = {'protocol':protocol,'selection':selection,'validation_baseline':r.metrics(labels['validation'],baseline['validation'],.7),
              'candidate_validation_results':[{'leaves':c[2],'threshold':c[5],'metrics':c[6]} for c in candidates],
              'regression':regression,'homepages':homepages,'gates':gates,
              'eligible_for_independent_evaluation':all(gates.values()),'independent_test_read':False,
              'promoted':False,'baseline_unchanged':all(r.digest(r.BASE/e['artifact'])==protocol['baseline_hashes'][n] for n,e in manifest['components'].items()),
              'elapsed_seconds':time.monotonic()-start}
    r.dump(REPORT,report)
    r.log('targeted_complete',gates=gates,independent_test_read=False,promoted=False)


if __name__ == '__main__':
    main()
