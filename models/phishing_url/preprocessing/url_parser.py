"""Offline URL validation. This module never resolves or fetches a URL."""
from dataclasses import dataclass
import ipaddress
from urllib.parse import urlsplit, SplitResult

PREPROCESSING_VERSION = "url-lexical-v1"

@dataclass(frozen=True)
class ParsedURL:
    original: str
    parts: SplitResult
    hostname: str
    is_ip: bool

def parse_url(url: str) -> ParsedURL:
    if not isinstance(url, str) or not url or len(url) > 8192:
        raise ValueError("URL must contain 1–8192 characters")
    if any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in url) or "\\" in url:
        raise ValueError("URL contains whitespace, controls or backslashes")
    try:
        parts = urlsplit(url)
        if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
            raise ValueError("An absolute HTTP or HTTPS URL is required")
        port = parts.port
        if port is not None and not 1 <= port <= 65535:
            raise ValueError("Invalid port")
        host = parts.hostname.rstrip(".").encode("idna").decode("ascii").lower()
        try:
            ipaddress.ip_address(host)
            is_ip = True
        except ValueError:
            is_ip = False
            labels = host.split(".")
            if len(host) > 253 or any(not label or len(label) > 63 or
                    label.startswith("-") or label.endswith("-") or
                    any(not (c.isascii() and (c.isalnum() or c == "-")) for c in label)
                    for label in labels):
                raise ValueError("Invalid hostname")
        return ParsedURL(url, parts, host, is_ip)
    except (UnicodeError, ValueError) as exc:
        raise ValueError(f"Invalid URL: {exc}") from exc
