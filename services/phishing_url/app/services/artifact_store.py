"""Versioned S3/MinIO artifact transport with a trusted manifest digest."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

def client():
    import boto3
    return boto3.client('s3',endpoint_url=os.getenv('PHISHING_S3_ENDPOINT'),region_name=os.getenv('AWS_REGION','us-east-1'))
def location(uri):
    parsed=urlsplit(uri)
    if parsed.scheme!='s3' or not parsed.netloc or not parsed.path.strip('/'):
        raise ValueError('Use s3://bucket/versioned-prefix')
    return parsed.netloc,parsed.path.strip('/')
def artifacts(manifest):
    if manifest.get('kind')=='lightgbm_bert':
        fusion=manifest['fusion']
        return {manifest['lightgbm']['artifact']:manifest['lightgbm']['sha256'],fusion['calibrator']:fusion['calibrator_sha256'],**manifest['bert']['files'],**{entry['artifact']:entry['sha256'] for entry in fusion['fallbacks'].values()}}
    return {manifest['artifact']:manifest['sha256']}
def download(uri,destination,manifest_digest,storage=None):
    if not manifest_digest or len(manifest_digest)!=64:raise ValueError('Trusted manifest SHA256 required')
    storage=storage or client();bucket,prefix=location(uri)
    raw=storage.get_object(Bucket=bucket,Key=prefix+'/manifest.json')['Body'].read(262145)
    if len(raw)>262144 or hashlib.sha256(raw).hexdigest()!=manifest_digest:raise ValueError('Manifest checksum/size mismatch')
    manifest=json.loads(raw);destination=Path(destination).resolve();destination.mkdir(parents=True,exist_ok=True)
    for relative,digest in artifacts(manifest).items():
        path=(destination/relative).resolve()
        if not path.is_relative_to(destination):raise ValueError('Artifact path outside bundle')
        path.parent.mkdir(parents=True,exist_ok=True)
        storage.download_file(bucket,prefix+'/'+relative,str(path))
        if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('Artifact checksum mismatch')
    (destination/'manifest.json').write_bytes(raw)
    return destination/'manifest.json'
def publish(manifest_path,uri,storage=None):
    storage=storage or client();bucket,prefix=location(uri);path=Path(manifest_path).resolve()
    raw=path.read_bytes();manifest=json.loads(raw)
    for relative,digest in artifacts(manifest).items():
        artifact=(path.parent/relative).resolve()
        if not artifact.is_relative_to(path.parent) or hashlib.sha256(artifact.read_bytes()).hexdigest()!=digest:
            raise ValueError('Refuse unchecked artifact publication')
        storage.upload_file(str(artifact),bucket,prefix+'/'+relative)
    storage.put_object(Bucket=bucket,Key=prefix+'/manifest.json',Body=raw)
    return hashlib.sha256(raw).hexdigest()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('manifest');p.add_argument('destination');a=p.parse_args();print(publish(a.manifest,a.destination))
