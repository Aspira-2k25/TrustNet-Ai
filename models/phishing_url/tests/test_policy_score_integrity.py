from datetime import datetime,timezone
import pytest
from shared.schemas.detection_result import DetectionResult
from models.phishing_url.inference.dynamic_policy import apply


@pytest.mark.parametrize('url',[
    'https://customer-notice.net/account',
    'https://customer-notice.net/unsubscribe/account',
    'https://customer-notice.net/account?next=unsubscribe',
    'https://google.com/account',
    'https://university.edu/account',
])
def test_url_words_and_popularity_cannot_erase_a_model_alert(url):
    result=DetectionResult(scan_id='policy-test',module='phishing',detector_id='fixture',
        model_version='regional-recall-v1',preprocessing_version='fixture',
        native_score=.95,native_score_semantics='probability_of_positive_class',risk_score=95,
        confidence=0,label='phishing',status='SUCCESS',verdict='SUSPICIOUS',timestamp=datetime.now(timezone.utc).isoformat())
    result=apply(result,url,threshold=.7)
    assert result.metadata['diagnostic_model']['probability']==.95
    assert result.metadata['score_components']['model_probability']==.95
    assert result.verdict=='SUSPICIOUS'
    assert result.risk_score>=95
