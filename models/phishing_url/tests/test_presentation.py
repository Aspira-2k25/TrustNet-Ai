import unittest
from shared.schemas.detection_result import DetectionResult
from models.phishing_url.inference.presentation import present

class PresentationTests(unittest.TestCase):
    def result(self, **updates):
        data=dict(scan_id='presentation',module='phishing',detector_id='fixture',model_version='modern-v5',
                  preprocessing_version='test',native_score=.2,native_score_semantics='probability_of_positive_class',
                  risk_score=20,confidence=.8,label='legitimate',status='PARTIAL_SUCCESS',timestamp='2026-10-15T00:00:00Z')
        data.update(updates)
        return DetectionResult(**data)

    def test_low_signal_does_not_claim_website_verification(self):
        r=present(self.result(), 'https://example.com/', .53)
        self.assertEqual(r.verdict,'NO_STRONG_INDICATORS')
        self.assertEqual(r.metadata['assessment_dimensions']['website_verification']['status'],'NOT_VERIFIED')
        self.assertIn('not guarantee safety',r.metadata['limitations'][0])
        self.assertFalse(r.metadata.get('confidence_available',False))

    def test_failure_is_not_presented_as_low_risk(self):
        r=present(self.result(status='FAILED',error_code='INVALID_URL',label='unknown'),None,None)
        self.assertEqual(r.verdict,'UNABLE_TO_ASSESS')
        self.assertEqual(r.metadata['display_verdict'],'Check incomplete')

    def test_alert_preserves_shared_contract_and_score(self):
        r=present(self.result(label='phishing',native_score=.8,risk_score=80),'https://a.example/',.53)
        self.assertEqual(r.verdict,'SUSPICIOUS')
        self.assertEqual(r.risk_score,80)
        DetectionResult.model_validate(r.model_dump())

    def test_https_does_not_display_unvalidated_confidence(self):
        r=self.result(model_version='hybrid-v1',metadata={'confidence_available':True})
        r=present(r,'https://example.com/',.53)
        self.assertFalse(r.metadata['confidence_available'])
        self.assertEqual(r.confidence,0)
        self.assertEqual(r.metadata['coverage']['status'],'URL_ANALYSIS_ONLY')

    def test_disagreeing_models_abstain_instead_of_reporting_phishing(self):
        from models.phishing_url.inference.phishing_detector import PhishingDetector
        class DisagreeingModel:
            def predict_url(self,url,features):
                return .99,.53,{'configuration':'lightgbm_bert','model_disagreement':True,
                    'branch_decisions':{'bert':True,'lightgbm':False},'analyzers':[], 'inference_ms':1}
        d=PhishingDetector(); d.model=DisagreeingModel()
        d.manifest={'model_version':'hybrid-v1'}
        r=d.predict({'scan_id':'disagree','url':'http://example.com/'})
        self.assertEqual(r.status.value,'UNAVAILABLE')
        self.assertEqual(r.verdict,'UNCERTAIN')
        self.assertEqual(r.label,'unknown')
        self.assertEqual(r.error_code,'MODEL_DISAGREEMENT')
        self.assertFalse(r.metadata['confidence_available'])
        DetectionResult.model_validate(r.model_dump())
