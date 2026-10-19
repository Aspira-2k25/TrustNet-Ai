"""Pinned-address HTTP collection. Deploy on an isolated egress-only network."""
import http.client
import ipaddress
import socket
import ssl
import time
from urllib.parse import urljoin
from models.phishing_url.preprocessing.url_parser import parse_url

class FetchBlocked(ValueError):
    pass

def public_addresses(host, port):
    try:
        addresses = [str(ipaddress.ip_address(host))]
    except ValueError:
        import dns.resolver
        resolver = dns.resolver.Resolver()
        resolver.timeout, resolver.lifetime = 1, 2
        addresses = []
        for kind in ("A", "AAAA"):
            try:
                addresses.extend(str(record) for record in resolver.resolve(host, kind))
            except dns.resolver.NoAnswer:
                continue
            except dns.exception.DNSException:
                # A failed optional IPv6 lookup must not discard usable IPv4.
                # Only the validated/pinned returned address is ever contacted.
                if kind == 'AAAA' and addresses:
                    continue
                raise
        addresses = sorted(set(addresses))
    if not addresses:
        raise FetchBlocked("No DNS address")
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global or (ip.version == 6 and ip.ipv4_mapped is not None and not ip.ipv4_mapped.is_global):
            raise FetchBlocked("Non-public destination")
    return sorted(addresses, key=lambda address: (ipaddress.ip_address(address).version, address))

class PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host, address, port, timeout):
        super().__init__(host, port, timeout=timeout, context=ssl.create_default_context())
        self.address = address
    def connect(self):
        # Connect to validated IP, but validate certificate and SNI for URL hostname.
        self.sock = socket.create_connection((self.address, self.port), self.timeout)
        self.sock = self._context.wrap_socket(self.sock, server_hostname=self.host)

def fetch(url, *, timeout=5, max_bytes=262144, max_redirects=3):
    navigation = []
    try:
        return _fetch(url,timeout=timeout,max_bytes=max_bytes,max_redirects=max_redirects,navigation=navigation)
    except Exception as exc:
        exc.navigation = navigation
        raise

def _fetch(url, *, timeout, max_bytes, max_redirects, navigation):
    deadline = time.monotonic() + timeout
    for hop in range(max_redirects + 1):
        parsed = parse_url(url)
        if parsed.parts.username is not None:
            raise FetchBlocked("Userinfo collection disabled")
        port = parsed.parts.port or (443 if parsed.parts.scheme == "https" else 80)
        if port not in {80, 443}:
            raise FetchBlocked("Collection port not allowed")
        addresses = public_addresses(parsed.hostname, port)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Collection deadline exceeded")
        connection = (PinnedHTTPSConnection(parsed.hostname, addresses[0], port, remaining)
                      if parsed.parts.scheme == "https" else http.client.HTTPConnection(addresses[0], port, timeout=remaining))
        try:
            path = parsed.parts.path or "/"
            if parsed.parts.query:
                path += "?" + parsed.parts.query
            host_header = parsed.hostname if not (parsed.is_ip and ":" in parsed.hostname) else f"[{parsed.hostname}]"
            # Default ports must not leak into a server-generated HTTPS redirect.
            # Some origins copy Host verbatim, turning HTTP :80 into HTTPS :80.
            if port != (443 if parsed.parts.scheme == 'https' else 80):
                host_header += f":{port}"
            connection.request("GET", path, headers={"Host": host_header, "User-Agent": "TrustNet-Phishing/1.0", "Accept-Encoding": "identity", "Connection": "close"})
            certificate = connection.sock.getpeercert() if isinstance(connection, PinnedHTTPSConnection) and connection.sock else None
            certificate_details = None
            if certificate:
                from .certificate_analysis import inspect_certificate
                certificate_details = inspect_certificate(connection.sock.getpeercert(binary_form=True), connection.sock.version(), connection.sock.cipher())
            response = connection.getresponse()
            navigation.append({'url':url,'hostname':parsed.hostname,'status_code':response.status,
                               'scheme':parsed.parts.scheme,'path':parsed.parts.path or '/',
                               'certificate_details':certificate_details})
            if response.status in {301, 302, 303, 307, 308}:
                location = response.getheader("Location")
                if not location or hop == max_redirects:
                    raise FetchBlocked("Redirect limit or missing location")
                url = urljoin(url, location)
                navigation[-1]['redirect_to'] = url
                continue
            if response.getheader("Content-Encoding", "identity").lower() != "identity":
                raise FetchBlocked("Encoded response unsupported")
            content = bytearray()
            truncated = False
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("Collection deadline exceeded")
                if connection.sock:
                    connection.sock.settimeout(remaining)
                chunk = response.read1(min(8192, max_bytes + 1 - len(content)))
                if not chunk:
                    break
                content.extend(chunk)
                if len(content) > max_bytes:
                    truncated = True
                    break
            return {"status": response.status, "body": bytes(content[:max_bytes]), "truncated": truncated, "content_type": response.getheader("Content-Type", ""), "certificate": certificate, "certificate_details":certificate_details, "navigation":navigation, "resolved_addresses": addresses, "redirects": hop, "final_url": url}
        finally:
            connection.close()
    raise FetchBlocked("Redirect limit")
