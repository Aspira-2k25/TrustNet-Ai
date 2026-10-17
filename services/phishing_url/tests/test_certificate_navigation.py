import unittest
import ssl
from datetime import datetime,timezone,timedelta
from unittest.mock import patch,Mock
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from services.phishing_url.app.services.certificate_analysis import inspect_certificate
from services.phishing_url.app.services.metadata_collector import collect
from services.phishing_url.app.services.safe_fetch import fetch
from models.phishing_url.inference.navigation import inspect_path
from models.phishing_url.inference.forensics import analyze

class CertificateNavigationTests(unittest.TestCase):
    def test_certificate_properties_not_a_safety_verdict(self):
        key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'test.example')])
        now=datetime.now(timezone.utc)
        cert=(x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
              .serial_number(7).not_valid_before(now-timedelta(days=1)).not_valid_after(now+timedelta(days=30))
              .add_extension(x509.SubjectAlternativeName([x509.DNSName('test.example')]),critical=False).sign(key,hashes.SHA256()))
        # Parsing assumes the caller's TLS handshake has already verified trust.
        result=inspect_certificate(cert.public_bytes(serialization.Encoding.DER),'TLSv1.3',('TLS_AES_256_GCM_SHA384','TLSv1.3',256))
        self.assertEqual(result['signature_hash'],'sha256')
        self.assertEqual(result['public_key_bits'],2048)
        self.assertFalse(result['weak_public_key'])
        self.assertEqual(len(result['sha256_fingerprint']),64)
        self.assertEqual(result['revocation_status'],'NOT_CHECKED')
        self.assertIn('do not establish website safety',result['definition'])

    def test_bad_certificate_recorded_without_insecure_retry(self):
        error=ssl.SSLCertVerificationError('verification failed');error.verify_code=10;error.verify_message='certificate expired'
        with patch('services.phishing_url.app.services.metadata_collector.public_addresses',return_value=['8.8.8.8']),patch('services.phishing_url.app.services.metadata_collector.lookup',return_value={'status':'UNAVAILABLE'}),patch('services.phishing_url.app.services.metadata_collector.fetch',side_effect=error) as get:
            observed=collect('https://test.example/',True)
        self.assertFalse(observed['signals']['tls']['validated'])
        report=analyze('https://test.example/',observed)
        self.assertIn('TLS_VALIDATION_FAILED',{f['code'] for f in report['findings']})
        self.assertEqual(report['outcome'],'REVIEW')
        # One website call and one independent RDAP call; no insecure retry.
        self.assertEqual(get.call_count,2)

    def test_intermediate_downgrade_and_domain_bounces(self):
        urls=['https://one.com/','http://two.net/','https://one.com/final']
        obs={'signals':{'http':{'status':'observed','final_url':urls[-1]},'navigation':{'status':'observed','hops':[{'url':u,'scheme':u.split(':')[0]} for u in urls]}}}
        codes={f['code'] for f in analyze(urls[0],obs)['findings']}
        self.assertTrue({'HTTPS_DOWNGRADE','MULTI_DOMAIN_NAVIGATION'}<=codes)

    def test_paths_and_redirect_parameters_are_not_followed_or_proof(self):
        path=inspect_path('https://example.com/%252e%252e%252faccounts?next=https%3A%2F%2Fother.net%2F')
        self.assertTrue(path['double_encoding']);self.assertTrue(path['dot_segments'])
        self.assertEqual(path['navigation_parameters'][0]['hostname'],'other.net')
        report=analyze('https://example.com/login?redirect_uri=https%3A%2F%2Fother.net%2F')
        self.assertEqual(report['outcome'],'NO_STRONG_INDICATORS')
        self.assertEqual(inspect_path('https://example.com/3/')['segments'],1)

    def test_fetch_records_each_observed_redirect_hop(self):
        first,final=Mock(),Mock();first.status=302;final.status=200
        first.getheader.return_value='http://example.com/final'
        final.getheader.side_effect=lambda name,default=None: 'text/html' if name=='Content-Type' else default
        final.read1.return_value=b''
        with patch('services.phishing_url.app.services.safe_fetch.public_addresses',return_value=['8.8.8.8']),patch('http.client.HTTPConnection') as connection:
            connection.return_value.getresponse.side_effect=[first,final]
            response=fetch('http://example.com/start')
            self.assertEqual(connection.return_value.request.call_args_list[0].kwargs['headers']['Host'],'example.com')
        self.assertEqual([h['status_code'] for h in response['navigation']],[302,200])
        self.assertEqual(response['navigation'][0]['path'],'/start')
