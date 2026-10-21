"""Small checksummed multilingual lexical model; no executable model deserialization.

Hindi standalone warnings failed a separate hard-negative release gate and remain
disabled. English/Hinglish readings are not calibrated probabilities or guarantees.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
import numpy as np
from scipy.sparse import hstack
from scipy.special import expit
from sklearn.feature_extraction.text import TfidfVectorizer
from shared.schemas.detection_result import DetectionResult
from shared.utils.message_normalization import normalize_message, message_language


class MultilingualHead:
    def __init__(self, path=None):
        self.path=Path(path) if path else Path(__file__).with_name('multilingual_artifacts')
        manifest=json.loads((self.path/'manifest.json').read_text(encoding='utf-8'))
        for name in ('config.json','weights.npz'):
            if hashlib.sha256((self.path/name).read_bytes()).hexdigest()!=manifest['files'][name]:
                raise ValueError('Multilingual model checksum mismatch: '+name)
        self.config=json.loads((self.path/'config.json').read_text(encoding='utf-8'))
        if self.config['normalization']!='nfkc-casefold-url-email-number-v1':raise ValueError('Unknown text preprocessing')
        if sum(len(self.config[k]) for k in ('word_vocab','char_vocab'))>60000:raise ValueError('Unexpected vocabulary size')
        with np.load(self.path/'weights.npz',allow_pickle=False) as data:
            self.coef=data['coef'];self.intercept=data['intercept']
            self.word=TfidfVectorizer(vocabulary=self.config['word_vocab'],ngram_range=(1,2),sublinear_tf=True,token_pattern=r'(?u)\b\w+\b')
            self.char=TfidfVectorizer(vocabulary=self.config['char_vocab'],analyzer='char',ngram_range=(3,5),sublinear_tf=True)
            self.word.idf_=data['word_idf'];self.char.idf_=data['char_idf']
        if self.coef.shape!=(1,len(self.word.vocabulary)+len(self.char.vocabulary)) or not np.isfinite(self.coef).all():
            raise ValueError('Invalid multilingual head shape')
        self.version=manifest['model_version']

    def supports(self,text):
        letters=[c for c in text if c.isalpha()]
        latin=sum('a'<=c.lower()<='z' for c in letters)/max(1,len(letters))
        return bool(letters) and latin>=.8 and message_language(text) in self.config['enabled_languages']

    def predict(self,text,scan_id):
        if not text.strip() or len(text)>10000 or '\x00' in text:raise ValueError('Message must contain 1–10000 characters and no NUL bytes')
        language=message_language(text)
        if language not in self.config['enabled_languages']:raise ValueError('Unsupported language for selected multilingual head')
        started=time.perf_counter();truncated=len(text)>1800
        value=normalize_message(text[:1800])
        x=hstack([self.word.transform([value]),self.char.transform([value])],format='csr')
        score=float(expit(np.asarray(x@self.coef.T).ravel()[0]+self.intercept[0]))
        threshold=self.config['thresholds'][language]
        covered=x.nnz>0 and not truncated
        return DetectionResult(scan_id=scan_id,module='scam_message',detector_id='scam_message.multilingual_tfidf.v1',
            model_version=self.version,preprocessing_version=self.config['normalization'],
            native_score=score,native_score_semantics='anomaly_score',risk_score=score*100,confidence=0,
            label='smishing' if covered and score>=threshold else 'unknown',status='SUCCESS',
            verdict='LIKELY_SCAM' if covered and score>=threshold else 'NO_STRONG_INDICATORS' if covered else 'UNABLE_TO_ASSESS',
            explanation='Word and character patterns from the selected multilingual text classifier. This reading is not a calibrated probability.',
            timestamp=datetime.now(timezone.utc).isoformat(),processing_time_ms=round((time.perf_counter()-started)*1000),
            metadata={'classifier_policy':'multilingual-tfidf-v1','threshold':threshold,'language_route':language,
                      'language_coverage_limited':False,'confidence_available':False,'probabilities':{},'spans':[],
                      'coverage':{'characters_processed':min(1800,len(text)),'truncated':truncated,'features_found':int(x.nnz),'supported':covered},
                      'evaluated_domains':['Public-source English/Hinglish short messages'],
                      'limitations':['Public labels and templates limit generalization. Sender identity and intent are not verified.',
                                     'Hindi standalone classifier disabled after false warnings on normal OTP and delivery messages.'],
                      'confidence_definition':'Uncalibrated lexical reading; no confidence percentage is available.'})
