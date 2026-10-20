"""Prepare a pinned public evaluation subset outside the application tree.

Source images retain original bytes. Derived versions intentionally test transport
degradation. All versions and masks inherit their source family's split.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
from pathlib import Path
import time

from PIL import Image, ImageDraw, ImageEnhance
import requests

DATASET = 'Jouesmak/DiTFake'
REVISION = 'ca9ea06c8f926c3a11ca4b657074cc7cbb99e5c7'
GENERATORS = ['FLUX.1-schnell', 'PixArt-Sigma-XL-2-1024-MS', 'stable-diffusion-3-medium-diffusers']


def digest(data):
    return hashlib.sha256(data).hexdigest()


def fetch(url):
    for attempt in range(4):
        try:
            response = requests.get(url, timeout=(10, 60))
            response.raise_for_status()
            return response.content
        except requests.RequestException:
            if attempt == 3:
                raise
            time.sleep(attempt+1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--rebuild-manifest', action='store_true', help='Reuse originals and rebuild derived fixtures after a protocol correction')
    args = parser.parse_args()
    out = args.output.resolve()
    root = Path(__file__).resolve().parents[1]
    if out.is_relative_to(root):
        raise SystemExit('Raw evaluation images must stay outside the application repository')
    out.mkdir(parents=True, exist_ok=True)
    manifest = out/'manifest.json'
    if manifest.exists() and not args.rebuild_manifest:
        print('Frozen manifest already exists; reusing it.')
        return
    source = json.loads(fetch(f'https://huggingface.co/api/datasets/{DATASET}/revision/{REVISION}'))
    files = [r['rfilename'] for r in source['siblings']]
    real_files = sorted({p for p in files if '/0_real/' in p}, key=lambda p:digest(p.encode()))
    selected, seen = [], set()
    for path in real_files:
        name = Path(path).name
        if name in seen:
            continue
        seen.add(name)
        selected.append((path, 'real', 'validation' if len(selected)<32 else 'test', 'coco:'+name))
        if len(selected) == 96:
            break
    # Matching fake IDs may reuse prompts across generators. Keep them together.
    fake_ids = sorted({Path(p).name for p in files if '/1_fake/' in p}, key=lambda p:digest(p.encode()))
    for generator in GENERATORS:
        ids = fake_ids[16:48] if generator == GENERATORS[0] else fake_ids[:32]
        for index, name in enumerate(ids):
            split = 'test' if generator == GENERATORS[0] or index>=16 else 'validation'
            selected.append((f'DiTFake/test/{generator}/1_fake/{name}', generator, split, 'prompt:'+name))

    def download(record):
        path, generator, split, family = record
        dest = out/'originals'/(digest(path.encode())[:20]+Path(path).suffix)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            data = fetch(f'https://huggingface.co/datasets/{DATASET}/resolve/{REVISION}/{path}')
            Image.open(io.BytesIO(data)).verify()
            dest.write_bytes(data)
        data = dest.read_bytes()
        with Image.open(dest) as image:
            width,height = image.size
        return dict(path=str(dest.relative_to(out)), source_path=path, sha256=digest(data),
            generator=generator, split=split, family=family, ai=generator!='real', manipulation=False,
            variant='original', width=width, height=height, mask=None)

    with ThreadPoolExecutor(max_workers=6) as pool:
        rows = []
        for index, row in enumerate(pool.map(download, selected)):
            rows.append(row)
            if (index+1)%24==0:
                print(f'Downloaded {index+1}/{len(selected)}', flush=True)
    originals = list(rows)
    for index, row in enumerate(originals):
        with Image.open(out/row['path']) as original:
            image = original.convert('RGB')
        # Same transformations and encoding distribution for real and generated.
        for variant in ('matched_jpeg70', 'screenshot', 'filtered'):
            version = image.copy()
            if variant == 'screenshot':
                version.thumbnail((640,640))
                screen = Image.new('RGB',(version.width+32,version.height+80),'#ededed')
                screen.paste(version,(16,48))
                ImageDraw.Draw(screen).rectangle((16,16,120,28),fill='#777777')
                version = screen
            elif variant == 'filtered':
                version = ImageEnhance.Contrast(version).enhance(1.08)
                version = ImageEnhance.Color(version).enhance(0.85)
            dest = out/'variants'/f'{index:03}-{variant}.jpg'
            dest.parent.mkdir(exist_ok=True)
            version.save(dest, quality=70 if variant=='matched_jpeg70' else 90)
            rows.append({**row, 'path':str(dest.relative_to(out)), 'sha256':digest(dest.read_bytes()),
                         'variant':variant, 'width':version.width, 'height':version.height})
        if row['generator'] == 'real' and (index < 16 or 32 <= index < 48):
            w,h = image.size
            for kind in ('copy_move','splice'):
                edited = image.copy()
                bw,bh = max(24,w//4),max(24,h//4)
                x,y = w//2,h//2
                patch = image.crop((w//8,h//8,w//8+bw,h//8+bh))
                if kind == 'splice':
                    donor = originals[index+7]
                    with Image.open(out/donor['path']) as d:
                        patch = d.convert('RGB').resize((bw,bh))
                edited.paste(patch,(x,y))
                mask = Image.new('L',(w,h),0)
                ImageDraw.Draw(mask).rectangle((x,y,x+bw-1,y+bh-1),fill=255)
                dest = out/'variants'/f'{index:03}-{kind}.png'
                mask_path = out/'variants'/f'{index:03}-{kind}-mask.png'
                edited.save(dest); mask.save(mask_path)
                assert originals[index+7]['split'] == row['split']
                rows.append({**row,'path':str(dest.relative_to(out)), 'sha256':digest(dest.read_bytes()),
                    'variant':kind, 'manipulation':True, 'mask':str(mask_path.relative_to(out))})
    by_family = {}
    for row in rows:
        by_family.setdefault(row['family'],set()).add(row['split'])
    assert all(len(s)==1 for s in by_family.values())
    exact = {}
    for row in rows:
        exact.setdefault(row['sha256'],set()).add(row['split'])
    assert all(len(s)==1 for s in exact.values()), 'Exact bytes cross splits'
    result = dict(dataset=DATASET, revision=REVISION, license='apache-2.0 dataset card; underlying COCO photo rights remain applicable',
        license_url=f'https://huggingface.co/datasets/{DATASET}/blob/{REVISION}/README.md',
        held_out_generator=GENERATORS[0], rows=rows,
        limits=['COCO photos do not prove phone/DSLR device coverage.',
            'Only Flux, PixArt and SD3 generator coverage; GPT-image, Midjourney, Gemini, GANs and face swaps not established.',
            'Pretrained models may have unknown upstream overlap. Prompt grouping uses available file IDs.',
            'Controlled copy-move/splice masks are synthetic diagnostics, not authentic inpainting annotations.'])
    manifest.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'rows':len(rows),'originals':len(originals),'manifest':str(manifest)},indent=2))


if __name__ == '__main__':
    main()
