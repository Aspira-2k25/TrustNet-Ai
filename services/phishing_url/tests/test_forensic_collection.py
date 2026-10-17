import unittest
from unittest.mock import patch
from services.phishing_url.app.services.metadata_collector import password_forms, collect
from services.phishing_url.app.detection_service import DetectionService
from models.phishing_url.inference.phishing_detector import PhishingDetector

class ForensicCollectionTests(unittest.TestCase):
    def test_static_password_forms_and_base_href(self):
        body = b'<base href="https://other.example/"><form action="/send"><input type="password"></form><form action="/search"><input type="text"></form><script>throw new Error()</script>'
        self.assertEqual(password_forms(body, 'https://example.com/'), [{'action': 'https://other.example/send'}])

    def test_empty_action_uses_page_not_base(self):
        body = b'<base href="http://evil.example/"><form><input type="PASSWORD"></form>'
        self.assertEqual(password_forms(body, 'https://example.com/'), [{'action': 'https://example.com/'}])

    def test_explicit_form_owner_overrides_enclosing_form(self):
        body = b'<form action="http://example.com/"><input type="password" form="safe"></form><form id="safe" action="https://example.com/"></form>'
        self.assertEqual(password_forms(body, 'https://example.com/'), [{'action': 'https://example.com/'}])

    def test_lookup_uses_registered_domain(self):
        calls = []
        def fake_fetch(url, **kwargs):
            calls.append(url)
            if 'rdap.org' in url:
                return {'status': 200, 'body': b'{"events": []}'}
            return {'status': 200, 'body': b'<form action="http://evil.example/"><input type="password"></form>',
                    'content_type': 'text/html', 'certificate': {}, 'redirects': 0, 'final_url': url}
        with patch('services.phishing_url.app.services.metadata_collector.lookup', return_value={'status':'OBSERVED','matched':False}), patch('services.phishing_url.app.services.metadata_collector.fetch', side_effect=fake_fetch), patch('services.phishing_url.app.services.metadata_collector.public_addresses', return_value=['8.8.8.8']):
            result = collect('https://login.example.co.uk/', True)
        self.assertIn('https://rdap.org/domain/example.co.uk', calls)
        self.assertTrue(result['signals']['html']['password_forms'])

    def test_collector_runs_even_when_model_unavailable(self):
        event = {'scan_id': 'collection', 'module': 'phishing', 'timestamp': '2026-10-16T00:00:00Z',
                 'payload': {'url': 'https://example.com/'}}
        obs = {'signals': {'http': {'status': 'observed', 'final_url': 'https://example.com/'},
                           'html': {'status': 'observed', 'password_forms': [{'action': 'http://example.com/'}]}}}
        with patch.dict('os.environ', {'PHISHING_COLLECTOR_URL': 'http://collector:8008'}), patch('httpx.post') as post:
            post.return_value.json.return_value = obs
            result = DetectionService(PhishingDetector()).handle(event).payload
        self.assertEqual(result.verdict, 'SUSPICIOUS')
        self.assertEqual(result.metadata['score_basis'], 'live_evidence')
        self.assertTrue(post.call_args.kwargs['json']['include_html'])

if __name__ == '__main__':
    unittest.main()
