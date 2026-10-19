"""Reproducible, offline preparation of the approved Kaggle version 1 archive."""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import io
import json
from pathlib import Path
import zipfile
from models.phishing_url.preprocessing.url_parser import parse_url

def normalize(raw):
    # Keep the source verbatim separately. Scheme-less source rows have unknown
    # transport; HTTP is a parsing convention, not a historical observation.
    inferred = "://" not in raw
    url = "http://" + raw if inferred else raw
    parsed = parse_url(url)
    parts = parsed.parts
    authority = parsed.hostname
    if parsed.is_ip and ":" in authority:
        authority = f"[{authority}]"
    if parts.port is not None:
        authority += f":{parts.port}"
    if parts.username is not None:
        # Preserve original userinfo including password without decoding.
        authority = parts.netloc.rsplit("@", 1)[0] + "@" + authority
    key = parts._replace(scheme=parts.scheme.lower(), netloc=authority).geturl()
    return url, key, inferred, parsed

def prepare(archive, metadata_path, output):
    import numpy as np
    import tldextract
    from sklearn.model_selection import StratifiedGroupKFold
    metadata = json.loads(Path(metadata_path).read_text(encoding="utf-8"))
    if metadata.get("currentVersionNumber") != 1:
        raise ValueError("Review dataset changes before importing another version")
    extract = tldextract.TLDExtract(suffix_list_urls=(), cache_dir=None, include_psl_private_domains=True)
    snapshot = Path(tldextract.__file__).parent / ".tld_set_snapshot"
    archive = Path(archive)
    with zipfile.ZipFile(archive) as source:
        raw_bytes = source.read("phishing_site_urls.csv")
    source_rows = list(csv.DictReader(io.StringIO(raw_bytes.decode("utf-8-sig"))))
    labels, counts, by_key = Counter(), Counter(), defaultdict(list)
    for row in source_rows:
        labels[row["Label"]] += 1
        if row["Label"] not in {"good", "bad"}:
            raise ValueError("Unknown source label")
        original = row["URL"]
        try:
            url, key, inferred, parsed = normalize(original)
            domain = extract(parsed.hostname)
            group = domain.top_domain_under_public_suffix
            if not group and not parsed.is_ip:
                counts["unrecognized_suffix"] += 1
                continue
            group = group or parsed.hostname
        except (ValueError, UnicodeError):
            counts["invalid_url"] += 1
            continue
        by_key[key].append(dict(url=url, original_url=original, label=int(row["Label"] == "bad"), domain_group=group, scheme_inferred=int(inferred)))
    rows = []
    for key in sorted(by_key):
        candidates = by_key[key]
        if len({row["label"] for row in candidates}) > 1:
            counts["conflicting_url_groups"] += 1
            counts["conflicting_rows_quarantined"] += len(candidates)
            continue
        counts["duplicate_rows_removed"] += len(candidates) - 1
        rows.append(candidates[0])
    y = np.array([row["label"] for row in rows])
    groups = np.array([row["domain_group"] for row in rows])
    indices = np.arange(len(rows))
    # Reserve a test partition before creating any development folds.
    dev, test = next(StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42).split(indices, y, groups))
    fold_ids = np.full(len(rows), -1)
    for fold, (_, heldout) in enumerate(StratifiedGroupKFold(n_splits=10, shuffle=True, random_state=43).split(dev, y[dev], groups[dev])):
        if set(y[dev[heldout]]) != {0, 1}:
            raise ValueError("A development fold lacks both classes; reduce folds only with a documented exception")
        fold_ids[dev[heldout]] = fold
    test_set = set(test.tolist())
    partitions, partition_groups = defaultdict(Counter), defaultdict(set)
    for index, row in enumerate(rows):
        row["fold"] = int(fold_ids[index])
        row["split"] = "test" if index in test_set else "validation" if fold_ids[index] == 0 else "train"
        partitions[row["split"]][str(row["label"])] += 1
        partition_groups[row["split"]].add(row["domain_group"])
    for split in ("train", "validation", "test"):
        if set(partitions[split]) != {"0", "1"}:
            raise ValueError("A partition lacks both classes; review grouped split")
    if any(partition_groups[a] & partition_groups[b] for a, b in (("train", "validation"), ("train", "test"), ("validation", "test"))):
        raise ValueError("Domain leakage")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    prepared = output / "prepared.csv"
    with prepared.open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=["url", "original_url", "label", "domain_group", "scheme_inferred", "fold", "split"])
        writer.writeheader()
        writer.writerows(rows)
    report = dict(source="taruntiwarihp/phishing-site-urls", version=1,
                  source_rows=len(source_rows), original_label_counts=dict(labels),
                  retained_rows=len(rows), exclusions=dict(counts),
                  original_label_mapping={"good": 0, "bad": 1},
                  archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                  source_csv_sha256=hashlib.sha256(raw_bytes).hexdigest(),
                  metadata_sha256=hashlib.sha256(Path(metadata_path).read_bytes()).hexdigest(),
                  prepared_sha256=hashlib.sha256(prepared.read_bytes()).hexdigest(),
                  tldextract_version=tldextract.__version__, psl_sha256=hashlib.sha256(snapshot.read_bytes()).hexdigest(),
                  include_private_suffixes=True, split_seed=42, fold_seed=43,
                  development_folds=10, partition_labels={k: dict(v) for k, v in partitions.items()},
                  partition_domains={k: len(v) for k, v in partition_groups.items()},
                  scheme_inferred_rows=sum(row["scheme_inferred"] for row in rows),
                  license=metadata["licenseName"], domain_overlap=0,
                  source_lineage="Uploader description does not identify original collection sources",
                  temporal_generalization="unmeasured: no per-row observation dates",
                  campaign_grouping="unmeasured: registrable domain grouping only",
                  normalization="preserve path/query/fragment encoding and case; normalize host/scheme for dedup; assume HTTP only for parsing source rows lacking scheme")
    (output / "preparation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("archive")
    parser.add_argument("metadata")
    parser.add_argument("output")
    args = parser.parse_args()
    print(json.dumps(prepare(args.archive, args.metadata, args.output), indent=2))
