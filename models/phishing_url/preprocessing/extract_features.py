"""Fixed lexical schema shared by training and inference; no invented metadata."""
from .url_parser import parse_url

FEATURE_NAMES = ("url_length", "host_length", "path_length", "query_length",
                 "host_labels", "digits", "hyphens", "percent_signs", "has_userinfo",
                 "is_ip", "is_idn", "https", "explicit_port", "sensitive_tokens")

def extract_features(url: str) -> dict[str, float]:
    parsed = parse_url(url)
    parts, host = parsed.parts, parsed.hostname
    lower = url.lower()
    values = (len(url), len(host), len(parts.path), len(parts.query), len(host.split(".")),
              sum(c.isdigit() for c in url), url.count("-"), url.count("%"),
              int(parts.username is not None), int(parsed.is_ip), int("xn--" in host),
              int(parts.scheme.lower() == "https"), int(parts.port is not None),
              sum(token in lower for token in ("login", "verify", "password", "account", "secure", "update")))
    return dict(zip(FEATURE_NAMES, map(float, values)))
