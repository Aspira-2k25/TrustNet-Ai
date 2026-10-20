"""Export portable split evidence and verify diagnostic exclusion without inference."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--evaluation-root',type=Path,required=True)
    a=p.parse_args();root=a.evaluation_root
    source=root/'adaptation/manifest.json'
    rows=json.loads(source.read_text(encoding='utf-8'))['rows']
    diagnostics=json.loads((root/'diagnostics/manifest.json').read_text(encoding='utf-8'))
    export=[]
    for r in rows:
        export.append({k:r[k] for k in ['family','split','ai','category','url','sha256','source_sha256']})
    collisions=[]
    for key in ['family','sha256','source_sha256']:
        groups={}
        for r in rows:groups.setdefault(r[key],set()).add(r['split'])
        collisions += [{'key':key,'identity':v,'splits':sorted(s)} for v,s in groups.items() if len(s)>1]
    diagnostic_overlap=[d for d in diagnostics if any(d['sha256'] in [r['sha256'],r['source_sha256']] or d['family']==r['family'] for r in rows)]
    report={
        'source_manifest_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'counts':dict(Counter(r['split'] for r in rows)),
        'cross_split_collisions':collisions,'fresh_diagnostic_overlap':diagnostic_overlap,
        'fresh_batch':'One locally generated source image, three transformations; no other locally generated batch image was trained.',
        'upstream_batch_limit':'SafeIMG does not establish independence of generation sessions or upstream pretraining. Different image IDs are not proof of different generator batches.',
        'diagnostic_interpretation':'Fresh OpenAI results are development diagnostics, excluded from headline metrics because they informed development.',
        'split_policy':'Head trained on train only; threshold and Platt fitting used validation only. Test must not select thresholds.',
        'rows':export,'diagnostics':diagnostics,
    }
    destination=root/'adaptation/split-audit.json'
    destination.write_text(json.dumps(report,indent=2),encoding='utf-8')
    assert not collisions and not diagnostic_overlap
    print(json.dumps({k:v for k,v in report.items() if k not in ['rows','diagnostics']},indent=2))


if __name__=='__main__':main()
