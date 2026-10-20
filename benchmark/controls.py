"""Build matched format/size controls and JPEG localization cases from frozen sources."""
import hashlib
import json
from pathlib import Path
import sys
from PIL import Image,ImageOps


def main():
    manifest=Path(sys.argv[1])
    root=manifest.parent
    source=json.loads(manifest.read_text(encoding='utf-8'))
    controls=[]
    localization=[]
    for index,row in enumerate(source['rows']):
        if row['variant']=='original':
            with Image.open(root/row['path']) as image:
                # Controlled evaluation view only. Application source bytes never
                # undergo this transform. Equal geometry removes a size shortcut.
                view=ImageOps.fit(image.convert('RGB'),(512,512),method=Image.Resampling.LANCZOS)
            for quality in (50,70,90):
                if quality!=70 and index%3!=0:
                    continue
                target=root/'controls'/f'{index:03}-q{quality}.jpg'
                target.parent.mkdir(exist_ok=True)
                view.save(target,quality=quality)
                data=target.read_bytes()
                assert len(data)<262144
                # Padding after JPEG EOI is ignored by decoding. Equal byte length
                # prevents a metadata-only classifier from using source file size.
                target.write_bytes(data+b'\0'*(262144-len(data)))
                controls.append({**row,'path':str(target.relative_to(root)),
                    'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
                    'variant':f'matched_jpeg{quality}','width':512,'height':512})
        if (row['generator']=='real' and row['variant']=='original') or row['manipulation']:
            with Image.open(root/row['path']) as image:
                view=image.convert('RGB')
                target=root/'localization-controls'/Path(row['path']).with_suffix('.jpg').name
                target.parent.mkdir(exist_ok=True)
                view.save(target,quality=70)
            localization.append({**row,'path':str(target.relative_to(root)),
                'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'variant':row['variant']+'_jpeg70'})
    for name,rows in [('manifest-controls.json',controls),('manifest-localization.json',localization)]:
        value={**source,'rows':rows,'source_manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest()}
        value['limits']=source['limits']+['Controlled classification views use the same square crop, resolution, JPEG quality and padded byte count in both classes. These controls do not cover every real-world format distribution.']
        (root/name).write_text(json.dumps(value,indent=2),encoding='utf-8')
    print(json.dumps({'classification_controls':len(controls),'localization_controls':len(localization)}))


if __name__=='__main__':
    main()
