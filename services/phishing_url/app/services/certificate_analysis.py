"""Describe the leaf certificate after OpenSSL validates chain, dates and hostname.

A valid signature authenticates the TLS endpoint, not its business or content.
"""
from datetime import datetime, timezone
import hashlib

def inspect_certificate(der, tls_version=None, cipher=None):
    from cryptography import x509
    from cryptography.hazmat.primitives.asymmetric import rsa, ec, dsa
    cert = x509.load_der_x509_certificate(der)
    key = cert.public_key()
    try:
        signature_hash = cert.signature_hash_algorithm.name if cert.signature_hash_algorithm else None
    except Exception:
        signature_hash = None
    key_type = 'RSA' if isinstance(key,rsa.RSAPublicKey) else 'EC' if isinstance(key,ec.EllipticCurvePublicKey) else 'DSA' if isinstance(key,dsa.DSAPublicKey) else type(key).__name__
    bits = getattr(key,'key_size',None)
    try: sans = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value.get_values_for_type(x509.DNSName)
    except x509.ExtensionNotFound: sans = []
    now = datetime.now(timezone.utc)
    return {'status':'observed','chain_validated':True,'hostname_validated':True,
            'signature_validation':'TLS handshake validated certificate chain using the configured CA trust store.',
            'sha256_fingerprint':hashlib.sha256(der).hexdigest(),
            'subject':cert.subject.rfc4514_string(),'issuer':cert.issuer.rfc4514_string(),
            'not_before':cert.not_valid_before_utc.isoformat(),'not_after':cert.not_valid_after_utc.isoformat(),
            'expires_in_days':(cert.not_valid_after_utc-now).days,
            'signature_algorithm_oid':cert.signature_algorithm_oid.dotted_string,'signature_hash':signature_hash,
            'public_key_type':key_type,'public_key_bits':bits,'dns_names':sans[:100],
            'weak_signature_hash':signature_hash in {'md5','sha1'},
            'weak_public_key':key_type in {'RSA','DSA'} and bits is not None and bits<2048,
            'tls_version':tls_version,'cipher':cipher[0] if cipher else None,
            'revocation_status':'NOT_CHECKED',
            'definition':'TLS identity and cryptography only. Issuer, fingerprint and a valid signature do not establish website safety.'}
