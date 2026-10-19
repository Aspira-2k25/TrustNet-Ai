import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
from models.phishing_url.research.audit_uci import audit

class AuditTests(unittest.TestCase):
    def test_duplicates_and_conflicts_are_not_hidden(self):
        headers = [f"@attribute f{i} {{-1,1}}" for i in range(30)] + ["@attribute Result {-1,1}"]
        positive = ",".join(["1"] * 31)
        negative = ",".join(["1"] * 30 + ["-1"])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.zip"
            with ZipFile(path, "w") as source:
                source.writestr("Training Dataset.arff", "\n".join(headers + ["@data", positive, positive, negative]))
                source.writestr("Phishing Websites Features.docx", b"fixture dictionary")
            result = audit(path)
        self.assertEqual(result["exact_duplicate_rows"], 1)
        self.assertEqual(result["conflicting_feature_vectors"], 1)
        self.assertEqual(result["original_label_counts"], {"1": 2, "-1": 1})
        self.assertFalse(result["live_url_compatible"])
        self.assertTrue(result["label_mapping_status"].startswith("pending"))
