"""Check split leakage and flag near-duplicate candidates without inventing identities."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps


def audit(manifests, output):
    target = Path(output)
    if target.exists():
        raise ValueError('Refusing to overwrite dataset audit')
    seen = {'bytes': {}, 'pixels': {}, 'group': {}, 'subject': {}}
    collisions, candidates, fingerprints, counts = [], [], [], {}
    for split, manifest in manifests.items():
        if split not in {'train', 'validation', 'calibration', 'test'}:
            raise ValueError('Unknown split')
        path = Path(manifest).resolve(); rows = json.loads(path.read_text())
        counts[split] = len(rows)
        for row in rows:
            if isinstance(row, list):
                row = dict(path=row[0], label=row[1], group=row[2])
            if row.get('split', split) != split or not row.get('group'):
                raise ValueError('Split or source group missing/mismatched')
            source = (path.parent / row['path']).resolve(); blob = source.read_bytes()
            with Image.open(source) as image:
                image = ImageOps.exif_transpose(image).convert('RGB')
                pixels = hashlib.sha256(str(image.size).encode() + image.tobytes()).hexdigest()
                small = np.asarray(image.convert('L').resize((9, 8)), dtype=np.int16)
                fingerprint = np.packbits(small[:, 1:] > small[:, :-1]).tobytes()
            identities = {'bytes': hashlib.sha256(blob).hexdigest(), 'pixels': pixels,
                          'group': row['group'], 'subject': row.get('subject_id')}
            for kind, key in identities.items():
                if not key: continue
                if key in seen[kind] and seen[kind][key] != split:
                    collisions.append({'kind': kind, 'split': split, 'other_split': seen[kind][key], 'sha256': identities['bytes']})
                seen[kind][key] = split
            fingerprints.append((split, identities['bytes'], fingerprint))
    # Exact fingerprint buckets are a bounded triage, not exhaustive similarity search.
    buckets = {}
    for split, digest, fingerprint in fingerprints:
        for prior_split, prior_digest in buckets.get(fingerprint, []):
            if prior_split != split and prior_digest != digest:
                candidates.append({'sha256': digest, 'other_sha256': prior_digest,
                                   'split': split, 'other_split': prior_split})
                if len(candidates) >= 1000: break
        if len(candidates) < 1000:
            buckets.setdefault(fingerprint, []).append((split, digest))
    report = {'counts': counts, 'cross_split_collisions': collisions,
              'near_duplicate_candidates': candidates, 'passed_exact_checks': not collisions,
              'limits': 'dHash bucket matches require human review; no exhaustive near-duplicate or unknown-subject guarantee.',
              'manifest_sha256': {k: hashlib.sha256(Path(p).read_bytes()).hexdigest() for k, p in manifests.items()}}
    target.parent.mkdir(parents=True, exist_ok=True); target.write_text(json.dumps(report, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for split in ('train', 'validation', 'calibration', 'test'): parser.add_argument('--' + split)
    parser.add_argument('--output', required=True); args = parser.parse_args()
    report = audit({s: getattr(args, s) for s in ('train', 'validation', 'calibration', 'test') if getattr(args, s)}, args.output)
    raise SystemExit(0 if report['passed_exact_checks'] else 1)
