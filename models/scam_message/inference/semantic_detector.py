"""Local safetensors DistilBERT inference with bounded original-text occlusion."""
from pathlib import Path
from datetime import datetime, timezone
import json
import os
import re
import time
import numpy as np
import torch
from scipy.special import softmax
from scipy.sparse import hstack, csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from shared.schemas.detection_result import DetectionResult
from models.scam_message.preprocessing.validation import validate_text
from models.scam_message.configs.runtime import load_runtime
from models.scam_message.explainability.occlusion import measure_spans
from models.scam_message.preprocessing.links import feature_matrix, FEATURE_NAMES

STOPWORDS = {
    'a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and', 'any', 'are', 'aren\'t', 'as', 'at',
    'be', 'because', 'been', 'before', 'being', 'below', 'between', 'both', 'but', 'by', 'can\'t', 'cannot', 'could',
    'couldn\'t', 'did', 'didn\'t', 'do', 'does', 'doesn\'t', 'doing', 'don\'t', 'down', 'during', 'each', 'few', 'for',
    'from', 'further', 'had', 'hadn\'t', 'has', 'hasn\'t', 'have', 'haven\'t', 'having', 'he', 'he\'d', 'he\'ll', 'he\'s',
    'her', 'here', 'here\'s', 'hers', 'herself', 'him', 'himself', 'his', 'how', 'how\'s', 'i', 'i\'d', 'i\'ll', 'i\'m',
    'i\'ve', 'if', 'in', 'into', 'is', 'isn\'t', 'it', 'it\'s', 'its', 'itself', 'let\'s', 'me', 'more', 'most', 'mustn\'t',
    'my', 'myself', 'no', 'nor', 'not', 'of', 'off', 'on', 'once', 'only', 'or', 'other', 'ought', 'our', 'ours',
    'ourselves', 'out', 'over', 'own', 'same', 'shan\'t', 'she', 'she\'d', 'she\'ll', 'she\'s', 'should', 'shouldn\'t',
    'so', 'some', 'such', 'than', 'that', 'that\'s', 'the', 'their', 'theirs', 'them', 'themselves', 'then', 'there',
    'there\'s', 'these', 'they', 'they\'d', 'they\'ll', 'they\'re', 'they\'ve', 'this', 'those', 'through', 'to', 'too',
    'under', 'until', 'up', 'very', 'was', 'wasn\'t', 'we', 'we\'d', 'we\'ll', 'we\'re', 'we\'ve', 'were', 'weren\'t',
    'what', 'what\'s', 'when', 'when\'s', 'where', 'where\'s', 'which', 'while', 'who', 'who\'s', 'whom', 'why', 'why\'s',
    'with', 'won\'t', 'would', 'wouldn\'t', 'you', 'you\'d', 'you\'ll', 'you\'re', 'you\'ve', 'your', 'yours', 'yourself',
    'yourselves'
}


