"""Inspect submitted paths and observed redirects without crawling page links."""
import re
from urllib.parse import unquote, parse_qsl, urlsplit

def inspect_path(url):
    p=urlsplit(url)
    decoded=unquote(p.path)
    twice=unquote(decoded)
    traversal=any(part in {'.','..'} for part in re.split(r'[/\\]',twice))
    targets=[]
    for name,value in parse_qsl(p.query,keep_blank_values=True)[:100]:
        if name.lower() not in {'url','redirect','redirect_uri','redirect_url','next','continue','return','returnto','return_url','destination','goto'}:continue
        try:
            target=urlsplit(unquote(value))
            if target.scheme in {'http','https'} and target.hostname:
                targets.append({'parameter':name,'hostname':target.hostname,'scheme':target.scheme,
                                'external_hostname':target.hostname.lower()!=(p.hostname or '').lower()})
        except ValueError:continue
    return {'path':p.path or '/','segments':len([part for part in p.path.split('/') if part]),
            'encoded_separators':bool(re.search(r'%(?:2f|5c)',p.path,re.I)),
            'double_encoding':decoded!=twice,'dot_segments':traversal,'navigation_parameters':targets[:20],
            'definition':'Path/query syntax is inspected locally. Parameter targets are not fetched and do not prove an open redirect.'}
