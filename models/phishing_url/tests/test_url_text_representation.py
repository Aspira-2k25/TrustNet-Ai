import unittest
from models.phishing_url.inference.url_text_model import canonical_text

class URLTextRepresentationTests(unittest.TestCase):
    def test_transport_does_not_change_representation(self):
        self.assertEqual(canonical_text('http://WWW.example.com/account?q=Hello'),canonical_text('https://www.example.com/account?q=Hello'))

    def test_destination_obfuscation_and_query_are_preserved(self):
        text=canonical_text('https://bank.example@other.example/a%2Fb?next=Login')
        self.assertIn('bank.example@other.example',text)
        self.assertIn('/a%2Fb?next=Login',text)

    def test_fragments_ignored_and_input_validation_retained(self):
        self.assertEqual(canonical_text('https://example.com/#section'),'example.com/')
        with self.assertRaises(ValueError):canonical_text('file:///etc/passwd')
