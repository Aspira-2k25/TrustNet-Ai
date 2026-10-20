"""Install the pinned research-only TruFor localizer, preserving upstream licences.

TruFor allows informational/nonprofit use, not unrestricted commercial deployment.
No training datasets or unrelated pretrained checkpoints are installed.
"""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
from pathlib import Path
import zipfile
import time
import requests
import argparse

ROOT=Path(__file__).resolve().parents[2]
REVISION='ae54475df6f41a491d7615100feb19263dec13f7'
DEST=ROOT/'models/image_deepfake/vendor/trufor'
WEIGHTS=ROOT/'models/image_deepfake/artifacts/trufor.pth.tar'
WEIGHTS_SHA256='ac1d90e329a72e0d66e8665e123a19e94bfae3209c3ef8a4f9ca3b91578c7844'


def fetch(url):
    response=requests.get(url,timeout=(10,180))
    response.raise_for_status()
    return response.content


def download_weights():
    """Resume bounded byte ranges because the university host throttles streams."""
    url='https://www.grip.unina.it/download/prog/TruFor/TruFor_weights.zip'
    cache=ROOT/'runtime_state/image-install'
    cache.mkdir(parents=True,exist_ok=True)
    size=int(requests.head(url,timeout=20).headers['Content-Length'])
    chunk_size=4*1024*1024
    def part(start):
        end=min(size-1,start+chunk_size-1)
        target=cache/f'{start}-{end}.part'
        if target.exists() and target.stat().st_size==end-start+1:
            return target
        for attempt in range(5):
            started=time.monotonic()
            try:
                with requests.get(url,headers={'Range':f'bytes={start}-{end}'},stream=True,timeout=(10,45)) as response:
                    response.raise_for_status()
                    if response.status_code!=206 or response.headers.get('Content-Range')!=f'bytes {start}-{end}/{size}':
                        raise ValueError('Invalid ranged download response')
                    with target.open('wb') as stream:
                        for chunk in response.iter_content(65536):
                            stream.write(chunk)
                            if time.monotonic()-started>180:
                                raise TimeoutError('Download range exceeded its deadline')
                if target.stat().st_size!=end-start+1:
                    raise ValueError('Incomplete weight archive chunk')
                return target
            except (requests.RequestException,TimeoutError,ValueError):
                if target.exists():target.unlink()
                if attempt==4:raise
                time.sleep(min(8,2**attempt))
    starts=list(range(0,size,chunk_size))
    with ThreadPoolExecutor(4) as pool:
        parts=[]
        for index,target in enumerate(pool.map(part,starts)):
            parts.append(target)
            if (index+1)%8==0:print(f'Weights: {index+1}/{len(starts)} verified ranges',flush=True)
    archive=cache/'TruFor_weights.zip'
    md5=hashlib.md5()
    with archive.open('wb') as output:
        for target in parts:
            with target.open('rb') as stream:
                for block in iter(lambda:stream.read(1024*1024),b''):
                    output.write(block);md5.update(block)
    if md5.hexdigest()!='7bee48f3476c75616c3c5721ab256ff8':
        raise ValueError('Official upstream archive checksum differs')
    return archive


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-only',action='store_true')
    args=parser.parse_args()
    manifest_path=DEST/'manifest.json'
    if manifest_path.exists() and WEIGHTS.exists():
        existing=json.loads(manifest_path.read_text())
        with WEIGHTS.open('rb') as stream:weight_digest=hashlib.file_digest(stream,'sha256').hexdigest()
        source_valid=all((DEST/name).is_file() and hashlib.sha256((DEST/name).read_bytes()).hexdigest()==digest
            for name,digest in existing.get('source_sha256',{}).items())
        if existing.get('revision')==REVISION and len(existing.get('source_sha256',{}))>=10 and source_valid and weight_digest==WEIGHTS_SHA256:
            print('Verified pinned TruFor sources and weights; no download repeated. Nonprofit/informational licence applies.')
            return
    if args.verify_only:raise SystemExit('TruFor source or weight verification failed. Run this installer without --verify-only.')
    tree=json.loads(fetch(f'https://api.github.com/repos/grip-unina/TruFor/git/trees/{REVISION}?recursive=1'))['tree']
    selected=[item['path'] for item in tree if item['path'].startswith('TruFor_train_test/lib/models/') and item['path'].endswith('.py')]
    selected+=['TruFor_train_test/lib/config/default.py','TruFor_train_test/lib/config/trufor_ph3.yaml']
    licences=[item['path'] for item in tree if 'license' in item['path'].lower() and item['type']=='blob']
    hashes={}
    def install(path):
        data=fetch(f'https://raw.githubusercontent.com/grip-unina/TruFor/{REVISION}/{path}')
        relative=path.removeprefix('TruFor_train_test/lib/')
        target=DEST/relative
        if not target.resolve().is_relative_to(DEST.resolve()):
            raise ValueError('Unsafe upstream source path')
        target.parent.mkdir(parents=True,exist_ok=True)
        # Namespace only. Inference mathematics remain the upstream implementation.
        text=data.decode('utf-8').replace('from lib.models.', 'from models.image_deepfake.vendor.trufor.models.')
        target.write_text(text,encoding='utf-8')
        return relative,hashlib.sha256(target.read_bytes()).hexdigest()
    with ThreadPoolExecutor(4) as pool:
        hashes.update(pool.map(install,selected))
    for path in licences:
        target=DEST/Path(path).name
        target.write_bytes(fetch(f'https://raw.githubusercontent.com/grip-unina/TruFor/{REVISION}/{path}'))
    DEST.mkdir(parents=True,exist_ok=True)
    (DEST/'__init__.py').write_text('"""Pinned TruFor research implementation. See included upstream licence."""\n')
    WEIGHTS.parent.mkdir(parents=True,exist_ok=True)
    installed_digest=None
    if WEIGHTS.exists():
        with WEIGHTS.open('rb') as stream:installed_digest=hashlib.file_digest(stream,'sha256').hexdigest()
    if installed_digest!=WEIGHTS_SHA256:
        print('Downloading official TruFor weights (about 261 MB)...',flush=True)
        archive=download_weights()
        with zipfile.ZipFile(archive) as bundle:
            matches=[name for name in bundle.namelist() if name.endswith('trufor.pth.tar')]
            assert len(matches)==1
            downloaded=bundle.read(matches[0])
            if hashlib.sha256(downloaded).hexdigest()!=WEIGHTS_SHA256:raise ValueError('Localizer download integrity failed')
            temporary=WEIGHTS.with_suffix('.installing')
            temporary.write_bytes(downloaded)
            temporary.replace(WEIGHTS)
    weight_sha=hashlib.sha256(WEIGHTS.read_bytes()).hexdigest()
    if weight_sha!=WEIGHTS_SHA256:
        raise ValueError('TruFor weights do not match the pinned release SHA-256')
    manifest={'upstream':'https://github.com/grip-unina/TruFor','revision':REVISION,
        'license':'Informational and nonprofit purposes only. See upstream licence.',
        'weights_url':'https://www.grip.unina.it/download/prog/TruFor/TruFor_weights.zip',
        'archive_md5':'7bee48f3476c75616c3c5721ab256ff8','weights_sha256':weight_sha,'source_sha256':hashes}
    (DEST/'manifest.json').write_text(json.dumps(manifest,indent=2))
    print(json.dumps({'installed':str(WEIGHTS),'sha256':weight_sha,'source_files':len(hashes)}))


if __name__=='__main__':
    main()
