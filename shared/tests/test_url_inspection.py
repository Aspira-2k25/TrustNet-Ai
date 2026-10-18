from datetime import datetime, timezone
from shared.schemas.detection_result import DetectionResult
from shared.schemas.url_inspection import inspection_summary


def result(signals):
    return DetectionResult(scan_id='fixture', module='phishing', detector_id='fixture', model_version='fixture',
        preprocessing_version='fixture', native_score=.9, native_score_semantics='probability_of_positive_class',
        risk_score=90, confidence=0, label='phishing', status='PARTIAL_SUCCESS',
        timestamp=datetime.now(timezone.utc).isoformat(), metadata={'threshold': .7,
        'score_components': {'model_probability': .9}, 'forensics': {'hostname': 'example.com',
        'registered_domain': 'example.com', 'network': {'signals': signals}}})


def test_no_live_evidence_is_not_reported_as_certificate_or_page_verification():
    summary = inspection_summary(result({}))
    assert summary['live_checks_observed'] == 0
    assert {item['check'] for item in summary['missing_checks']} == {'dns','tls','http','html','registration','reputation','javascript'}
    assert all(item['title'] != 'HTTPS and certificate' for item in summary['observations'])
    assert 'learned URL patterns' in summary['model_assessment']


def test_invalid_certificate_and_html_form_are_explained_without_a_safety_claim():
    summary = inspection_summary(result({'tls': {'status': 'observed', 'validated': False, 'reason': 'expired'},
        'html': {'status': 'observed', 'password_forms': [{'action': 'http://other.example/submit'}], 'truncated': True}}))
    tls = next(item for item in summary['observations'] if item['title'] == 'HTTPS and certificate')
    assert tls['status'] == 'warning' and 'validation failed' in tls['observed']
    assert 'http://other.example/submit' in next(item for item in summary['observations'] if item['title'] == 'Page forms')['observed']
    assert any(item['check'] == 'complete_html' for item in summary['missing_checks'])
    assert any(item['check'] == 'javascript' for item in summary['missing_checks'])


def test_malformed_nested_metadata_is_not_reported_as_live_evidence():
    value = result({'dns': 'invalid', 'tls': []})
    value.metadata['score_components'] = ['invalid']
    summary = inspection_summary(value)
    assert summary['live_checks_observed'] == 0
    assert 'No primary URL model estimate' in summary['model_assessment']
    value.metadata['forensics'] = 'invalid'
    assert inspection_summary(value)['live_checks_observed'] == 0
