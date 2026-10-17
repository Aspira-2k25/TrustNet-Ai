"""Plain-language observed reasons; no website reputation or ownership claims."""
from models.phishing_url.preprocessing.url_parser import parse_url

def explain_url(url, evidence, flagged):
    parsed=parse_url(url)
    reasons=[]
    if parsed.parts.username is not None:
        reasons.append(f'Text before @ can look like a trusted website, but the actual destination hostname is {parsed.hostname}.')
    if parsed.is_ip:
        reasons.append('The destination uses a numeric IP address rather than a named website. This needs extra checking, but is not proof of phishing.')
    if 'xn--' in parsed.hostname:
        reasons.append('The hostname contains an internationalised domain representation; check the exact spelling for lookalike characters.')
    if not flagged and not parsed.is_ip and parsed.parts.username is None:
        reasons.append(f'The destination hostname is {parsed.hostname}; the address does not contain a numeric IP destination or an embedded @ login section.')
    names={'url_length':'The overall address length','host_length':'The hostname length','path_length':'The page-path length','query_length':'The amount of query text','sensitive_tokens':'Account or payment-related words in the address','host_labels':'The hostname structure','digits':'Digits in the address','hyphens':'Hyphens in the address','percent_signs':'Encoded characters in the address','has_userinfo':'The user-information section','is_ip':'The numeric destination address','is_idn':'The internationalised hostname','explicit_port':'The explicit network port'}
    supported=[e for e in evidence if (e.contribution>0 if flagged else e.contribution<0) and e.feature_or_region in names]
    for e in sorted(supported,key=lambda e:abs(e.contribution),reverse=True)[:2]:
        reasons.append(f"{names[e.feature_or_region]} {'increased' if e.contribution>0 else 'reduced'} the lexical model's risk estimate.")
    text=[e for e in evidence if e.feature_or_region.startswith('URL text: ') and (e.contribution>0 if flagged else e.contribution<0)]
    if text:
        fragments=', '.join(repr(e.feature_or_region.removeprefix('URL text: ')) for e in text[:2])
        reasons.append(f"Text patterns {fragments} {'raised' if flagged else 'lowered'} the model's estimate, based on the examples it learned. This is a pattern match, not a website verification.")
    if not reasons:
        reasons.append('The decision comes from the learned URL pattern; there is no separately verified website-content reason.')
    reasons.append('The website itself was not opened or verified, so this result cannot guarantee safety or prove fraud.')
    return reasons
