"""Initialize local configuration without replacing user credentials or databases."""
from pathlib import Path
import re
import secrets

root=Path(__file__).resolve().parents[2]
target=root/'.env'
if not target.exists():
    target.write_bytes((root/'.env.example').read_bytes())
text=target.read_text(encoding='utf-8-sig')
match=re.search(r'^JWT_SECRET_KEY=(.*)$',text,re.M)
known={'GENERATE_ON_SETUP','change_this_to_a_secure_random_secret_in_production_32bytes','trustnet_super_secret_jwt_key_for_development_purposes_only'}
if not match or match.group(1).strip() in known:
    line='JWT_SECRET_KEY='+secrets.token_urlsafe(48)
    text=text[:match.start()]+line+text[match.end():] if match else text.rstrip()+'\n'+line+'\n'
    target.write_text(text,encoding='utf-8')
    print('Generated a local JWT secret. Existing custom credentials were preserved.')
else:
    print('Existing custom JWT configuration preserved.')
