import unittest
from models.phishing_url.preprocessing.url_parser import parse_url
from models.phishing_url.preprocessing.extract_features import extract_features
from models.phishing_url.inference.phishing_detector import PhishingDetector
from services.phishing_url.app.detection_service import DetectionService

class FoundationsTests(unittest.TestCase):
    def test_preserves_path_and_encoding(self):
        parsed = parse_url("https://EXAMPLE.com/A%2fb?q=Hello")
        self.assertEqual(parsed.hostname, "example.com")
        self.assertEqual(parsed.parts.path, "/A%2fb")

    def test_idn_ipv6_userinfo(self):
        self.assertEqual(extract_features("https://bücher.de/")["is_idn"], 1)
        self.assertEqual(extract_features("https://[::1]/")["is_ip"], 1)
        self.assertEqual(extract_features("https://bank.com@evil.example/")["has_userinfo"], 1)

    def test_invalid_urls(self):
        for url in ("file:///etc/passwd", "https://", "https://a:99999", "https://a b/", "https://a\\b", "https://-bad.com"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                parse_url(url)

    def test_missing_model_is_not_safe_verdict(self):
        result = PhishingDetector().predict({"scan_id": "s1", "url": "https://example.com"})
        self.assertEqual(result.status.value, "UNAVAILABLE")
        self.assertEqual(result.label, "unknown")
        self.assertEqual(result.error_code, "MODEL_NOT_CONFIGURED")

    def test_contract_preserves_scan(self):
        completion = DetectionService(PhishingDetector()).handle({"scan_id": "s1", "module": "phishing", "timestamp": "2026-10-12T00:00:00Z", "payload": {"url": "https://example.com"}})
        self.assertEqual(completion.payload.scan_id, "s1")
        with self.assertRaises(ValueError):
            DetectionService(PhishingDetector()).handle({"scan_id": "s1", "module": "scam_message", "timestamp": "2026-10-12T00:00:00Z", "payload": {"url": "https://example.com"}})

    def test_leakage_rejected(self):
        import tempfile
        from pathlib import Path
        from models.phishing_url.training.train_baselines import load_rows
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data.csv"
            path.write_text("url,label,domain_group,split\nhttps://a.example,0,example,train\nhttps://b.example,1,example,test\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "leakage"):
                load_rows(path)

if __name__ == "__main__":
    unittest.main()
