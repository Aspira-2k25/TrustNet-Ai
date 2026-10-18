"""Inspect submitted paths and observed redirects without crawling page links."""
import re
from urllib.parse import unquote, parse_qsl, urlsplit
from models.phishing_url.preprocessing.url_parser import parse_url

def inspect_path(url):
    p=urlsplit(url)
    decoded=unquote(p.path)
    twice=unquote(decoded)
    traversal=any(part in {'.','..'} for part in re.split(r'[/\\]',twice))
    targets=[]
    for name,value in parse_qsl(p.query,keep_blank_values=True)[:100]:
        navigation_name=name.lower() in {'url','redirect','redirect_uri','redirect_url','next','continue','return','returnto','return_url','destination','goto','target','target_url','dn','domain','host','hostname'}
        try:
            value=unquote(value)
            target=urlsplit(value)
            inferred=False
            if navigation_name and not target.scheme and not target.netloc and '.' in value and not any(c in value for c in '/?#@ \\'):
                target=urlsplit('https://'+value)
                inferred=True
            elif navigation_name and value.startswith('//'):
                target=urlsplit(p.scheme+':'+value)
                inferred=True
            if target.scheme in {'http','https'} and target.hostname:
                parsed=parse_url(target.geturl())
                if parsed.parts.username is not None:continue
                targets.append({'parameter':name,'hostname':parsed.hostname,'scheme':None if inferred else target.scheme,
                                'inferred_destination':inferred,'navigation_parameter_name':navigation_name,
                                'external_hostname':parsed.hostname!=(p.hostname or '').lower()})
        except ValueError:continue
    return {'path':p.path or '/','segments':len([part for part in p.path.split('/') if part]),
            'encoded_separators':bool(re.search(r'%(?:2f|5c)',p.path,re.I)),
            'double_encoding':decoded!=twice,'dot_segments':traversal,'navigation_parameters':targets[:20],
            'definition':'Path/query syntax is inspected locally. Parameter targets are not fetched and do not prove an open redirect. Bare-hostname targets have no observed transport scheme.'}
