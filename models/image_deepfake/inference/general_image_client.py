"""Explicit pretrained whole-image backend. No token/image is logged; no implicit fallback."""
import hashlib
import json
import os
import threading
import time
from dataclasses import dataclass, field

import httpx

MODEL = 'Ateeqq/ai-vs-human-image-detector'
REVISION = '60e82406916921b823616bee33397baab38af3f0'
REGISTRY = {
    MODEL: {'revision': REVISION, 'labels': {'ai':'fake','hum':'real'}, 'license':'apache-2.0',
            'scope':'whole-image AI screening',
            'limits':'Experimental pretrained detector; model author reports overfitting concerns. Contemporary generator and camera-photo performance require independent evaluation.'},
    'Organika/sdxl-detector': {'revision':'b37fede8562cb72b89ec201c0987f96ba21b518a',
            'labels':{'artificial':'fake','human':'real'}, 'license':'cc-by-nc-3.0', 'scope':'whole-image SDXL screening',
            'limits':'Experimental SDXL-oriented detector; other generators, CGI and screenshots require independent evaluation. Non-commercial use only.'},
}


def enabled(name):
    return os.getenv(name, 'false').lower() == 'true'


def parse_distribution(predictions, model=MODEL):
    """Only registered model-specific binary labels are accepted."""
    from models.image_deepfake.inference.classifier_contract import parse_binary_predictions
    if not isinstance(predictions, list):
        raise ValueError('Invalid prediction distribution')
    labels = REGISTRY[model]['labels']
    mapped = []
    for item in predictions:
        if not isinstance(item, dict) or item.get('label') not in labels:
            raise ValueError('Unknown model label')
        mapped.append({'label': labels[item['label']], 'score': item.get('score')})
    return parse_binary_predictions(mapped)


@dataclass(frozen=True)
class GeneralConfig:
    model: str
    revision: str
    backend: str
    allow_download: bool
    allow_hosted: bool
    license_ack: bool
    key: str = field(default='', repr=False)

    @classmethod
    def environment(cls):
        model = os.getenv('HF_GENERAL_IMAGE_MODEL', MODEL)
        return cls(model, os.getenv('HF_GENERAL_IMAGE_REVISION', REGISTRY.get(model,{}).get('revision','')),
                   os.getenv('IMAGE_INFERENCE_BACKEND', 'local'), enabled('IMAGE_ALLOW_MODEL_DOWNLOAD'),
                   enabled('IMAGE_ALLOW_HOSTED_INFERENCE') and enabled('IMAGE_HOSTED_UPLOAD_ACK'),
                   enabled('IMAGE_GENERAL_ALLOW_NONCOMMERCIAL'), os.getenv('HUGGINGFACE_API_KEY', '').strip())


