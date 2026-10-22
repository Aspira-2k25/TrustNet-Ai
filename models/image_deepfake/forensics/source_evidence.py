"""Original-byte validation, provenance observations and explicit quality limits."""
import hashlib
import io
import json
import re
import warnings
from functools import lru_cache
from pathlib import Path

from PIL import Image,ImageOps,ExifTags
from .generator_signatures import metadata_clues

MAX_BYTES=10*1024*1024
MAX_PIXELS=24_000_000
FORMATS={'JPEG':'image/jpeg','PNG':'image/png','WEBP':'image/webp'}


import zlib


def _clean_str(val, max_len=16000):
    if isinstance(val, bytes):
        if val.startswith(b'ASCII\x00\x00\x00'):
            val = val[8:]
        elif val.startswith(b'UNICODE\x00\x00'):
            try:
                return val[9:].decode('utf-16', errors='ignore')[:max_len].strip('\x00 ')
            except Exception:
                pass
        for enc in ('utf-8', 'latin-1'):
            try:
                decoded = val.decode(enc, errors='replace')
                return decoded.replace('\x00', '')[:max_len].strip()
            except Exception:
                pass
        return str(val)[:max_len]
    return str(val)[:max_len]


def metadata_fields(image, raw_bytes=None):
    """Inspect bounded original metadata, without exposing personal EXIF values."""
    raw = image.getexif()
    fields = {ExifTags.TAGS.get(k, str(k)): _clean_str(v, 16000) for k, v in raw.items()}
    for ifd_id, prefix in [(34665, 'Exif.'), (34853, 'GPS.'), (40965, 'Interop.')]:
        try:
            for k, v in raw.get_ifd(ifd_id).items():
                fields[f'{prefix}{ExifTags.TAGS.get(k, str(k))}'] = _clean_str(v, 16000)
        except (KeyError, ValueError, TypeError, OSError):
            pass

    for key, value in image.info.items():
        if key in ('icc_profile', 'exif'):
            continue
        if isinstance(value, (str, bytes)):
            fields[str(key)] = _clean_str(value, max_len=262144)
        elif isinstance(value, (dict, list)):
            try:
                fields[str(key)] = json.dumps(value)[:262144]
            except Exception:
                pass

    try:
        from PIL.IptcImagePlugin import getiptcinfo
        for key, value in (getiptcinfo(image) or {}).items():
            fields[f'IPTC.{key}'] = _clean_str(value, 16000)
    except (ValueError, TypeError, OSError, SyntaxError):
        pass

    if raw_bytes:
        try:
            xmp_matches = re.findall(rb'(?:<x:xmpmeta[\s\S]*?</x:xmpmeta>|<\?xpacket begin[\s\S]*?\?xpacket end[\s\S]*?>|<rdf:RDF[\s\S]*?</rdf:RDF>)', raw_bytes)
            for i, match in enumerate(xmp_matches[:4]):
                xmp_text = match.decode('utf-8', errors='ignore')
                tag_name = 'XMP' if i == 0 else f'XMP.{i}'
                fields[tag_name] = xmp_text[:262144]

            if raw_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
                offset = 8
                while offset < len(raw_bytes) - 12:
                    length = int.from_bytes(raw_bytes[offset:offset+4], 'big')
                    chunk_type = raw_bytes[offset+4:offset+8]
                    chunk_data = raw_bytes[offset+8:offset+8+length]
                    offset += 12 + length
                    if chunk_type == b'zTXt' and len(chunk_data) > 2:
                        null_idx = chunk_data.find(b'\x00')
                        if 0 < null_idx < len(chunk_data) - 2:
                            kw = chunk_data[:null_idx].decode('latin-1', errors='ignore')
                            try:
                                decompressed = zlib.decompress(chunk_data[null_idx+2:])
                                fields[f'PNG.zTXt.{kw}'] = _clean_str(decompressed, 262144)
                            except Exception:
                                pass
                    elif chunk_type in (b'tEXt', b'iTXt') and len(chunk_data) > 2:
                        null_idx = chunk_data.find(b'\x00')
                        if null_idx > 0:
                            kw = chunk_data[:null_idx].decode('latin-1', errors='ignore')
                            fields[f'PNG.{chunk_type.decode("ascii", errors="ignore")}.{kw}'] = _clean_str(chunk_data[null_idx+1:], 262144)
        except Exception:
            pass

    return fields


@lru_cache(maxsize=1)
def c2pa_verification_settings():
    root=Path(__file__).resolve().parents[1]/'calibration/c2pa'
    manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    pem=(root/'official-trust-anchors.pem').read_bytes().replace(b'\r\n',b'\n')
    if hashlib.sha256(pem).hexdigest()!=manifest['sha256']:
        raise ValueError('C2PA trust-anchor integrity check failed')
    return {'trust':{'trust_anchors':pem.decode('ascii')},
        'verify':{'remote_manifest_fetch':False,'ocsp_fetch':False,
                  'verify_trust':True,'verify_timestamp_trust':True}}


