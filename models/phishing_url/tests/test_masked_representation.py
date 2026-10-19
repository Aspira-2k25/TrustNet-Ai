import unittest
from models.phishing_url.inference.modern_model import masked_url_text

class MaskedRepresentationTests(unittest.TestCase):
    def test_registered_names_do_not_create_identity_based_verdict_features(self):
        self.assertEqual(masked_url_text('https://google.com/a?q=1'),masked_url_text('https://entirely-unseen.net/a?q=1'))
        self.assertNotIn('google',masked_url_text('https://google.com/'))

    def test_subdomain_path_query_and_fragment_evidence_are_retained(self):
        value=masked_url_text('https://login.accounts.example.co.uk/A%2Fb?q=verify#step')
        self.assertEqual(value,'login.accounts.[DOMAIN]/A%2Fb?q=verify#step')

    def test_private_suffix_tenant_is_the_registration_boundary(self):
        self.assertEqual(masked_url_text('https://tenant.github.io/'),'[DOMAIN]/')

    def test_scheme_and_empty_root_are_invariant(self):
        self.assertEqual(masked_url_text('http://example.com'),masked_url_text('https://example.com/'))
