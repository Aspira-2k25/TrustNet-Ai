import unittest
from unittest.mock import patch
from models.phishing_url.preprocessing.link_input import inspect_input
from models.phishing_url.preprocessing.url_parser import parse_url
from models.phishing_url.inference.forensics import analyze,apply_policy
from models.phishing_url.inference.lookalike import compare,index
from models.phishing_url.inference.phishing_detector import PhishingDetector
from services.phishing_url.app.detection_service import DetectionService
from services.scan_management.app.schemas.scan_schemas import ScanCreateURLRequest
from shared.schemas.detection_result import DetectionResult

class LinkInputTests(unittest.TestCase):
    def test_bare_domain_and_paths_preserve_identity_and_encoding(self):
        for value in ['paypal.com','paypaI.com/login?q=A%2FB','//example.com/A','example.com:443/A']:
            link=inspect_input(value)
            self.assertTrue(link['inferred_https'])
            self.assertEqual(link['original'],value)
            self.assertTrue(link['normalized'].startswith('https:'))
            self.assertEqual(ScanCreateURLRequest(url=value).url,value)
        self.assertEqual(inspect_input('paypaI.com')['hostname'],'paypai.com')
        self.assertEqual(inspect_input('PAYPAL.com')['hostname'],'paypal.com')

    def test_invalid_input_still_rejected(self):
        for value in ['not a url','https://','http:paypal.com','example.com:99999','https://-bad.com','paypal.com\\@evil.com','word']:
            with self.subTest(value=value),self.assertRaises(ValueError):inspect_input(value)

    def test_trained_fetch_parser_remains_web_only(self):
        for value in ['ftp://example.com/','javascript:alert(1)','file:///tmp/test','mailto:a@example.com']:
            self.assertEqual(inspect_input(value)['kind'],'non_web')
            with self.assertRaises(ValueError):parse_url(value)

    def test_paypal_case_and_lookalikes(self):
        for value in ['paypal.com','PAYPAL.COM','https://www.paypal.com/','https://example.org/paypaI.com']:
            self.assertNotIn('VISUAL_DOMAIN_IMPERSONATION',{f['code'] for f in analyze(value)['findings']})
        for value in ['paypaI.com','paypai.com','https://app1e.com/','https://раураl.com/']:
            report=analyze(value)
            self.assertIn('VISUAL_DOMAIN_IMPERSONATION',{f['code'] for f in report['findings']})
            self.assertEqual(report['outcome'],'SUSPICIOUS')

    def test_detection_is_generic_not_a_paypal_exception(self):
        index.cache_clear()
        try:
            with patch('models.phishing_url.inference.lookalike.reference',return_value={'domains':{'examplebank.com':1},'confusables':{},'version':'fixture','retrieved_at':'fixture'}):
                self.assertEqual(compare('examp1ebank.com')['resembles_domain'],'examplebank.com')
                self.assertIsNone(compare('examplebank.com'))
        finally:index.cache_clear()

    def test_lookalike_forensics_changes_same_model_prediction(self):
        def result():return DetectionResult(scan_id='lookalike',module='phishing',detector_id='fixture',model_version='modern-v5',preprocessing_version='test',native_score=.1,native_score_semantics='probability_of_positive_class',risk_score=10,confidence=0,label='legitimate',status='PARTIAL_SUCCESS',timestamp='2026-10-17T00:00:00Z')
        real=apply_policy(result(),'paypal.com',.7)
        fake=apply_policy(result(),'paypaI.com',.7)
        self.assertEqual(real.risk_score,10)
        self.assertGreater(fake.risk_score,real.risk_score)
        self.assertEqual(fake.verdict,'SUSPICIOUS')
        self.assertEqual(fake.metadata['forensics']['hostname'],'paypai.com')

    def test_nonweb_inputs_are_never_fetched_or_given_web_predictions(self):
        for url in ['ftp://example.com/','mailto:a@example.com','javascript:alert(1)','file:///etc/passwd','myapp://example.com/open']:
            with self.subTest(url=url),patch.dict('os.environ',{'PHISHING_COLLECTOR_URL':'http://collector:8008'}),patch('httpx.post') as post:
                result=DetectionService(PhishingDetector()).handle({'scan_id':'nonweb','module':'phishing','timestamp':'2026-10-17T00:00:00Z','payload':{'url':url}}).payload
                post.assert_not_called()
                self.assertEqual(result.error_code,'NON_WEB_LINK')
                self.assertEqual(result.model_version,'link-forensics-v1')
                self.assertNotEqual(result.label,'legitimate')

    def test_mailto_and_ftp_lookalike_identity_is_checked_offline(self):
        for url in ['mailto:billing@paypaI.com','ftp://paypaI.com/download']:
            result=PhishingDetector().predict({'scan_id':'nonweb-lookalike','url':url})
            self.assertEqual(result.verdict,'SUSPICIOUS')
            self.assertEqual(result.risk_score,80)

    def test_lookalike_redirect_destination_is_checked(self):
        report=analyze('https://example.org/short',{'signals':{'http':{'status':'observed','final_url':'https://paypai.com/'}}})
        self.assertEqual(report['outcome'],'SUSPICIOUS')
        self.assertEqual(report['visual_domain_match']['actual_domain'],'paypai.com')
        self.assertEqual(report['visual_domain_match']['match_scope'],'observed_navigation')
