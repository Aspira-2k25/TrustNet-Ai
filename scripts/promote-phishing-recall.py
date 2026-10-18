"""Package the frozen recall candidate only after both acceptance stages pass."""
import importlib.util
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('recall_training',ROOT/'scripts/improve-phishing-recall.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
t=r.t
from models.phishing_url.inference.recall_model import RecallModel


def main():
    destination=ROOT/'models/phishing_url/checkpoints/regional_recall_v1'
    if destination.exists():raise SystemExit('Published recall bundle is immutable')
    development=t.json.loads(r.REPORT.read_text());independent=t.json.loads((ROOT/'models/phishing_url/research/recall_independent_20261018.json').read_text())
    digest=t.r.digest(r.OUT/'manifest.json')
    if not development['eligible'] or not independent['comparison_passed'] or not all(independent['gates'].values()):raise ValueError('Recall acceptance failed')
    if digest!=development['selection']['manifest_sha256'] or digest!=independent['protocol']['candidate_manifest_sha256']:raise ValueError('Candidate changed after acceptance')
    if t.r.digest(r.ACTIVE/'manifest.json')!=development['protocol']['active_manifest_sha256']:raise ValueError('Active comparator changed')
    manifest=t.json.loads((r.OUT/'manifest.json').read_text());RecallModel(r.OUT,manifest);destination.mkdir()
    for e in manifest['components'].values():
        if t.r.digest(r.OUT/e['artifact'])!=e['sha256']:raise ValueError('Component changed')
        shutil.copyfile(r.OUT/e['artifact'],destination/e['artifact'])
    shutil.copyfile(r.OUT/'manifest.json',destination/'manifest.json');RecallModel(destination,manifest)
    t.r.dump(ROOT/'models/phishing_url/research/recall_promotion_20261018.json',{
        'model_version':'regional-recall-v1','manifest_sha256':digest,'acceptance_passed':True,
        'old_regional_v1_bundle_preserved':True,'old_modern_v5_bundle_preserved':True,
        'independent_test_consumed':True,'score_calibration_established':False,
        'modest_observed_improvement_not_population_certification':True,
        'inference_source_sha256':t.r.digest(ROOT/'models/phishing_url/inference/recall_model.py')})
    t.r.log('recall_packaged',manifest_sha256=digest)


if __name__=='__main__':main()