def signed_source_declarations(active):
    """Read standard source declarations from the active signed manifest only.

    This extracts claims, never grants trust. Reader verification decides trust.
    JSON-LD contexts are interpreted locally; remote contexts are never fetched.
    """
    declarations=[]
    recognized={'trainedAlgorithmicMedia':'generation','compositeWithTrainedAlgorithmicMedia':'generative_edit'}
    source_properties={scheme+'://iptc.org/std/Iptc4xmpExt/2008-02-29/DigitalSourceType'
                       for scheme in ('http','https')}
    def expand_property(term,context,seen=None):
        # Only local, bounded term expansion; never resolve remote contexts.
        seen=set() if seen is None else seen
        if not isinstance(term,str) or term in seen or len(seen)>=8:return None
        if term in source_properties:return term
        seen.add(term)
        mapped=context.get(term)
        if isinstance(mapped,dict):mapped=mapped.get('@id')
        if isinstance(mapped,str):return expand_property(mapped,context,seen)
        if ':' in term:
            prefix,suffix=term.split(':',1)
            namespace=context.get(prefix)
            if isinstance(namespace,dict):namespace=namespace.get('@id')
            if isinstance(namespace,str):return namespace+suffix
        return None
    def add(value,label,depth=0):
        if depth>8 or len(declarations)>=128:return
        if isinstance(value,list):
            for item in value[:64]:add(item,label,depth+1)
            return
        if isinstance(value,dict):value=value.get('@id',value.get('@value'))
        if not isinstance(value,str):return
        match=re.fullmatch(r'https?://cv\.iptc\.org/newscodes/digitalsourcetype/([A-Za-z]+)',value)
        kind=recognized.get(match.group(1)) if match else None
        if kind and len(declarations)<128:
            entry={'assertion':label,'source_type':value,'kind':kind}
            if entry not in declarations:declarations.append(entry)
    if not isinstance(active,dict):return declarations
    assertions=active.get('assertions',[])
    if not isinstance(assertions,list):return declarations
    for assertion in assertions[:256]:
        if not isinstance(assertion,dict):continue
        label=assertion.get('label','');data=assertion.get('data')
        if not isinstance(label,str) or not isinstance(data,dict):continue
        if re.fullmatch(r'c2pa\.actions(?:\.v[0-9]+)?',label):
            actions=data.get('actions',[])
            if isinstance(actions,list):
                for action in actions[:256]:
                    if isinstance(action,dict):add(action.get('digitalSourceType'),label)
        elif re.fullmatch(r'(?:c2pa\.metadata|stds\.iptc(?:\.photometadata)?)(?:\.v[0-9]+)?',label):
            nodes=[(data,{},0)];visited=0
            while nodes and visited<256:
                node,inherited,depth=nodes.pop();visited+=1
                if not isinstance(node,dict) or depth>8:continue
                context={**inherited}
                local=node.get('@context')
                if local is None and '@context' in node:context={}
                elif isinstance(local,dict):context.update(local)
                elif isinstance(local,list):
                    for entry in local[:64]:
                        if entry is None:context={}
                        elif isinstance(entry,dict):context.update(entry)
                for key,value in node.items():
                    if expand_property(key,context) in source_properties:
                        add(value,label)
                graph=node.get('@graph',[])
                if isinstance(graph,list):nodes.extend((item,context,depth+1) for item in graph[:128])
    return declarations


def inspect_c2pa(data,mime_type):
    output=dict(c2pa_status='absent',signature_trusted=False,asserts_ai_generation=False,
                asserts_generative_edit=False,validation_state=None)
    try:
        from c2pa import Context,Reader
        context=Context.from_dict(c2pa_verification_settings())
        with Reader(mime_type,io.BytesIO(data),context=context) as reader:
            doc=json.loads(reader.json())
            active=doc.get('manifests',{}).get(doc.get('active_manifest'),{})
            if not active:
                return output
            state=reader.get_validation_state()
            output.update(c2pa_status='present',validation_state=str(state),
                signature_trusted=str(state).casefold()=='trusted',
                signer=(active.get('signature_info') or {}).get('issuer'),
                trust_source='Official C2PA trust list (pinned repository snapshot)',
                validation_status=doc.get('validation_status',[]))
            declarations=signed_source_declarations(active)
            output.update(source_declarations=declarations,
                asserts_ai_generation=any(d['kind']=='generation' for d in declarations),
                asserts_generative_edit=any(d['kind']=='generative_edit' for d in declarations))
    except ImportError:
        output['c2pa_status']='unavailable'
    except Exception as exc:
        # Missing manifests are common. A C2PA-looking but invalid packet is
        # recorded rather than trusted. Remote manifests/OCSP are never fetched.
        if b'c2pa' in data.lower() or b'jumb' in data[:65536].lower():
            output.update(c2pa_status='unverifiable',signature_trusted=False,reason=f'Content Credential could not be validated ({type(exc).__name__})')
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
            textual=metadata_fields(image, raw_bytes=data)
            clues=metadata_clues({**exif,**textual})
            quantization=getattr(image,'quantization',None)
            quality_limits=[]
            if min(width,height)<256:
                quality_limits.append('Image dimensions below 256px limit generator and localization evidence')
            if quantization and sum(quantization.get(0,[0]))/len(quantization.get(0,[0]))>65:
                quality_limits.append('JPEG quantization suggests extreme compression; fine manipulation traces may be lost')
            oriented=ImageOps.exif_transpose(image)
            shape=oriented.size
    return dict(sha256=hashlib.sha256(data).hexdigest(),byte_length=len(data),format=fmt,mime_type=FORMATS[fmt],
        original_dimensions=[width,height],oriented_dimensions=list(shape),
        quality=dict(limits=quality_limits,adequate=not quality_limits,
            note='Screenshots, filtering and re-encoding can hide traces even when not identifiable from the file'),
        provenance=dict(ai_markers=clues,software=exif.get('Software'),camera_make=exif.get('Make'),
            metadata_fields=sorted(textual),
            camera_model=exif.get('Model'),has_exif=bool(exif),c2pa_status='not_checked',
            note='Missing metadata is neutral. Editable software and camera tags do not prove origin.'))
