"""Build a versioned visual-domain reference, never a safe-domain allowlist."""
import csv,hashlib,itertools,json,os
from datetime import datetime,timezone
from pathlib import Path
import httpx

root=Path(__file__).resolve().parents[1]/'models/phishing_url/configs'
rank_url='https://downloads.majestic.com/majestic_million.csv'
unicode_url='https://www.unicode.org/Public/security/latest/confusables.txt'
with httpx.Client(timeout=30,follow_redirects=True) as client:
    with client.stream('GET',rank_url) as response:
        response.raise_for_status()
        lines=list(itertools.islice(response.iter_lines(),10001))
    records=list(csv.DictReader(lines))
    assert len(records)==10000 and 'Domain' in records[0]
    response=client.get(unicode_url);response.raise_for_status();unicode_data=response.text
    response=client.get('https://www.unicode.org/license.txt');response.raise_for_status();unicode_license=response.text
mapping={}
for line in unicode_data.splitlines():
    body=line.split('#',1)[0].strip()
    if not body:continue
    source,target,*_=body.split(';')
    source=source.strip().split()
    if len(source)==1:mapping[chr(int(source[0],16))]=''.join(chr(int(c,16)) for c in target.split())
assert len(mapping)>1000
value={'version':'visual-domain-reference-v1','retrieved_at':datetime.now(timezone.utc).isoformat(),
       'ranking_source':rank_url,'ranking_attribution':'Majestic Million, Majestic, CC BY 3.0, https://majestic.com/reports/majestic-million',
       'ranking_prefix_sha256':hashlib.sha256('\n'.join(lines).encode()).hexdigest(),
       'confusables_source':unicode_url,'confusables_sha256':hashlib.sha256(unicode_data.encode()).hexdigest(),
       'confusables_attribution':'Unicode Consortium confusables data; Unicode License v3: https://www.unicode.org/license.txt',
       'definition':'Popular-domain similarity references only. Inclusion is not proof of ownership or safety; no phishing labels are supplied.',
       'domains':{r['Domain'].lower():int(r['GlobalRank']) for r in records},'confusables':mapping}
temporary=root/'domain_reference.pending.json'
temporary.write_text(json.dumps(value,ensure_ascii=True,sort_keys=True),encoding='utf-8')
os.replace(temporary,root/'domain_reference.json')
(root/'domain_reference_LICENSE.txt').write_text('Ranking source: Majestic Million, Majestic, https://majestic.com/reports/majestic-million\nLicense: Creative Commons Attribution 3.0 Unported, https://creativecommons.org/licenses/by/3.0/\nThis derivative retains the first 10,000 ranked domains for visual similarity, not safety decisions.\n\nUnicode confusables data is redistributed as a character map. Full Unicode license follows:\n\n'+unicode_license,encoding='utf-8')
print(json.dumps({'domains':len(value['domains']),'confusables':len(mapping),'retrieved_at':value['retrieved_at']}))
