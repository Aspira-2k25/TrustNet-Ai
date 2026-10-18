"""Package the frozen independently compared regional model; preserve v5 rollback."""
import importlib.util
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('targeted_base',ROOT/'scripts/research/train-targeted-phishing.py')
t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)
from models.phishing_url.inference.regional_model import RegionalModel


def main():
    source=ROOT/'models/phishing_url/checkpoints/research_v17'
    destination=ROOT/'models/phishing_url/checkpoints/regional_v1'
    if destination.exists():raise SystemExit('Published bundle is immutable; use a new version')
    development=t.json.loads((ROOT/'models/phishing_url/research/regional_expanded_20261018.json').read_text())
    independent=t.json.loads((ROOT/'models/phishing_url/research/regional_independent_20261018.json').read_text())
    digest=t.r.digest(source/'manifest.json')
    if not all(development['gates'].values()) or not independent['relative_comparison_passed']:
        raise ValueError('Model acceptance gates failed')
    if digest!=development['selection']['manifest_sha256'] or digest!=independent['protocol']['model_manifest_sha256']:
        raise ValueError('Frozen acceptance bundle changed')
    manifest=t.json.loads((source/'manifest.json').read_text());RegionalModel(source,manifest)
    destination.mkdir()
    for e in manifest['components'].values():
        path=source/e['artifact']
        if t.r.digest(path)!=e['sha256']:raise ValueError('Component changed')
        shutil.copyfile(path,destination/e['artifact'])
    # Publish manifest last; an incomplete copy cannot be loaded as a bundle.
    shutil.copyfile(source/'manifest.json',destination/'manifest.json')
    RegionalModel(destination,manifest)
    t.r.dump(ROOT/'models/phishing_url/research/regional_promotion_20261018.json',{
        'model_version':'regional-v1','manifest_sha256':digest,'relative_independent_comparison_passed':True,
        'independent_test_consumed':True,'production_accuracy_certification':False,
        'routed_calibration_established':False,'previous_bundle_preserved':'modern_v5',
        'activation':'Local compose modern model binding; requires phishing service restart/rebuild.',
        'scope':'Phishing only; no scam/image changes.'})
    t.r.log('regional_packaged',manifest_sha256=digest)


if __name__=='__main__':main()
