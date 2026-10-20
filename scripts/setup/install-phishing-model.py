"""Install the trusted teammate release without overwriting other files."""
import argparse
import hashlib
import importlib.util
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('phishing_package', ROOT / 'scripts/packaging/package-phishing-team.py')
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)

def install(package):
    with zipfile.ZipFile(package) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError('Duplicate archive paths')
        prefix = 'models/phishing_url/checkpoints/regional_recall_v1/'
        manifest_bytes = archive.read(prefix + 'manifest.json')
        if hashlib.sha256(manifest_bytes).hexdigest() != release.EXPECTED_MANIFEST:
            raise ValueError('Untrusted release manifest')
        import json
        manifest = json.loads(manifest_bytes)
        expected = {prefix + 'manifest.json': release.EXPECTED_MANIFEST}
        for component in manifest['components'].values():
            name = component['artifact']
            if Path(name).name != name or '/' in name or '\\' in name:
                raise ValueError('Invalid component filename')
            expected[prefix + name] = component['sha256']
        allowed_extras = {'docs/phishing/TEAM_SETUP.md', 'PHISHING_TEAM_SETUP.md', 'TEAM_SETUP.md','README.md'}
        if set(names) - set(expected) - allowed_extras:
            raise ValueError('Unexpected archive contents')
        checked = []
        for name, checksum in expected.items():
            payload = archive.read(name)
            if hashlib.sha256(payload).hexdigest() != checksum:
                raise ValueError('Checksum mismatch: ' + name)
            destination = (ROOT / name).resolve()
            if not destination.is_relative_to(ROOT):
                raise ValueError('Refusing to write outside repository: ' + name)
            checked.append((destination, payload))
        for destination, payload in checked:
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not destination.exists() or destination.read_bytes() != payload:
                with destination.open('wb') as stream:
                    stream.write(payload)
    release.verified_files()
    print('PASS: installed and verified regional-recall-v1 (all eight components).')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', type=Path)
    install(parser.parse_args().package)
