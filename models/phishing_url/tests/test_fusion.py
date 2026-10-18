import csv
import tempfile
from pathlib import Path
import unittest
from models.phishing_url.training.tune_ensemble import tune

class FusionTests(unittest.TestCase):
    def test_calibration_and_threshold_are_separated(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            paths=[root/"left.csv",root/"right.csv"]
            for path in paths:
                with path.open("w",newline="") as target:
                    writer=csv.writer(target);writer.writerow(["url","domain_group","label","probability"])
                    for index in range(150):
                        label=index%2;writer.writerow([f"https://fixture{index}.com",f"fixture{index}.com",label,.8 if label else .2])
            report=tune(*paths,root/"fusion")
            self.assertEqual(set(report["partition_counts"]),{"0","1","2"})
            self.assertEqual(set(report["fallbacks"]),{"lightgbm","bert"})
            self.assertLessEqual(report["threshold"],1)
            paths[1].write_text("url,domain_group,label,probability\n")
            with self.assertRaises(ValueError):tune(*paths,root/"other")