class SemanticDetector:
    def __init__(self, path: Path, manifest: dict):
        self.path, self.manifest = path, manifest
        self.config = load_runtime(path)
        torch.set_num_threads(max(1, min(4, int(os.getenv('SCAM_TORCH_THREADS', '1')))))
        self.tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True, use_fast=True)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            path, local_files_only=True, use_safetensors=True, trust_remote_code=False
        ).to('cpu').eval()
        if self.model.config.model_type != 'distilbert' or self.model.config.num_labels != 3:
            raise ValueError('Invalid semantic architecture')
        if [self.model.config.id2label[i] for i in range(3)] != self.config['labels']:
            raise ValueError('Model and runtime class mappings differ')
        self.hybrid = None
        if manifest.get('engine') == 'distilbert_hybrid':
            c=self.hybrid=json.loads((path/'hybrid_config.json').read_text(encoding='utf-8'))
            if c['labels']!=self.config['labels'] or not 0<=c['semantic_weight']<=1 or not 0<c['temperature']<100 or not 0<c['linear_temperature']<100:
                raise ValueError('Invalid hybrid calibration')
            self.word=TfidfVectorizer(vocabulary=c['word_vocab'],ngram_range=(1,2),sublinear_tf=True,token_pattern=r'(?u)\b\w+\b')
            self.char=TfidfVectorizer(vocabulary=c['char_vocab'],analyzer='char',ngram_range=(3,5),sublinear_tf=True)
            with np.load(path/'hybrid_weights.npz',allow_pickle=False) as arrays:
                self.coef=arrays['coef'];self.intercept=arrays['intercept'];self.word.idf_=arrays['word_idf'];self.char.idf_=arrays['char_idf']
            structural_names = c.get('structural_feature_names', [])
            self.structural_scales = np.asarray(c.get('structural_feature_scales', []), dtype=float)
            if structural_names and (structural_names != FEATURE_NAMES or
                                     self.structural_scales.shape != (len(FEATURE_NAMES),) or
                                     not np.isfinite(self.structural_scales).all() or
                                     (self.structural_scales <= 0).any()):
                raise ValueError('Invalid structural feature configuration')
            if not structural_names and self.structural_scales.size:
                raise ValueError('Unexpected structural feature scales')
            if self.coef.shape!=(3,len(c['word_vocab'])+len(c['char_vocab'])+len(structural_names)) or self.intercept.shape != (3,) or not all(np.isfinite(x).all() for x in [self.coef,self.intercept,self.word.idf_,self.char.idf_]):
                raise ValueError('Invalid hybrid weights')
            self.config['threshold']=c['threshold']

    validate = staticmethod(validate_text)

    def probabilities(self, text):
        encoded = self.tokenizer(
            text, truncation=True, max_length=384, stride=64,
            return_overflowing_tokens=True, padding=False
        )
        total = np.zeros(3, dtype=np.float64)
        windows = len(encoded['input_ids'])
        with torch.inference_mode():
            for start in range(0, windows, 2):
                items = [{k: encoded[k][i] for k in ('input_ids', 'attention_mask')}
                         for i in range(start, min(start + 2, windows))]
                batch = self.tokenizer.pad(items, return_tensors='pt')
                total += self.model(**batch).logits.numpy().sum(axis=0)
        probabilities = softmax(total / windows / self.config['temperature'])
        if self.hybrid is not None:
            c=self.hybrid
            features = [self.word.transform([text]), self.char.transform([text])]
            if self.structural_scales.size:
                features.append(csr_matrix(feature_matrix([text]) / self.structural_scales))
            x=hstack(features,format='csr')
            linear=softmax((np.asarray(x@self.coef.T).ravel()+self.intercept)/c['linear_temperature'])
            mixed=c['semantic_weight']*probabilities+(1-c['semantic_weight'])*linear
            probabilities=softmax(np.log(np.clip(mixed,1e-9,1))/c['temperature'])
        if not np.isfinite(probabilities).all():
            raise ValueError('Invalid model probabilities')
        return probabilities, windows

    def predict(self, text, scan_id):
        started = time.perf_counter()
        self.validate(text)
        p, windows = self.probabilities(text)
        prediction_seconds = time.perf_counter() - started
        score = float(p[1])
        label = self.config['labels'][int(p.argmax())]
        verdict = ('SMISHING_RISK' if score >= self.config['threshold'] else
                   'SPAM_SCREENING' if label == 'spam' else 'LOW_SMISHING_SIGNAL')
        spans, context, links = [], [], []
        indicators = {
            'urgency': r'\b(urgent|immediately|today|blocked|suspended)\b',
            'sensitive_information': r'\b(otp|password|pin|credentials|bank account)\b',
            'payment_or_prize': r'\b(prize|winner|processing fee|payment|pay)\b',
            'negation_or_warning': r'\b(do not share|never share|warning|scam)\b',
        }
        for name, pattern in indicators.items():
            for match in re.finditer(pattern, text, re.I):
                item = {'start': match.start(), 'end': match.end(), 'kind': 'context',
                        'note': name, 'contribution': 0, 'direction': 'observation'}
                spans.append(item)
                context.append(item)
        for match in re.finditer(r'https?://[^\s<>\"\']+|www\.[^\s<>\"\']+', text, re.I):
            url = match.group().rstrip('.,);]')
            links.append({'url': url, 'status': 'UNAVAILABLE',
                          'reason': 'Extracted without opening; reputation, DNS, TLS, redirects and domain age were not analyzed'})
            spans.append({'start': match.start(), 'end': match.start() + len(url), 'kind': 'link',
                          'note': 'Extracted link; analysis unavailable', 'contribution': 0, 'direction': 'observation'})

        # Context chooses possible spans only; it never alters the prediction.
        # Add uniform samples across meaningful content words so candidates avoid stopwords and short tokens.
        words = list(re.finditer(r'\b[A-Za-z][A-Za-z\d\'-]{1,}\b', text))
        content_words = [m for m in words if m.group().lower() not in STOPWORDS and len(m.group()) > 2]
        candidates = [(s['start'], s['end']) for s in context[:6]]
        pool = content_words if content_words else words
        if pool:
            sample_count = min(8, len(pool))
            candidates += [(pool[i].start(), pool[i].end())
                           for i in np.linspace(0, len(pool) - 1, sample_count, dtype=int)]
        candidates = list(dict.fromkeys(candidates))[:12]
        attribution_start = time.perf_counter()
        model_spans, evidence, timed_out, _ = measure_spans(
            self.probabilities, text, score, candidates,
            float(self.config.get('occlusion_budget_seconds', 3)),
            estimated_call_seconds=prediction_seconds,
        )
        partial = timed_out
        spans.extend(model_spans)
        measured = self.manifest['evaluation'].get('final_holdout')
        limitations = [
            'English SMS model; Hindi/Hinglish and email accuracy are not validated.',
            'Low signal does not establish safety or sender identity.',
            'Context clues are observations, not fraud proof.',
            'Occlusion samples at most 12 spans. Masking and window-boundary changes can influence its sensitivity values.',
        ]
        if measured:
            limitations[0] = 'Evaluated on limited English SMS/email collections; modern inbox, Hindi/Hinglish and other-language reliability are not established.'
            limitations.extend([
                f"Frozen labelled holdout macro-F1: {measured['macro_f1']:.3f}; collection-specific, not production accuracy.",
                f"Holdout fraud alert recall: {measured['fraud_alert_recall']['value']:.1%}; legitimate alert false-positive rate: {measured['legitimate_fpr']['value']:.1%}.",
                'Historical ham/spam and limited separately annotated promotional evidence restrict generalization. Sender authenticity is not checked.',
                'The previous baseline missed many independent-source scams; improvement on these collections does not establish universal detection.',
            ])
        else:
            source = self.manifest['evaluation']['source_heldout']
            limitations.extend([
                f"Previously inspected diagnostic-source macro-F1 was {source['macro_f1']:.3f}; this is not a production accuracy measurement.",
                f"Diagnostic-source argmax smishing recall was {source['per_class']['smishing']['recall']:.1%}; many smishing examples were missed.",
            ])
        if len(text) > 1500 and not measured:
            limitations.append('Long/email input is outside validated SMS coverage; all windows were processed without silent tail truncation.')
        if timed_out:
            if not evidence and candidates:
                limitations.append('A masked prediction was estimated to exceed the attribution budget; model highlights are unavailable for this request.')
            else:
                limitations.append('Attribution stopped at its time budget; displayed evidence is partial.')
        return DetectionResult(
            scan_id=scan_id, module='scam_message', detector_id=self.manifest.get('detector_id', 'scam_message.distilbert-hybrid.v2' if self.hybrid else 'scam_message.distilbert.v1'),
            model_version=self.manifest['model_version'], preprocessing_version=self.manifest.get('preprocessing_version', 'unicode-window384-stride64-tfidf-mixture.v2' if self.hybrid else 'unicode-window384-stride64.v1'),
            native_score=score, native_score_semantics='probability_of_positive_class',
            risk_score=score * 100, confidence=float(p.max()), label=label, verdict=verdict,
            status='SUCCESS', timestamp=datetime.now(timezone.utc).isoformat(),
            processing_time_ms=int((time.perf_counter() - started) * 1000), evidence=evidence,
            explanation=f'The model estimates smishing at {score:.1%}; highest-probability class is {label}. Highlights show bounded occlusion sensitivity, not keyword rules or fraud proof.',
            analyzers=[
                {'name': 'Fine-tuned DistilBERT + calibrated linear hybrid' if self.hybrid else 'Fine-tuned DistilBERT', 'status': 'APPLIED', 'finding': 'Validation-selected probability mixture, separate calibration; all accepted-text windows processed' if self.hybrid else 'Three-class model with separate temperature calibration; all accepted-text windows processed'},
                {'name': 'Model occlusion attribution', 'status': 'APPLIED' if evidence else 'UNAVAILABLE',
                 'finding': f'{len(evidence)} spans measured; partial: {partial}; single predictor sensitivity'},
                {'name': 'Context observations', 'status': 'APPLIED', 'finding': f'{len(context)} observations; these do not modify probability'},
                {'name': 'Embedded URL analysis', 'status': 'UNAVAILABLE', 'reason': 'URL analysis service is a placeholder'},
                *([{'name': 'Literal URL structure', 'status': 'APPLIED', 'finding': '14 locally parsed structural features in the learned lexical component; no links opened, HTTPS does not establish legitimacy'}] if self.hybrid and self.structural_scales.size else []),
            ],
            metadata={
                'threshold': self.config['threshold'],
                'probabilities': {name: float(p[i]) for i, name in enumerate(self.config['labels'])},
                'confidence_definition': 'Largest calibrated class probability; distribution-specific, not measured accuracy',
                'attribution_definition': 'Original smishing probability minus masked-span probability, measured using the deployed predictor; partial bounded occlusion sensitivity, not causal proof',
                'attribution_unit': 'probability change', 'attribution_partial': partial,
                'attribution_seconds': time.perf_counter() - attribution_start,
                'prediction_seconds': prediction_seconds,
                'spans': spans, 'context_indicators': context, 'links': links, 'limitations': limitations,
                'coverage': {'characters_processed': len(text), 'truncated': False, 'windows': windows,
                             'window_policy': '384 tokens, 64 overlap, mean message logits'},
                'model_agreement': None,
                'evaluated_domains': self.manifest.get('evaluated_domains', ['English SMS']),
                'evaluation_scope': 'Limited labelled collections; not a production guarantee',
            }
        )
