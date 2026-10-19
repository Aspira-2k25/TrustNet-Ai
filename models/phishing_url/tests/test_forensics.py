import unittest
from unittest.mock import patch

from models.phishing_url.inference.forensics import analyze, apply_policy, canonical_url
from models.phishing_url.inference.phishing_detector import PhishingDetector
from shared.schemas.detection_result import DetectionResult

class ForensicsTests(unittest.TestCase):
    def result(self, **updates):
        values = dict(scan_id='forensic-test', module='phishing', detector_id='fixture',
                      model_version='hybrid-v1', preprocessing_version='url-lexical-v1',
                      native_score=.99, native_score_semantics='probability_of_positive_class',
                      risk_score=99, confidence=.99, label='phishing', status='PARTIAL_SUCCESS',
                      timestamp='2026-10-16T00:00:00Z')
        values.update(updates)
        return DetectionResult(**values)

    def codes(self, url):
        return {f['code'] for f in analyze(url)['findings']}

    def test_root_variants_are_identical_model_inputs(self):
        self.assertEqual(canonical_url('https://google.com'), canonical_url('https://google.com/'))
        self.assertEqual(canonical_url('https://google.com#top'), 'https://google.com/#top')
        self.assertEqual(canonical_url('https://google.com?q=1'), 'https://google.com/?q=1')
        self.assertEqual(canonical_url('https://example.com/A%2fb'), 'https://example.com/A%2fb')

    def test_real_registered_domain_uses_private_suffixes(self):
        self.assertEqual(analyze('https://login.accounts.example.co.uk')['registered_domain'], 'example.co.uk')
        self.assertEqual(analyze('https://tenant.github.io')['registered_domain'], 'tenant.github.io')

    def test_deceptive_userinfo_high_but_same_domain_not_high(self):
        self.assertEqual(analyze('https://google.com@evil.example')['outcome'], 'SUSPICIOUS')
        self.assertEqual(analyze('https://google.com@accounts.google.com')['outcome'], 'REVIEW')

    def test_brand_paths_are_not_hostname_impersonation(self):
        self.assertNotIn('EMBEDDED_DOMAIN', self.codes('https://example.com/articles/google'))
        self.assertIn('EMBEDDED_DOMAIN', self.codes('https://google.com.login.evil.example'))
        self.assertNotIn('BRAND_LOOKALIKE', self.codes('https://g00gle.com/login'))

    def test_weak_signals_are_not_added_into_proof(self):
        report = analyze('http://127.0.0.1:8080/login?next=%2Faccount')
        self.assertEqual(report['outcome'], 'REVIEW')
        self.assertIn('NON_PUBLIC_DESTINATION', {f['code'] for f in report['findings']})

    def test_invalid_punycode_does_not_crash_worker(self):
        report = analyze('https://xn--abc.com/')
        self.assertIn('INVALID_IDN', {f['code'] for f in report['findings']})
        self.assertEqual(report['outcome'], 'REVIEW')

    def test_normal_url_not_fetched_or_declared_safe(self):
        with patch('socket.getaddrinfo', side_effect=AssertionError('No DNS allowed')):
            report = analyze('https://google.com')
        self.assertEqual(report['outcome'], 'NO_STRONG_INDICATORS')
        self.assertEqual(report['network']['status'], 'NOT_COLLECTED')
        self.assertIn('does not establish safety', report['definition'])

    def test_every_google_https_variant_withholds_bad_probability(self):
        for url in ['https://google.com', 'https://google.com/', 'https://www.google.com', 'https://www.google.com/']:
            with self.subTest(url=url):
                r = apply_policy(self.result(), url)
                self.assertEqual(r.status.value, 'UNAVAILABLE')
                self.assertEqual(r.verdict, 'UNCERTAIN')
                self.assertIsNone(r.metadata['assessment_dimensions']['phishing_risk']['score'])
                self.assertEqual(r.metadata['diagnostic_model']['probability'], .99)
                self.assertEqual(r.error_code, 'INSUFFICIENT_EVIDENCE')
                DetectionResult.model_validate(r.model_dump())

    def test_model_positive_alone_no_longer_decides(self):
        r = apply_policy(self.result(), 'http://google.com/')
        self.assertEqual(r.error_code, 'INSUFFICIENT_EVIDENCE')
        self.assertEqual(r.status.value, 'UNAVAILABLE')

    def test_rule_assessment_works_without_a_model(self):
        r = PhishingDetector().predict({'scan_id': 'rule-only', 'url': 'https://paypal.com@evil.example/login'})
        self.assertEqual(r.status.value, 'PARTIAL_SUCCESS')
        self.assertEqual(r.verdict, 'SUSPICIOUS')
        self.assertEqual(r.metadata['score_basis'], 'live_evidence')
        self.assertEqual(r.native_score_semantics.value, 'anomaly_score')
        self.assertFalse(r.metadata['confidence_available'])
        self.assertFalse(r.metadata['calibrated'])
        self.assertIn('risk', r.metadata['score_definition'].lower())
        DetectionResult.model_validate(r.model_dump())

    def test_password_post_to_http_is_detected(self):
        observations = {'signals': {'http': {'status': 'observed', 'final_url': 'https://login.example/'},
                                  'html': {'status': 'observed', 'password_forms': [{'action': 'http://login.example/submit'}]}}}
        r = apply_policy(self.result(), 'https://login.example/', observations=observations)
        self.assertEqual(r.verdict, 'SUSPICIOUS')
        self.assertIn('PASSWORD_HTTP', {f['code'] for f in r.metadata['forensics']['findings']})

    def test_external_password_identity_provider_needs_review_not_proof(self):
        observations = {'signals': {'http': {'status': 'observed', 'final_url': 'https://example.com/'},
                                  'html': {'status': 'observed', 'password_forms': [{'action': 'https://accounts.google.com/submit'}]}}}
        self.assertEqual(analyze('https://example.com/', observations)['outcome'], 'REVIEW')

    def test_redirect_and_registration_evidence(self):
        obs = {'domain_age_days': 3, 'signals': {'http': {'status': 'observed', 'final_url': 'http://other.example/'}}}
        report = analyze('https://example.com/', obs)
        self.assertEqual(report['outcome'], 'REVIEW')
        self.assertTrue({'RECENT_REGISTRATION', 'CROSS_DOMAIN_REDIRECT', 'HTTPS_DOWNGRADE'} <= {f['code'] for f in report['findings']})

    def test_missing_collection_never_becomes_safe(self):
        r = apply_policy(self.result(), 'https://example.com/', observations={'signals': {}})
        self.assertEqual(r.metadata['forensics']['network']['status'], 'UNAVAILABLE')
        self.assertEqual(r.verdict, 'UNCERTAIN')

    def test_reapplying_network_policy_is_idempotent(self):
        r = apply_policy(self.result(), 'https://google.com@evil.example')
        count = len(r.evidence)
        apply_policy(r, 'https://google.com@evil.example', observations={'signals': {}})
        self.assertEqual(len(r.evidence), count)
        self.assertEqual(len([a for a in r.analyzers if a['category'] == 'forensics']), 1)
        self.assertEqual(r.metadata['diagnostic_model']['probability'], .99)

    def test_low_model_does_not_override_forensic_review(self):
        r = apply_policy(self.result(model_version='modern-v5',label='legitimate', native_score=.01, risk_score=1), 'http://user@unrelated.example/login', .5)
        self.assertEqual(r.verdict, 'REVIEW_RECOMMENDED')
        self.assertEqual(r.status.value, 'PARTIAL_SUCCESS')

    def test_reapplication_restores_original_low_model_fields_consistently(self):
        r = self.result(model_version='modern-v5', label='legitimate', native_score=.1, risk_score=10)
        apply_policy(r, 'http://example.com/', .5, observations={'domain_age_days': 2, 'signals': {}})
        self.assertGreater(r.risk_score, 10)
        apply_policy(r, 'http://example.com/', .5, observations={'signals': {}})
        self.assertEqual(r.status.value, 'PARTIAL_SUCCESS')
        self.assertEqual(r.label, 'legitimate')
        self.assertEqual(r.risk_score, 10)
        DetectionResult.model_validate(r.model_dump())

    def test_inference_receives_normalized_url(self):
        class Model:
            classes_ = [0, 1]
            def predict_proba(self, rows):
                self.rows = rows
                return [[.99, .01]]
        detector = PhishingDetector()
        detector.model = Model()
        detector.manifest = {'threshold': .5, 'model_version': 'baseline-v1'}
        first = detector.predict({'scan_id': 'a', 'url': 'http://example.com'})
        second = detector.predict({'scan_id': 'b', 'url': 'http://example.com/'})
        self.assertEqual(first.metadata['features'], second.metadata['features'])
        self.assertEqual(first.metadata['assessed_url'], 'http://example.com')

if __name__ == '__main__':
    unittest.main()
