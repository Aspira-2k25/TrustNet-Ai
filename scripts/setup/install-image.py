"""Install pinned image-classifier artifacts without relying on an HF cache."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import urllib.request

ROOT=Path(__file__).resolve().parents[2]
MODEL=ROOT/'models/image_deepfake'


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-only',action='store_true')
    a=parser.parse_args()
    calibration=json.loads((MODEL/'calibration/evidence-v2.json').read_text(encoding='utf-8'))
    if calibration.get('modern_head_sha256'):
        if digest(MODEL/'calibration/modern-feature-head.json')!=calibration['modern_head_sha256']:
            raise SystemExit('Tracked image feature head checksum mismatch; restore the matching Git version.')
        print('Verified tracked feature head',flush=True)
    spec=json.loads((MODEL/'calibration/global-artifacts.json').read_text())
    folder=MODEL/'artifacts/global'
    folder.mkdir(parents=True,exist_ok=True)
    for name,entry in spec['files'].items():
        target=folder/name
        if target.is_file() and digest(target)==entry['sha256']:
            print('Verified',name,flush=True);continue
        if a.verify_only:raise SystemExit(f'Missing or corrupt image artifact: {name}. Run this installer without --verify-only.')
        url=f"https://huggingface.co/{spec['model_id']}/resolve/{spec['revision']}/{name}"
        temporary=target.with_suffix(target.suffix+'.download')
        try:
            with urllib.request.urlopen(url,timeout=120) as response,temporary.open('wb') as output:
                while chunk:=response.read(1024*1024):output.write(chunk)
            if temporary.stat().st_size!=entry['bytes'] or digest(temporary)!=entry['sha256']:
                raise ValueError(f'Image artifact integrity failure: {name}')
            temporary.replace(target)
        finally:temporary.unlink(missing_ok=True)
        print('Installed',name,flush=True)
    print('Image classifier ready. Manipulation localization additionally requires install-image-localizer.py (nonprofit/informational licence).')


if __name__=='__main__':main()
