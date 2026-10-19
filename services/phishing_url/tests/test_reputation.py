import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import patch, Mock
from services.phishing_url.app.services.reputation import lookup
from services.phishing_url.app.services.reputation import match_key, prefetch

class ReputationTests(unittest.TestCase):
    def test_batch_uses_provider_rows_and_reuses_cache(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict('os.environ',{'PHISHING_CACHE_DIR':directory}), patch('httpx.get') as get:
            get.return_value=Mock(status_code=200)
            get.return_value.json.return_value=[{'id':7,'url':'https://a.example/login','date':datetime.now(timezone.utc).isoformat(),'score':9}]
            self.assertEqual(prefetch(['https://a.example/login','https://b.example/'])['provider_records'],1)
            self.assertTrue(lookup('https://a.example/login')['fresh_match'])
            self.assertFalse(lookup('https://b.example/')['matched'])
            self.assertTrue(prefetch(['https://a.example/login'])['cached'])
            self.assertEqual(get.call_count,1)

    def test_match_canonicalisation_preserves_path_and_query(self):
        self.assertEqual(match_key('https://EXAMPLE.com:443'),match_key('https://example.com/'))
        self.assertNotEqual(match_key('https://example.com/A?q=1'),match_key('https://example.com/a?q=2'))
    def test_exact_match_cached_and_only_hostname_sent(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict('os.environ',{'PHISHING_CACHE_DIR':directory}), patch('httpx.get') as get:
            get.return_value=Mock(status_code=200)
            get.return_value.json.return_value=[{'id':123,'url':'https://a.example/login?secret=token','score':9}]
            a=lookup('https://a.example/login?secret=token')
            b=lookup('https://a.example/other')
            self.assertTrue(a['matched']);self.assertFalse(b['matched'])
            self.assertEqual(get.call_count,1)
            self.assertNotIn('secret',str(get.call_args.kwargs['params']))
            self.assertTrue(b['cached'])

    def test_quota_is_unknown_not_safe_and_is_backed_off(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict('os.environ',{'PHISHING_CACHE_DIR':directory}), patch('httpx.get') as get:
            get.return_value=Mock(status_code=429)
            self.assertEqual(lookup('https://a.example/')['status'],'RATE_LIMITED')
            self.assertEqual(lookup('https://a.example/')['status'],'RATE_LIMITED')
            self.assertEqual(lookup('https://another.example/')['status'],'RATE_LIMITED')
            self.assertEqual(get.call_count,1)

    def test_missing_match_does_not_claim_clean(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict('os.environ',{'PHISHING_CACHE_DIR':directory}), patch('httpx.get') as get:
            get.return_value=Mock(status_code=200);get.return_value.json.return_value=[]
            r=lookup('https://a.example/')
            self.assertFalse(r['matched']);self.assertIn('not evidence of safety',r['definition'])

    def test_credentials_are_never_queried(self):
        with patch('httpx.get') as get:
            self.assertEqual(lookup('https://name:password@a.example/')['status'],'UNAVAILABLE')
            get.assert_not_called()

    def test_provider_substring_results_are_not_domain_only_verdicts(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict('os.environ',{'PHISHING_CACHE_DIR':directory}), patch('httpx.get') as get:
            get.return_value=Mock(status_code=200)
            get.return_value.json.return_value=[{'id':1,'url':'https://attacker.example/?redirect=https://google.com/','date':datetime.now(timezone.utc).isoformat(),'score':9}]
            self.assertFalse(lookup('https://google.com/')['matched'])
            self.assertEqual(get.call_args.kwargs['params']['_where'],'(host,eq,google.com)')

    def test_only_fresh_high_score_reports_are_current_matches(self):
        for date, expected in [('2001-01-01T00:00:00Z',False),(datetime.now(timezone.utc).isoformat(),True)]:
            with self.subTest(date=date), tempfile.TemporaryDirectory() as directory, patch.dict('os.environ',{'PHISHING_CACHE_DIR':directory}), patch('httpx.get') as get:
                get.return_value=Mock(status_code=200)
                get.return_value.json.return_value=[{'id':1,'url':'https://a.example/','date':date,'score':9}]
                result=lookup('https://a.example/')
                self.assertTrue(result['matched'])
                self.assertEqual(result['fresh_match'],expected)
