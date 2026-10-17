"""Scheme-neutral URL structure, shared verbatim by v3 training and inference.

No domain names, brand lists, reputation labels or live observations are inputs.
"""
import math
import re
from collections import Counter
from urllib.parse import unquote, parse_qsl
from .url_parser import parse_url

VERSION = 'url-structural-v3'
NAMES = ('length', 'host_length', 'path_length', 'query_length', 'host_labels',
         'host_digits', 'host_digit_ratio', 'host_hyphens', 'host_entropy',
         'max_label_length', 'mean_label_length', 'path_segments', 'path_digits',
         'path_entropy', 'query_parameters', 'percent_count', 'encoded_fraction',
         'userinfo', 'ip_destination', 'internationalised', 'unusual_port',
         'dots_in_path', 'slashes', 'equals', 'at_signs', 'double_slash_path',
         'fragment_length', 'credential_terms', 'longest_digit_run', 'suffix_length')

def entropy(text):
    return -sum((n / len(text)) * math.log2(n / len(text)) for n in Counter(text).values()) if text else 0.

def extract(url):
    p = parse_url(url)
    host, path, query = p.hostname, p.parts.path or '/', p.parts.query
    text = p.parts.netloc + path + ('?' + query if query else '') + ('#' + p.parts.fragment if p.parts.fragment else '')
    labels = host.split('.')
    digits = sum(c.isdigit() for c in host)
    terms = re.findall(r'[a-z]+', unquote(path + '?' + query).lower())
    values = (len(text), len(host), len(path), len(query), len(labels), digits,
              digits / max(1, len(host)), host.count('-'), entropy(host),
              max(map(len, labels)), sum(map(len, labels)) / len(labels),
              len([v for v in path.split('/') if v]), sum(c.isdigit() for c in path),
              entropy(path), len(parse_qsl(query, keep_blank_values=True)), text.count('%'),
              max(0, len(text) - len(unquote(text))) / max(1, len(text)),
              int(p.parts.username is not None), int(p.is_ip), int('xn--' in host),
              int(p.parts.port is not None and p.parts.port not in (80, 443)),
              path.count('.'), path.count('/'), text.count('='), text.count('@'),
              int('//' in path), len(p.parts.fragment),
              sum(t in {'login', 'verify', 'password', 'account', 'signin', 'payment', 'otp'} for t in terms),
              max((len(v) for v in re.findall(r'\d+', text)), default=0), len(labels[-1]))
    return dict(zip(NAMES, map(float, values)))
