"""Install only approved, checksummed selected artifacts from the shared ZIP."""
from pathlib import Path
import argparse,hashlib,json,os,tempfile,zipfile
root=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--package',type=Path,required=True)
parser.add_argument('--baseline',action='store_true',help='Restore the documented, separately supplied hybrid-2 rollback package')
args=parser.parse_args()
metadata_name='rollback-package.json' if args.baseline else 'model-package.json'
metadata=json.loads((root/'models/scam_message'/metadata_name).read_text(encoding='utf-8'))
def digest(path):
 sha=hashlib.sha256()
 with path.open('rb') as stream:
  for chunk in iter(lambda:stream.read(1024*1024),b''):sha.update(chunk)
 return sha.hexdigest()
if digest(args.package)!=metadata['sha256']:raise SystemExit('Model ZIP checksum mismatch. Request the exact selected version/checksum.')
destination=root/'models/scam_message/artifacts';destination.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(args.package) as archive:
 for name,expected in metadata['files'].items():
  if Path(name).name!=name or '\\' in name or name in {'.','..'}:raise SystemExit('Invalid artifact filename')
  path=destination/name
  if path.is_file() and digest(path)==expected['sha256']:continue
  entry=archive.getinfo('artifacts/'+name)
  if entry.file_size!=expected['bytes']:raise SystemExit('Artifact size mismatch: '+name)
  temporary=None
  try:
   with tempfile.NamedTemporaryFile(dir=destination,delete=False) as stream:
    temporary=Path(stream.name);sha=hashlib.sha256()
    with archive.open(entry) as source:
     for chunk in iter(lambda:source.read(1024*1024),b''):
      sha.update(chunk);stream.write(chunk)
   if sha.hexdigest()!=expected['sha256']:raise SystemExit('Artifact checksum mismatch: '+name)
   os.replace(temporary,path);temporary=None
  finally:
   if temporary is not None:temporary.unlink(missing_ok=True)
print('Installed and verified '+metadata['model_version']+'; no external cache or research folder required.')
