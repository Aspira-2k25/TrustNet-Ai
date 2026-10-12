"""Local structural features of literal URLs; no network or reputation claims."""
import ipaddress
import re
from urllib.parse import urlsplit
import numpy as np

FEATURE_NAMES = ['url_count', 'max_url_length', 'max_host_length', 'max_host_digits',
                 'max_host_hyphens', 'max_host_dots', 'ip_literal_count',
                 'userinfo_count', 'punycode_count', 'max_path_depth',
                 'max_query_length', 'http_count', 'https_count', 'placeholder_count']


def structural_features(text):
    values = np.zeros(len(FEATURE_NAMES), dtype=float)
    values[13] = len(re.findall(r'<URL>|\[URL\]', text, re.I))
    urls = re.findall(r'https?://[^\s<>"\']+|www\.[^\s<>"\']+', text, re.I)[:50]
    values[0] = len(urls)
    for original in urls:
        url = original.rstrip('.,);]')[:2048]
        try:
            parsed = urlsplit(url if '://' in url else 'https://' + url)
            host = parsed.hostname or ''
        except ValueError:
            continue
        values[1:6] = np.maximum(values[1:6],
            [len(url), len(host), sum(c.isdigit() for c in host), host.count('-'), host.count('.')])
        try:
            ipaddress.ip_address(host)
            values[6] += 1
        except ValueError:
            pass
        values[7] += parsed.username is not None
        values[8] += 'xn--' in host
        values[9] = max(values[9], len([part for part in parsed.path.split('/') if part]))
        values[10] = max(values[10], len(parsed.query))
        values[11] += parsed.scheme.lower() == 'http'
        values[12] += parsed.scheme.lower() == 'https'
    # Log compression is fixed, stateless preprocessing. Any scaling or model
    # coefficients must be learned using the training partition only.
    return np.log1p(values)


def feature_matrix(texts):
    return np.vstack([structural_features(text) for text in texts])
