"""Private original bytes and derived model assets, owned by a saved scan."""
import base64
import re
import shutil
from pathlib import Path

KINDS={'original':'original.bin','overlay':'overlay.png','mask':'mask.png',
       'heatmap':'heatmap.png','raw_heatmap':'raw_heatmap.npz','ela':'ela.png'}


def directory(storage,scan_id):
    if not re.fullmatch(r'(?:scan-[0-9a-f]{10}|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})',scan_id):
        raise ValueError('Invalid image scan identifier')
    root=Path(storage).resolve()
    target=(root/'image_evidence'/scan_id).resolve()
    if not target.is_relative_to(root):raise ValueError('Invalid image storage path')
    return target


def persist(storage,scan_id,original,encoded):
    target=directory(storage,scan_id)
    target.mkdir(parents=True,exist_ok=False)
    try:
        (target/KINDS['original']).write_bytes(original)
        urls={}
        for kind,payload in encoded.items():
            if kind not in KINDS or kind=='original':raise ValueError('Unexpected image asset kind')
            data=base64.b64decode(payload,validate=True)
            if len(data)>128*1024*1024:raise ValueError('Image evidence exceeds storage budget')
            (target/KINDS[kind]).write_bytes(data)
            urls[kind]=f'/api/v1/scans/{scan_id}/image/{kind}'
        return target,urls
    except Exception:
        # Only this newly created scan directory is eligible for rollback.
        shutil.rmtree(target)
        raise


def asset_path(storage,scan_id,kind):
    if kind not in KINDS:raise ValueError('Unknown image asset')
    return directory(storage,scan_id)/KINDS[kind]
