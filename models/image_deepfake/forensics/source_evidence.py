"""Original-byte validation, provenance observations and explicit quality limits."""
import hashlib
import io
import json
import re
import warnings

from PIL import Image,ImageOps,ExifTags

MAX_BYTES=10*1024*1024
MAX_PIXELS=24_000_000
FORMATS={'JPEG':'image/jpeg','PNG':'image/png','WEBP':'image/webp'}
AI_MARKERS=re.compile(r'\b(?:chatgpt|dall[ -]?e|midjourney|stable diffusion|comfyui|automatic1111|firefly|generative fill|flux\.1|imagen)\b',re.I)


def inspect_c2pa(data,mime_type):
    output=dict(c2pa_status='absent',signature_trusted=False,asserts_ai_generation=False,
                asserts_generative_edit=False,validation_state=None)
    try:
        from c2pa import Context,Reader
        context=Context.from_dict({'verify':{'remote_manifest_fetch':False,'ocsp_fetch':False,
            'verify_trust':True,'verify_timestamp_trust':True}})
        with Reader(mime_type,io.BytesIO(data),context=context) as reader:
            doc=json.loads(reader.json())
            active=doc.get('manifests',{}).get(doc.get('active_manifest'),{})
            if not active:
                return output
            state=reader.get_validation_state()
            output.update(c2pa_status='present',validation_state=str(state),
                signature_trusted=str(state).casefold()=='trusted',
                signer=(active.get('signature_info') or {}).get('issuer'),
                validation_status=doc.get('validation_status',[]))
            for assertion in active.get('assertions',[]):
                if not str(assertion.get('label','')).startswith('c2pa.actions'):
                    continue
                for action in (assertion.get('data') or {}).get('actions',[]):
                    source=str(action.get('digitalSourceType','')).rsplit('/',1)[-1]
                    if source=='trainedAlgorithmicMedia':
                        output['asserts_ai_generation']=True
                    elif source=='compositeWithTrainedAlgorithmicMedia':
                        output['asserts_generative_edit']=True
    except ImportError:
        output['c2pa_status']='unavailable'
    except Exception as exc:
        # Missing manifests are common. A C2PA-looking but invalid packet is
        # recorded rather than trusted. Remote manifests/OCSP are never fetched.
        if b'c2pa' in data.lower() or b'jumb' in data[:65536].lower():
            output.update(c2pa_status='unverifiable',reason=f'Content Credential could not be validated ({type(exc).__name__})')
    return output


def inspect_source(data):
    if not data or len(data)>MAX_BYTES:
        raise ValueError('Upload a nonempty image of at most 10 MB')
    with warnings.catch_warnings():
        warnings.simplefilter('error',Image.DecompressionBombWarning)
        with Image.open(io.BytesIO(data)) as image:
            if image.format not in FORMATS:
                raise ValueError('Only JPEG, PNG and WebP images are supported')
            fmt=image.format
            width,height=image.size
            if width*height>MAX_PIXELS or min(width,height)<32 or max(width,height)>16384:
                raise ValueError('Image dimensions exceed the supported 32 pixel minimum or 24 megapixel maximum')
            if getattr(image,'n_frames',1)!=1:
                raise ValueError('Animated images are unsupported; upload one frame explicitly')
            image.verify()
        with Image.open(io.BytesIO(data)) as image:
            exif={ExifTags.TAGS.get(k,str(k)):str(v)[:1000] for k,v in image.getexif().items()}
            textual={str(k):str(v)[:16000] for k,v in image.info.items() if isinstance(v,(str,bytes)) and k!='icc_profile'}
            clues=[]
            for key,value in {**exif,**textual}.items():
                match=AI_MARKERS.search(value)
                if match:
                    clues.append(dict(field=key,marker=match.group(),status='unverified editable metadata'))
            quantization=getattr(image,'quantization',None)
            quality_limits=[]
            if min(width,height)<256:
                quality_limits.append('Small image dimensions limit generator and localization evidence')
            if quantization and sum(quantization.get(0,[0]))/len(quantization.get(0,[0]))>35:
                quality_limits.append('JPEG quantization suggests substantial compression; fine manipulation traces may be lost')
            oriented=ImageOps.exif_transpose(image)
            shape=oriented.size
    return dict(sha256=hashlib.sha256(data).hexdigest(),byte_length=len(data),format=fmt,mime_type=FORMATS[fmt],
        original_dimensions=[width,height],oriented_dimensions=list(shape),
        quality=dict(limits=quality_limits,adequate=not quality_limits,
            note='Screenshots, filtering and re-encoding can hide traces even when not identifiable from the file'),
        provenance=dict(ai_markers=clues,software=exif.get('Software'),camera_make=exif.get('Make'),
            camera_model=exif.get('Model'),has_exif=bool(exif),c2pa_status='not_checked',
            note='Missing metadata is neutral. Editable software and camera tags do not prove origin.'))
