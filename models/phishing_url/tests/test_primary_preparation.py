import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile
from models.phishing_url.training.prepare_primary import normalize, prepare

class PreparationTests(unittest.TestCase):
    def test_scheme_provenance_and_case(self):
        url, key, inferred, parsed = normalize("EXAMPLE.com/Case%2F?q=ABC")
        self.assertTrue(inferred)
        self.assertEqual(url, "http://EXAMPLE.com/Case%2F?q=ABC")
        self.assertEqual(key, "http://example.com/Case%2F?q=ABC")
        self.assertEqual(parsed.hostname, "example.com")

    def test_conflict_quarantine_and_group_isolation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = io.StringIO()
            writer = csv.writer(data)
            writer.writerow(["URL", "Label"])
            for index in range(120):
                for subdomain in ("a", "b"):
                    writer.writerow([f"https://{subdomain}.fixture{index}.com/", "bad" if index % 2 else "good"])
            writer.writerow(["https://a.fixture0.com/", "good"])
            writer.writerow(["https://conflict.com/", "good"])
            writer.writerow(["https://conflict.com/", "bad"])
            archive = root / "source.zip"
            with ZipFile(archive, "w") as source:
                source.writestr("phishing_site_urls.csv", data.getvalue())
            metadata = root / "metadata.json"
            metadata.write_text(json.dumps({"currentVersionNumber": 1, "licenseName": "fixture"}))
            report = prepare(archive, metadata, root / "output")
            self.assertEqual(report["exclusions"]["conflicting_rows_quarantined"], 2)
            self.assertEqual(report["exclusions"]["duplicate_rows_removed"], 1)
            self.assertEqual(report["domain_overlap"], 0)
            with (root / "output" / "prepared.csv").open() as source:
                rows = list(csv.DictReader(source))
            group_splits = {}
            for row in rows:
                self.assertEqual(group_splits.setdefault(row["domain_group"], row["split"]), row["split"])
