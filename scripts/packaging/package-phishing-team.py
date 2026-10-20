"""Package or verify the selected teammate model without loading pickle files."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "models/phishing_url/checkpoints/regional_recall_v1"
EXPECTED_MANIFEST = "30407968c6d02ab076db933a74201d7ac29853637e2d98d2a0faed897a8c6a9c"


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verified_files() -> list[Path]:
    manifest_path = BUNDLE / "manifest.json"
    if digest(manifest_path) != EXPECTED_MANIFEST:
        raise ValueError("Manifest does not match the accepted regional-recall-v1 release")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["model_version"] != "regional-recall-v1" or len(manifest["components"]) != 8:
        raise ValueError("Unexpected model release or component count")
    files = [manifest_path]
    for component in manifest["components"].values():
        name = component["artifact"]
        if not isinstance(name, str) or Path(name).name != name or "/" in name or "\\" in name:
            raise ValueError("Component must be a plain filename")
        path = BUNDLE / name
        if digest(path) != component["sha256"]:
            raise ValueError(f"Checksum mismatch: {name}")
        files.append(path)
    if len(set(files)) != len(files):
        raise ValueError("Duplicate component path")
    return files


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="Verify installed files; create nothing")
    args = parser.parse_args()
    files = verified_files()
    if args.verify:
        print("PASS: regional-recall-v1 manifest and all eight component SHA-256 checksums match.")
        return
    output = ROOT / "exports/TrustNet-Phishing-regional-recall-v1.zip"
    checksum = output.with_suffix(".zip.sha256")
    if output.exists() or checksum.exists():
        raise FileExistsError(f"Refusing to replace an existing release: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(ROOT).as_posix())
        archive.write(ROOT / "README.md", "README.md")
    with checksum.open("x", encoding="ascii") as stream:
        stream.write(f"{digest(output)}  {output.name}\n")
    print(f"Created: {output}\nChecksum: {checksum}\nContains model + guide only; no secrets or datasets.")


if __name__ == "__main__":
    main()
