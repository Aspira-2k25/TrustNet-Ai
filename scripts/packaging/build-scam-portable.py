"""Build a secret-free scam export from an explicit runtime allowlist."""
from pathlib import Path
import hashlib, json, shutil, zipfile, sys

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / 'exports' / 'TrustNet-Scam-Portable'
ARCHIVE = DEST.parent / 'TrustNet-Scam-Portable.zip'
refresh = '--refresh' in sys.argv
if (DEST.exists() or ARCHIVE.exists()) and not refresh:
    raise SystemExit('Export already exists. Preserve it or choose a new export name before rebuilding.')
if refresh and ((DEST / '.env').exists() or (DEST / '.venv-scam').exists()):
    raise SystemExit('Refusing to rebuild an export containing a local environment/configuration.')
DEST.mkdir(parents=True, exist_ok=refresh)
previous = {}
if refresh and (DEST / 'PACKAGE-MANIFEST.json').exists():
    previous = json.loads((DEST / 'PACKAGE-MANIFEST.json').read_text(encoding='utf-8'))['files']
    for path in DEST.rglob('*'):
        if path.is_file() and path.name != 'PACKAGE-MANIFEST.json':
            relative = path.relative_to(DEST).as_posix()
            if relative not in previous or hashlib.sha256(path.read_bytes()).hexdigest() != previous[relative]['sha256']:
                raise SystemExit('Refusing to overwrite an unrecognized/edited export file: ' + relative)
planned = set()
excluded = {'__pycache__', 'tests', '.pytest_cache', 'node_modules', '.venv', '.venv-scam'}
trees = ['shared', 'gateway/app', 'services/auth/app', 'services/scan_management/app',
         'services/scam_message/app', 'services/trust_engine/app', 'models/scam_message', 'extensions/trustnet-mail',
         'frontend/src', 'frontend/dist', 'docs/scam-portable']
files = ['models/__init__.py', 'gateway/__init__.py', 'services/__init__.py',
         'scripts/setup/install-scam.ps1', 'scripts/setup/install-scam-model.py', 'scripts/ops/start-scam.ps1', 'scripts/ops/stop-scam.ps1', 'scripts/checks/verify-scam.py',
         'docs/TEAM_SETUP.md', 'scripts/checks/smoke-scam.py', '.env.example', 'services/scam_message/README.md',
         'services/scam_message/requirements-portable.txt', 'frontend/package.json', 'frontend/package-lock.json',
         'frontend/index.html', 'frontend/vite.config.ts', 'frontend/tsconfig.json',
         'frontend/tsconfig.app.json', 'frontend/tsconfig.node.json', 'frontend/eslint.config.js', 'frontend/.oxlintrc.json',
         'docs/SCAM_CONTINUATION_HANDOFF.md']
files += ['docs/SCAM_RESEARCH_EVIDENCE.md', 'docs/SCAM_IMPLEMENTATION_MAP.md']
for tree in trees:
    source = ROOT / tree
    if not source.is_dir():
        raise FileNotFoundError(source)
    for path in source.rglob('*'):
        if not path.is_file() or any(p in excluded for p in path.relative_to(source).parts):
            continue
        if path.suffix.lower() in {'.pyc', '.sqlite', '.db', '.log'} or path.name.startswith('.env'):
            continue
        target = DEST / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        planned.add(path.relative_to(ROOT).as_posix())
for name in files:
    source = ROOT / name
    if source.is_file():
        target = DEST / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        planned.add(name)
shutil.copy2(ROOT / 'docs/scam-portable/README.md', DEST / 'README.md')
planned.add('README.md')
for relative in previous.keys() - planned:
    stale = (DEST / relative).resolve()
    if not stale.is_relative_to(DEST.resolve()):
        raise ValueError('Unsafe previous manifest path')
    if stale.is_file():
        stale.unlink()  # Only unchanged generated files verified above.
manifest = {'schema_version': 1, 'model': json.loads((ROOT / 'models/scam_message/artifacts/manifest.json').read_text(encoding='utf-8'))['model_version'],
            'scope': 'Scam-only CPU runtime; other image/audio/video services are not packaged.',
            'files': {}}
for path in sorted(DEST.rglob('*')):
    if path.is_file() and path.name != 'PACKAGE-MANIFEST.json':
        manifest['files'][path.relative_to(DEST).as_posix()] = {
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size}
(DEST / 'PACKAGE-MANIFEST.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
with zipfile.ZipFile(ARCHIVE, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
    for path in sorted(DEST.rglob('*')):
        if path.is_file():
            archive.write(path, path.relative_to(DEST.parent))
digest = hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
ARCHIVE.with_suffix('.zip.sha256').write_text(digest + '  ' + ARCHIVE.name + '\n', encoding='ascii')
print(json.dumps({'zip': str(ARCHIVE), 'bytes': ARCHIVE.stat().st_size,
                  'sha256': digest, 'files': len(manifest['files'])}, indent=2))
