import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from services.phishing_url.app.services.artifact_store import download
class Storage:
    def __init__(self,manifest):self.manifest=manifest
    def get_object(self,**kwargs):return {'Body':io.BytesIO(self.manifest)}
    def download_file(self,bucket,key,target):Path(target).write_bytes(b'trusted fixture')
class ArtifactTests(unittest.TestCase):
    def test_checked_download_and_manifest_digest(self):
        manifest=json.dumps({'artifact':'model.joblib','sha256':hashlib.sha256(b'trusted fixture').hexdigest()}).encode()
        with tempfile.TemporaryDirectory() as directory:
            path=download('s3://bucket/v1',directory,hashlib.sha256(manifest).hexdigest(),Storage(manifest))
            self.assertTrue(path.exists())
            with self.assertRaises(ValueError):download('s3://bucket/v1',directory,'0'*64,Storage(manifest))
    def test_traversal_rejected(self):
        manifest=json.dumps({'artifact':'../outside.joblib','sha256':'0'*64}).encode()
        with tempfile.TemporaryDirectory() as directory,self.assertRaises(ValueError):download('s3://bucket/v1',directory,hashlib.sha256(manifest).hexdigest(),Storage(manifest))
