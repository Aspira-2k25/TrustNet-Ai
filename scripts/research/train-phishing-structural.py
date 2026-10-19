"""CPU candidate with fresh, domain-disjoint train/calibration/threshold/test sets."""
import csv, hashlib, io, json, sys, time, zipfile
from pathlib import Path
root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root))
import joblib
import lightgbm as lgb
import numpy as np
import tldextract
from sklearn.isotonic import IsotonicRegression
from models.phishing_url.preprocessing.structural_features import extract, NAMES, VERSION
from models.phishing_url.inference.url_text_model import canonical_text
from models.phishing_url.preprocessing.url_parser import parse_url, PREPROCESSING_VERSION
from models.phishing_url.preprocessing.extract_features import FEATURE_NAMES
from models.phishing_url.evaluation.metrics import metrics

start = time.monotonic()
out = root / 'models/phishing_url/checkpoints/structural_v3'
out.mkdir(parents=True, exist_ok=True)
suffix = tldextract.TLDExtract(suffix_list_urls=(), cache_dir=None, include_psl_private_domains=True)
records, conflicts = {}, set()
def add(url, label, source):
    try:
        key = canonical_text(url)
        host = parse_url(url).hostname
    except ValueError:
        return
    if key in records and records[key][1] != label:
        conflicts.add(key)
    elif key not in records:
        domain = suffix(host).top_domain_under_public_suffix or host
        records[key] = (url, label, domain, source)
with (root / 'models/phishing_url/data/primary/prepared/prepared.csv').open(encoding='utf-8') as f:
    for row in csv.DictReader(f): add(row['url'], int(row['label']), 'primary')
with zipfile.ZipFile(root / 'models/phishing_url/data/phiusiil/source.zip') as z:
    with io.TextIOWrapper(z.open('PhiUSIIL_Phishing_URL_Dataset.csv'), encoding='utf-8-sig') as f:
        for row in csv.DictReader(f): add(row['URL'], 1 - int(row['label']), 'phiusiil')
for key in conflicts: records.pop(key, None)
# Evaluation exclusion list ONLY. Never used by runtime features or verdicts.
challenge = {'google.com','wikipedia.org','github.com','microsoft.com','amazon.in','python.org','bbc.com','example.com','paypal.com',
             'mozilla.org','cloudflare.com','stackoverflow.com','ubuntu.com','w3.org','nasa.gov','who.int','khanacademy.org','gnu.org','kernel.org'}
groups = {k: [] for k in ('train', 'calibration', 'validation', 'test')}
for row in records.values():
    h = int(hashlib.sha256(('structural-v3-42:' + row[2]).encode()).hexdigest()[:8], 16) % 100
    split = 'test' if row[2] in challenge or h >= 85 else 'validation' if h >= 78 else 'calibration' if h >= 70 else 'train'
    groups[split].append(row)
del records
domains = {s: {r[2] for r in rows} for s, rows in groups.items()}
for a in domains:
    for b in domains:
        if a != b: assert not domains[a] & domains[b]
matrices, labels = {}, {}
for s, rows in groups.items():
    matrices[s] = np.asarray([list(extract(r[0]).values()) for r in rows], dtype=np.float32)
    labels[s] = np.asarray([r[1] for r in rows])
    print(json.dumps({'stage': 'features', 'split': s, 'rows': len(rows)}), flush=True)
model = lgb.LGBMClassifier(n_estimators=900, learning_rate=.045, num_leaves=31, max_depth=8,
                          min_child_samples=100, reg_lambda=2, colsample_bytree=.9,
                          random_state=42, n_jobs=2, verbosity=-1)
model.fit(matrices['train'], labels['train'], eval_set=[(matrices['validation'], labels['validation'])],
          callbacks=[lgb.early_stopping(50, verbose=False)])
cal = IsotonicRegression(out_of_bounds='clip').fit(model.predict_proba(matrices['calibration'])[:, 1], labels['calibration'])
vp = cal.predict(model.predict_proba(matrices['validation'])[:, 1])
options = [(float(t), metrics(labels['validation'], vp, float(t))) for t in np.linspace(.05, .95, 91)]
eligible = [(t, m) for t, m in options if m['fpr'] <= .02]
threshold, validation = max(eligible or options, key=lambda item: item[1]['f1'])
tp = cal.predict(model.predict_proba(matrices['test'])[:, 1])
tests = metrics(labels['test'], tp, threshold)
checks = ['https://' + d + '/' for d in sorted(challenge)]
cp = cal.predict(model.predict_proba(np.asarray([list(extract(u).values()) for u in checks]))[:, 1])
report = {'rows': {s: len(v) for s,v in groups.items()}, 'domain_overlap': 0,
          'https_rows_by_label': {s: {str(y): sum(r[1] == y and r[0].lower().startswith('https://') for r in rows) for y in (0,1)} for s, rows in groups.items()},
          'conflicts_removed': len(conflicts), 'threshold': threshold, 'validation': validation,
          'test': tests, 'challenge_excluded_from_train_calibration_validation': sorted(challenge),
          'challenge': [{'url': u, 'probability': float(p), 'alert': bool(p >= threshold)} for u,p in zip(checks, cp)],
          'test_by_source': {}, 'elapsed_seconds': time.monotonic()-start,
          'live_accuracy_measured': False, 'scheme_is_not_a_feature': True,
          'features': list(NAMES), 'source_note': 'Primary approved corpus plus official UCI PhiUSIIL URL/label; PhiUSIIL 1=legitimate, 0=phishing. CC BY 4.0 Prasad and Chandra 2024.'}
for source in ('primary','phiusiil'):
    mask = np.array([r[3] == source for r in groups['test']])
    report['test_by_source'][source] = metrics(labels['test'][mask], tp[mask], threshold)
for name, value in [('model.joblib', model), ('calibrator.joblib', cal)]: joblib.dump(value, out/name)
manifest = {'kind': 'structural_v3', 'model_version': 'structural-v3', 'detector_id': 'phishing.structural.v3',
            'preprocessing_version': PREPROCESSING_VERSION, 'feature_names': list(FEATURE_NAMES),
            'structural_preprocessing': VERSION, 'structural_features': list(NAMES), 'threshold': threshold,
            'artifact': 'model.joblib', 'sha256': hashlib.sha256((out/'model.joblib').read_bytes()).hexdigest(),
            'calibrator': 'calibrator.joblib', 'calibrator_sha256': hashlib.sha256((out/'calibrator.joblib').read_bytes()).hexdigest()}
(out/'manifest.json').write_text(json.dumps(manifest, indent=2))
(root/'models/phishing_url/research/structural_candidate.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2), flush=True)
