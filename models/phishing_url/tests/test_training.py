"""Synthetic pipeline checks; these do not measure phishing effectiveness."""
import csv
import json
import tempfile
import unittest
from pathlib import Path
from models.phishing_url.training.train_baselines import train
from models.phishing_url.inference.phishing_detector import PhishingDetector

class TrainingTests(unittest.TestCase):
    def test_training_inference_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = root / "synthetic.csv"
            with dataset.open("w", newline="", encoding="utf-8") as source:
                writer = csv.writer(source)
                writer.writerow(["url", "label", "domain_group", "split"])
                for split in ("train", "validation", "test"):
                    for index in range(12):
                        host = f"{split}{index}.example"
                        label = index % 2
                        writer.writerow([f"https://{host}/" + ("login/verify/password" if label else "about"), label, host, split])
            report = train(dataset, root / "bundle")
            self.assertEqual(set(report), {"lr", "rf"})
            for name in report:
                manifest_path = root / "bundle" / f"{name}.json"
                detector = PhishingDetector(manifest_path)
                result = detector.predict({"scan_id": "fixture", "url": "https://heldout.example/login"})
                self.assertEqual(result.status.value, "UNAVAILABLE")
                probability = result.metadata['diagnostic_model']['probability']
                self.assertGreaterEqual(probability, 0)
                self.assertLessEqual(probability, 1)
                self.assertEqual(result.error_code, 'INSUFFICIENT_EVIDENCE')
                self.assertIsNone(result.metadata['assessment_dimensions']['phishing_risk']['score'])
                manifest = json.loads(manifest_path.read_text())
                artifact = manifest_path.parent / manifest["artifact"]
                artifact.write_bytes(b"tampered")
                with self.assertRaisesRegex(ValueError, "checksum"):
                    PhishingDetector(manifest_path)

if __name__ == "__main__":
    unittest.main()