class GeneralImageClient:
    def __init__(self, config=None):
        self.config = config or GeneralConfig.environment()
        self.pipeline = None
        self.processor_hash = None
        self.error = None
        self.hosted_verified = False
        self._lock = threading.Lock()
        self._last_load = 0.

    def configuration_error(self):
        c = self.config
        if c.model not in REGISTRY or c.revision != REGISTRY[c.model]['revision']:
            return 'MODEL_NOT_REGISTERED'
        if c.backend not in {'local', 'hosted'}:
            return 'INVALID_BACKEND'
        if REGISTRY[c.model]['license']=='cc-by-nc-3.0' and not c.license_ack:
            return 'NONCOMMERCIAL_LICENSE_ACK_REQUIRED'
        if c.backend == 'hosted' and not c.allow_hosted:
            return 'HOSTED_UPLOAD_NOT_ENABLED'
        if c.backend == 'hosted' and not c.key.startswith('hf_'):
            return 'CREDENTIAL_NOT_CONFIGURED'
        return None

    def identity(self):
        return {'model_id': self.config.model, 'requested_revision': self.config.revision,
                'model_revision': self.config.revision if self.config.backend == 'local' else None,
                'backend': self.config.backend, 'provider': 'hf-inference' if self.config.backend == 'hosted' else 'transformers',
                'processor_sha256': self.processor_hash, 'scope': REGISTRY.get(self.config.model,{}).get('scope','unsupported'),
                'deployment_pinned': self.config.backend == 'local', 'license': REGISTRY.get(self.config.model,{}).get('license'), 'limits': REGISTRY.get(self.config.model,{}).get('limits','Unregistered model')}

    def _load(self, allow_download=False):
        with self._lock:
            if self.pipeline is not None:
                return self.pipeline
            # Bound repeated failed cache loads. A deliberate download is a separate attempt.
            if self.error and not allow_download and time.monotonic()-self._last_load < 30:
                return None
            self._last_load = time.monotonic()
            try:
                from transformers import AutoImageProcessor, AutoModelForImageClassification, pipeline
                options = {'revision': self.config.revision, 'local_files_only': not allow_download,
                           'token': False, 'trust_remote_code': False}
                processor = AutoImageProcessor.from_pretrained(self.config.model, **options)
                model = AutoModelForImageClassification.from_pretrained(self.config.model, **options, use_safetensors=True)
                if set(model.config.id2label.values()) != set(REGISTRY[self.config.model]['labels']):
                    raise ValueError('Model labels do not match registry')
                self.processor_hash = hashlib.sha256(json.dumps(processor.to_dict(), sort_keys=True).encode()).hexdigest()
                self.pipeline = pipeline('image-classification', model=model, image_processor=processor, device=-1)
                self.error = None
            except Exception:
                self.error = 'LOCAL_MODEL_UNAVAILABLE'
            return self.pipeline

    def readiness(self):
        error = self.configuration_error()
        loaded = False
        if not error and self.config.backend == 'local':
            loaded = self._load(allow_download=False) is not None
        return {'ready': not error and (loaded or self.hosted_verified), 'configured': error is None,
                'credential_present': bool(self.config.key), 'connectivity_verified': self.hosted_verified,
                'error': error or self.error, **self.identity()}

    def predict(self, image_bytes):
        started = time.monotonic()
        output = {'status': 'UNAVAILABLE', 'risk_score': None, **self.identity()}
        error = self.configuration_error()
        if error:
            return {**output, 'reason': error}
        if not isinstance(image_bytes, bytes) or len(image_bytes) > 10*1024*1024:
            return {**output, 'reason': 'INPUT_BUDGET_EXCEEDED'}
        if not self._lock.acquire(blocking=False):
            return {**output, 'reason': 'INFERENCE_BUSY'}
        self._lock.release()
        try:
            if self.config.backend == 'local':
                pipe = self._load(allow_download=self.config.allow_download)
                if pipe is None:
                    return {**output, 'reason': self.error}
                from PIL import Image
                import io
                with self._lock:
                    data = pipe(Image.open(io.BytesIO(image_bytes)).convert('RGB'), top_k=None)
            else:
                data = self._hosted(image_bytes)
            score = parse_distribution(data,self.config.model)
            if self.config.backend == 'hosted':
                self.hosted_verified = True
            return {**output, **self.identity(), 'status': 'APPLIED', 'risk_score': score,
                    'processing_time_ms': round((time.monotonic()-started)*1000)}
        except ProviderFailure as failure:
            return {**output, 'reason': failure.code}
        except ValueError:
            return {**output, 'reason': 'INVALID_PROVIDER_RESPONSE'}
        except Exception:
            return {**output, 'reason': 'INFERENCE_FAILED'}

    def _hosted(self, blob):
        c = self.config
        endpoint = f'https://router.huggingface.co/hf-inference/models/{c.model}'
        headers = {'Authorization': 'Bearer '+c.key,
                   'Content-Type': 'image/png' if blob.startswith(b'\x89PNG') else 'image/jpeg'}
        with self._lock, httpx.Client(timeout=httpx.Timeout(12., connect=4.)) as client:
            for attempt in range(2):
                try:
                    response = client.post(endpoint, headers=headers, content=blob)
                except httpx.TimeoutException:
                    raise ProviderFailure('PROVIDER_TIMEOUT')
                except httpx.RequestError:
                    raise ProviderFailure('PROVIDER_NETWORK_ERROR')
                status = response.status_code
                if status == 200:
                    try:
                        return response.json()
                    except ValueError:
                        raise ProviderFailure('INVALID_PROVIDER_RESPONSE')
                if attempt == 0 and (status == 429 or status >= 500):
                    time.sleep(.25)
                    continue
                raise ProviderFailure({401:'PROVIDER_UNAUTHORIZED',402:'PROVIDER_BILLING_REQUIRED',
                                       403:'PROVIDER_FORBIDDEN',404:'MODEL_NOT_SERVED',429:'PROVIDER_RATE_LIMITED'}.get(status,'PROVIDER_UNAVAILABLE'))


class ProviderFailure(Exception):
    def __init__(self, code):
        self.code = code
