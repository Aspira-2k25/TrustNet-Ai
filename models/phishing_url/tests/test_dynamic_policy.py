import unittest
from shared.schemas.detection_result import DetectionResult
from models.phishing_url.inference.forensics import apply_policy, analyze
from models.phishing_url.preprocessing.structural_features import extract

class DynamicPolicyTests(unittest.TestCase):
    def result(self, p=.1):
        return DetectionResult(scan_id='dynamic',module='phishing',detector_id='fixture',model_version='modern-v5',
                 preprocessing_version='test',native_score=p,native_score_semantics='probability_of_positive_class',
                 risk_score=p*100,confidence=0,label='phishing' if p>=.5 else 'legitimate',status='PARTIAL_SUCCESS',timestamp='2026-10-16T00:00:00Z')

    def test_https_modern_model_is_not_blanket_blocked(self):
        for url in ['https://google.com','https://www.google.com/','https://previously-unseen.example/']:
            r=apply_policy(self.result(),url,.5)
            self.assertEqual(r.status.value,'PARTIAL_SUCCESS')
            self.assertEqual(r.risk_score,10)
            self.assertIsNone(r.error_code)
            self.assertEqual(r.verdict,'NO_STRONG_INDICATORS')
            DetectionResult.model_validate(r.model_dump())

    def test_same_forensic_finding_does_not_force_constant_score(self):
        a=apply_policy(self.result(.1),'https://university.edu@evil.example/',.5)
        b=apply_policy(self.result(.6),'https://university.edu@evil.example/',.5)
        self.assertNotEqual(a.risk_score,b.risk_score)
        self.assertGreater(b.risk_score,a.risk_score)
        self.assertEqual(a.verdict,'SUSPICIOUS')
        self.assertNotEqual(a.risk_score,75)

    def test_generic_impersonation_has_no_brand_list(self):
        report=analyze('https://arbitrary-university.edu@evil.example/')
        self.assertIn('MISLEADING_AUTHORITY',{f['code'] for f in report['findings']})

    def test_no_reputation_match_is_not_a_clean_verdict(self):
        r=self.result();r.model_version='hybrid-v1'
        apply_policy(r,'https://anything.example/',.5,{'signals':{'reputation':{'status':'OBSERVED','matched':False}}})
        self.assertEqual(r.status.value,'UNAVAILABLE')

    def test_reputation_report_dynamically_changes_assessment(self):
        a=apply_policy(self.result(.1),'https://a.example/',.5)
        b=apply_policy(self.result(.1),'https://a.example/',.5,{'signals':{'reputation':{'status':'OBSERVED','matched':True,'fresh_match':True,'provider':'fixture'}}})
        self.assertEqual(a.verdict,'NO_STRONG_INDICATORS')
        self.assertEqual(b.verdict,'SUSPICIOUS')
        self.assertGreater(b.risk_score,a.risk_score)
        self.assertTrue(b.metadata['score_components']['evidence_updates'])

    def test_offline_or_failed_site_does_not_erase_model_result(self):
        r=apply_policy(self.result(),'https://a.example/',.5,{'signals':{'http':{'status':'unavailable','reason':'TimeoutError'}}})
        self.assertEqual(r.status.value,'PARTIAL_SUCCESS')
        self.assertEqual(r.metadata['coverage']['status'],'URL_ANALYSIS_ONLY')

    def test_medium_index_is_not_called_low_risk(self):
        r=apply_policy(self.result(.4),'https://a.example/',.72)
        self.assertEqual(r.verdict,'REVIEW_RECOMMENDED')
        self.assertNotIn('Low',r.metadata['display_verdict'])

    def test_structural_features_are_scheme_and_root_slash_invariant(self):
        self.assertEqual(extract('http://example.com'),extract('https://example.com/'))
        self.assertNotEqual(extract('https://example.com/'),extract('https://example.com/login/12?a=1'))
