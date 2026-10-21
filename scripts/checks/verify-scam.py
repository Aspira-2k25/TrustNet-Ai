"""Offline integrity, selected-model inference and public-contract smoke, any working directory."""
from pathlib import Path
import sys,json,math
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root))
from models.scam_message.detector import ScamDetector
from shared.schemas.message_input import MessageInput
from models.scam_message.presentation import enrich
detector=ScamDetector()
request=MessageInput(text='🚨 Your access is suspended. Reply with your password and one-time code to restore access.')
result=enrich(detector.predict(request.canonical_text(),'offline-verification'),request)
assert result.model_version==detector.manifest['model_version']
assert result.verdict=='LIKELY_SCAM', 'Explicit password request must raise a warning'
assert result.metadata.get('classifier_policy')=='multilingual-tfidf-v1' or math.isclose(sum(result.metadata['probabilities'].values()),1,abs_tol=1e-8)
assert detector.path.is_relative_to(root)
for span in result.metadata['spans']:
 assert 0<=span['start']<span['end']<=len(request.text)
 if span['kind']=='model':
  p,_=detector.semantic.probabilities(request.text[:span['start']]+'[MASK]'+request.text[span['end']:])
  assert abs(span['contribution']-(result.native_score-float(p[1])))<1e-7
  break
assert result.metadata['assessment_dimensions']['ai_authorship']['status']=='NOT_ASSESSED'
print(json.dumps({'integrity':'PASS','model_version':result.model_version,'risk':result.risk_score,'verdict':result.verdict,'offline_model_load':True,'signed_attribution_verified':any(s.get('kind')=='model' for s in result.metadata['spans']),'public_contract_verified':result.presentation.contract_version=='1','external_research_folder_required':False},indent=2))
