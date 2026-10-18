"""Audit the official archive without assigning unverified label semantics."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import zipfile

def audit(archive):
    archive = Path(archive)
    with zipfile.ZipFile(archive) as source:
        raw = source.read("Training Dataset.arff")
        dictionary = source.read("Phishing Websites Features.docx")
    text = raw.decode("utf-8")
    names = re.findall(r"(?im)^@attribute\s+(\S+)", text)
    data = re.split(r"(?im)^@data\s*$", text, maxsplit=1)[1]
    rows = [tuple(int(value.strip()) for value in line.split(","))
            for line in data.splitlines() if line.strip() and not line.startswith("%")]
    if len(names) != 31 or any(len(row) != 31 for row in rows):
        raise ValueError("Unexpected UCI feature schema")
    grouped = defaultdict(set)
    for row in rows:
        grouped[row[:-1]].add(row[-1])
    return {"dataset": "UCI Phishing Websites", "uci_id": 327,
            "source": "https://archive.ics.uci.edu/dataset/327/phishing",
            "archive_url": "https://archive.ics.uci.edu/static/public/327/phishing+websites.zip",
            "license": "CC-BY-4.0", "audited_at": datetime.now(timezone.utc).isoformat(),
            "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            "arff_sha256": hashlib.sha256(raw).hexdigest(),
            "feature_dictionary_sha256": hashlib.sha256(dictionary).hexdigest(),
            "rows": len(rows), "feature_count": len(names) - 1, "feature_names": names[:-1],
            "target": names[-1], "original_label_counts": dict(Counter(str(row[-1]) for row in rows)),
            "exact_duplicate_rows": len(rows) - len(set(rows)),
            "unique_feature_vectors": len(grouped),
            "conflicting_feature_vectors": sum(len(labels) > 1 for labels in grouped.values()),
            "label_mapping_status": "pending: official metadata lists integer labels but does not explain target direction",
            "domain_grouping_available": False, "temporal_grouping_available": False,
            "live_url_compatible": False,
            "split_policy": "Group identical feature vectors before splitting; domain/time generalization cannot be measured from this release"}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("archive")
    parser.add_argument("output")
    args = parser.parse_args()
    report = audit(args.archive)
    Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("rows", "original_label_counts", "exact_duplicate_rows", "conflicting_feature_vectors")}, indent=2))
