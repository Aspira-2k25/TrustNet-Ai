"""Safe inference from checksummed JSON/NPZ; no research-folder dependency."""
from pathlib import Path
import hashlib,json,re,time
from datetime import datetime,timezone
import numpy as np
from scipy.special import softmax
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from shared.schemas.detection_result import DetectionResult

class ScamDetector:
    def __init__(self, artifact_dir=None):
        self.path=Path(artifact_dir) if artifact_dir else Path(__file__).resolve().parent/'artifacts'
        self.manifest=json.loads((self.path/'manifest.json').read_text(encoding='utf-8'))
        self.semantic = None
        if self.manifest.get('engine') in ('distilbert', 'distilbert_hybrid'):
            required = {'model.safetensors', 'config.json', 'runtime.json', 'tokenizer.json', 'tokenizer_config.json', 'special_tokens_map.json', 'vocab.txt'}
            if self.manifest.get('engine') == 'distilbert_hybrid':
                required |= {'hybrid_config.json', 'hybrid_weights.npz'}
            if not required.issubset(self.manifest.get('files', {})):
                raise ValueError('Incomplete semantic artifact manifest')
            for name, checksum in self.manifest['files'].items():
                artifact = (self.path / name).resolve()
                if not artifact.is_relative_to(self.path.resolve()):
                    raise ValueError('Invalid artifact path')
                digest = hashlib.sha256()
                with artifact.open('rb') as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                        digest.update(chunk)
                if digest.hexdigest() != checksum:
                    raise ValueError(f'Scam artifact checksum mismatch: {name}')
            from models.scam_message.inference.semantic_detector import SemanticDetector
            self.semantic = SemanticDetector(self.path, self.manifest)
            self.config = self.semantic.config
            return
        for name in ('weights.npz','config.json'):
            if hashlib.sha256((self.path/name).read_bytes()).hexdigest()!=self.manifest['files'][name]:
                raise ValueError('Scam artifact checksum mismatch')
        c=self.config=json.loads((self.path/'config.json').read_text(encoding='utf-8'))
        with np.load(self.path/'weights.npz',allow_pickle=False) as data:
            self.coef=data['coef']; self.intercept=data['intercept']
            self.word=TfidfVectorizer(vocabulary=c['word_vocab'],ngram_range=(1,2),sublinear_tf=True,token_pattern=r'(?u)\b\w+\b')
            self.char=TfidfVectorizer(vocabulary=c['char_vocab'],analyzer='char',ngram_range=(3,5),sublinear_tf=True)
            self.word.idf_=data['word_idf']; self.char.idf_=data['char_idf']
        if self.coef.shape!=(3,len(c['word_vocab'])+len(c['char_vocab'])) or not np.isfinite(self.coef).all():
            raise ValueError('Invalid scam artifact dimensions')
        self.features=list(self.word.get_feature_names_out())+list(self.char.get_feature_names_out())

    def predict(self,text,scan_id):
        from models.scam_message.coverage import predict_with_coverage
        return predict_with_coverage(self._predict_model,text,scan_id,self.manifest['model_version'])

    def _predict_model(self,text,scan_id):
        if self.semantic is not None:
            return self.semantic.predict(text,scan_id)
        start=time.perf_counter()
        if not text.strip() or len(text)>10000 or '\x00' in text:
            raise ValueError('Message must contain 1–10000 characters and no NUL bytes')
        hinglish_words = re.findall(r'\b(?:aap|apna|hai|karo|paisa|bhejo|turant)\b',text,re.I)
        if len(set(w.lower() for w in hinglish_words)) >= 2:
            raise ValueError('Possible Hinglish: unsupported language coverage; review manually')
        letters=[ch for ch in text if ch.isalpha()]
        latin=sum('a'<=ch.lower()<='z' for ch in letters)/max(1,len(letters))
        if not letters or latin<.8:
            raise ValueError('Unsupported script/language: trained for English SMS only')
        x=hstack([self.word.transform([text]),self.char.transform([text])],format='csr')
        if x.nnz==0: raise ValueError('Input has no features covered by the model')
        logits=np.asarray(x@self.coef.T).ravel()+self.intercept
        p=softmax(logits/self.config['temperature']); score=float(p[1]); label=self.config['labels'][int(p.argmax())]
        verdict='SMISHING_RISK' if score>=self.config['threshold'] else ('SPAM_SCREENING' if label=='spam' else 'LOW_SMISHING_SIGNAL')
        # Exact signed decomposition of positive-vs-rest-mean logit margin.
        contrast=(self.coef[1]-(self.coef[0]+self.coef[2])/2)/self.config['temperature']
        contributions=x.data*contrast[x.indices]; ordered=np.argsort(-np.abs(contributions))[:18]
        spans=[]; evidence=[]; lower=text.lower()
        for pos in ordered:
            feature=self.features[x.indices[pos]]; value=float(contributions[pos]); ischar=x.indices[pos]>=len(self.config['word_vocab'])
            # Char TF-IDF collapses whitespace; features without an exact original
            # occurrence remain in feature evidence, never invent an offset.
            matches=list(re.finditer(re.escape(feature),lower))[:8] if len(lower)==len(text) else []
            evidence.append({'feature_or_region':feature,'contribution':value,'human_readable_note':'Signed contribution to smishing-vs-other-classes mean logit margin; not probability change'})
            for m in matches:
                spans.append({'start':m.start(),'end':m.end(),'kind':'model','contribution':value/len(matches),'note':feature,'direction':'support' if value>0 else 'counterevidence'})
        indicators={
            'urgency':r'\b(urgent|immediately|today|blocked|suspended)\b',
            'sensitive_information':r'\b(otp|password|pin|credentials|bank account)\b',
            'payment_or_prize':r'\b(prize|winner|processing fee|payment|pay)\b',
            'negation_or_warning':r'\b(do not share|never share|warning|scam)\b'}
        context=[]
        for name,pattern in indicators.items():
            for m in re.finditer(pattern,text,re.I):
                span={'start':m.start(),'end':m.end(),'kind':'context','note':name,'contribution':0,'direction':'observation'}; spans.append(span);context.append(span)
        links=[]
        for m in re.finditer(r'(?i)\b(?:https?://|www\.)[^\s<>]+',text):
            end=m.end(); url=m.group().rstrip('.,;!?)]'); end=m.start()+len(url)
            link={'url':url,'start':m.start(),'end':end,'status':'UNAVAILABLE','reason':'Extracted without opening; reputation, DNS, TLS, redirects and domain age were not analyzed'};links.append(link);spans.append({'start':m.start(),'end':end,'kind':'link','note':link['reason'],'contribution':0,'direction':'observation'})
        warnings=['English SMS model; Hindi/Hinglish and email accuracy are not validated.','Low signal does not establish safety or sender identity.','Independent curated-source evaluation macro-F1 was 0.251; broad generalization is weak.','Context clues are observations, not fraud proof.']
        if len(text)>1600: warnings.append('Long input processed in full; this domain/length is outside validated SMS coverage.')
        if re.search(r'\b(hai|aap|karo|paisa|bhejo)\b',text,re.I):warnings.append('Possible Hinglish: unsupported language coverage; review manually.')
        explanation=f'{label} has the largest class probability. Estimated smishing probability is {score:.1%}; spam is a separate class. Highlights explain the deployed linear margin, not keyword rules.'
        return DetectionResult(scan_id=scan_id,module='scam_message',detector_id='scam_message.'+self.config['algorithm'],model_version=self.manifest['model_version'],preprocessing_version='unicode-tfidf-1',native_score=score,native_score_semantics='probability_of_positive_class',risk_score=score*100,confidence=float(p.max()),label=label,status='SUCCESS',verdict=verdict,explanation=explanation,evidence=evidence,analyzers=[{'name':self.config['algorithm'],'category':'primary_ml','status':'APPLIED','finding':'Three class model with temperature calibration'},{'name':'Context observations','category':'context','status':'APPLIED','finding':f'{len(context)} observations; these do not modify probability'},{'name':'Embedded URL analysis','category':'links','status':'UNAVAILABLE','reason':'URL analysis service is a placeholder'}],metadata={'probabilities':dict(zip(self.config['labels'],map(float,p))),'threshold':self.config['threshold'],'confidence_definition':'Largest calibrated class probability; distribution-specific, not measured accuracy','span_offset_unit':'Unicode code points','spans':spans,'links':links,'coverage':{'characters_processed':len(text),'truncated':False,'domain':'English SMS','validated_domain':len(text)<=1600},'limitations':warnings,'attribution_definition':'Additive signed TF-IDF contribution to calibrated smishing logit minus mean ham/spam logit; selected top 18 features, occurrence shares are display allocation','artifact_checksums':self.manifest['files']},processing_time_ms=int((time.perf_counter()-start)*1000),timestamp=datetime.now(timezone.utc).isoformat())
