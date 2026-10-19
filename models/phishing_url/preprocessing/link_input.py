"""User link handling, separate from the frozen web-model parser."""
import re
from urllib.parse import urlsplit
from .url_parser import parse_url

def inspect_input(value):
    if not isinstance(value,str) or not 1<=len(value)<=2048 or any(c.isspace() or ord(c)<32 or ord(c)==127 for c in value) or '\\' in value:
        raise ValueError('Enter a link or domain without spaces or control characters (up to 2048 characters).')
    original=value
    inferred=False
    if value.startswith('//'):
        value='https:'+value;inferred=True
    # A host:port is not a custom URI scheme.
    authority=value.split('/',1)[0].split('?',1)[0].split('#',1)[0]
    host_port=bool(re.match(r'^(?:[^:]+\.[^:]+|localhost):[0-9]+$',authority))
    if not re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:',value) or host_port:
        value='https://'+value;inferred=True
    parts=urlsplit(value)
    if parts.scheme.lower() in {'http','https'}:
        parsed=parse_url(value)
        if inferred and not ('.' in parsed.hostname or parsed.is_ip or parsed.hostname=='localhost'):
            raise ValueError('Enter a domain, IP address or complete link.')
        return {'original':original,'normalized':value,'scheme':parts.scheme.lower(),'kind':'web','inferred_https':inferred,'hostname':parsed.hostname}
    if not parts.scheme or not (parts.netloc or parts.path):raise ValueError('Incomplete link.')
    host=None
    if parts.netloc:
        host=parse_url(parts._replace(scheme='https').geturl()).hostname
    elif parts.scheme.lower()=='mailto':
        address=parts.path
        if address.count('@')!=1 or not address.split('@')[0]:raise ValueError('Enter one valid mailto recipient.')
        host=parse_url('https://'+address.rsplit('@',1)[1]).hostname
    return {'original':original,'normalized':value,'scheme':parts.scheme.lower(),'kind':'non_web','inferred_https':False,'hostname':host}
