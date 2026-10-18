import unittest
from unittest.mock import patch, Mock
from services.phishing_url.app.services.safe_fetch import public_addresses, FetchBlocked, fetch, PinnedHTTPSConnection
class FetchTests(unittest.TestCase):
    def test_private_addresses_blocked(self):
        for host in ("127.0.0.1","10.0.0.1","169.254.169.254","::1","::ffff:127.0.0.1","192.168.1.1"):
            with self.subTest(host=host), self.assertRaises(FetchBlocked): public_addresses(host,443)
    def test_mixed_public_private_dns_blocked(self):
        with patch("dns.resolver.Resolver") as resolver:
            resolver.return_value.resolve.return_value=["8.8.8.8","127.0.0.1"]
            with self.assertRaises(FetchBlocked): public_addresses("example.com",443)
    def test_ipv6_timeout_does_not_discard_validated_ipv4(self):
        import dns.exception
        with patch('dns.resolver.Resolver') as resolver:
            resolver.return_value.resolve.side_effect=[['8.8.8.8'],dns.exception.Timeout()]
            self.assertEqual(public_addresses('example.com',443),['8.8.8.8'])
        with patch('dns.resolver.Resolver') as resolver:
            resolver.return_value.resolve.side_effect=[['127.0.0.1'],dns.exception.Timeout()]
            with self.assertRaises(FetchBlocked):public_addresses('example.com',443)
    def test_disallowed_port_and_userinfo(self):
        for url in ("http://example.com:22/","http://user@example.com/"):
            with self.assertRaises(FetchBlocked): fetch(url)
    def test_tls_checks_hostname(self):
        with patch("socket.create_connection") as connect:
            connection=PinnedHTTPSConnection("example.com","8.8.8.8",443,1); connection._context=Mock(); connection.connect()
            connect.assert_called_once_with(("8.8.8.8",443),1)
            connection._context.wrap_socket.assert_called_once_with(connect.return_value,server_hostname="example.com")
    def test_redirect_revalidation(self):
        with patch("services.phishing_url.app.services.safe_fetch.public_addresses",side_effect=[["8.8.8.8"],FetchBlocked("private")]) as resolve, patch("http.client.HTTPConnection") as connection:
            response=connection.return_value.getresponse.return_value; response.status=302; response.getheader.return_value="http://127.0.0.1/"
            with self.assertRaises(FetchBlocked) as error: fetch("http://example.com")
            self.assertEqual(resolve.call_count,2)
            self.assertEqual(error.exception.navigation[0]['redirect_to'],'http://127.0.0.1/')
