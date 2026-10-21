"""Bounded offline URL assessment and transparent, conservative late fusion.

The message model and its calibrated probabilities are never retrained or changed.
The combined risk is an uncalibrated maximum evidence index, not a probability.
"""
import asyncio
import re
import time
from html.parser import HTMLParser
import httpx
from shared.schemas.detection_result import DetectionResult

POLICY = 'message-url-max-v1'
MAX_LINKS = 8
URL_PATTERN = re.compile(r'(?i)\b(?:https?://[^\s<>"\']+|www\.[^\s<>"\']+|(?:[a-z0-9](?:[a-z0-9-]{0,62})\.)+(?:com|org|net|in|co|io|xyz|top|online|site|info|gov|edu)(?:/[^\s<>"\']*)?)(?![\w@])')

class Anchors(HTMLParser):
    def __init__(self):
        super().__init__(); self.urls = []
    def handle_starttag(self, tag, attrs):
        if tag.lower() == 'a':
            self.urls.extend(v for k, v in attrs if k == 'href' and v)

def is_web_candidate(url: str) -> bool:
    val = url.strip()
    if not val:
        return False
    lower = val.lower()
    if lower.startswith(('mailto:', 'tel:', 'javascript:', 'sms:', 'data:', '#')):
        return False
    return bool(lower.startswith(('http://', 'https://', 'www.')) or re.match(r'^[a-z0-9][a-z0-9.-]+\.[a-z]{2,}(?:/|$)', lower))

def extract_urls(request):
    candidates = [link.href for link in request.displayed_links]
    if request.text_format == 'html':
        parser = Anchors(); parser.feed(request.text)
        candidates.extend(parser.urls)
    text = request.canonical_text()
    for match in URL_PATTERN.finditer(text):
        # Exclude the domain of an email address without removing complete
        # URLs that use a deceptive user-info section before @.
        if match.start() > 0 and text[match.start() - 1] == '@':
            continue
        candidates.append(match.group())
    seen, urls = set(), []
    for value in candidates:
        value = value.strip().rstrip('.,;!?)]}')
        if value and is_web_candidate(value) and value not in seen:
            seen.add(value); urls.append(value)
    return urls

async def assess_links(urls, scan_id, service_url, deadline=6.0):
    semaphore = asyncio.Semaphore(2)
    results = [dict(url=url, status='UNAVAILABLE', reason='URL assessment limit reached; not analysed') for url in urls]
    async with httpx.AsyncClient(timeout=3.0, trust_env=False) as client:
        async def one(index):
            url = urls[index]
            if len(url) > 2048:
                results[index]['reason'] = 'URL exceeds supported length'; return
            expected = f'{scan_id}:url:{index}'
            try:
                async with semaphore:
                    response = await client.post(service_url.rstrip('/') + '/infer', json={'scan_id':expected, 'url':url})
                    response.raise_for_status()
                    result = DetectionResult.model_validate(response.json()['data'])
                if result.scan_id != expected or result.module.value != 'phishing':
                    raise ValueError('Mismatched URL result')
                available = result.status.value in ('SUCCESS', 'PARTIAL_SUCCESS')
                results[index] = dict(url=url, status=result.status.value,
                    risk_score=result.risk_score if available else None,
                    verdict=result.verdict, label=result.label,
                    reason=result.explanation or result.error_message,
                    model_version=result.model_version,
                    assessment_policy=result.metadata.get('assessment_policy'),
                    coverage=result.metadata.get('coverage'),
                    reasons=result.metadata.get('reasons', []),
                    presentation=result.model_dump(mode='json')['presentation'],
                    mode='offline_model_and_link_checks; destination not opened')
            except (httpx.HTTPError, ValueError, KeyError, TypeError):
                results[index]['reason'] = 'Phishing service unavailable, timed out, busy or returned an invalid result'
        tasks = [asyncio.create_task(one(i)) for i in range(min(len(urls), MAX_LINKS))]
        try:
            await asyncio.wait_for(asyncio.gather(*tasks), timeout=deadline)
        except asyncio.TimeoutError:
            for i in range(min(len(urls), MAX_LINKS)):
                if results[i]['reason'] == 'URL assessment limit reached; not analysed':
                    results[i]['reason'] = 'Total URL assessment deadline exceeded'
        finally:
            for task in tasks:
                if not task.done(): task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
    return results

def combine(result, links):
    meta = result.metadata
    text_score, text_verdict = result.risk_score, result.verdict
    assessed = [link for link in links if link.get('risk_score') is not None]
    url_score = max((link['risk_score'] for link in assessed), default=None)
    incomplete = len(assessed) < len(links)
    flagged = any(link.get('label') == 'phishing' for link in assessed)
    review = any(link.get('verdict') == 'REVIEW_RECOMMENDED' for link in assessed)
    has_failed_check = any(l.get('status') == 'UNAVAILABLE' and l.get('reason') != 'URL assessment limit reached; not analysed' for l in links[:MAX_LINKS])
    no_links_assessed = len(assessed) == 0 and len(links) > 0
    needs_attention = review or incomplete or no_links_assessed or has_failed_check
    combined = max(text_score, url_score if url_score is not None else text_score)
    meta['message_model'] = dict(risk_score=meta.get('model_risk_score',text_score),
                                verdict=meta.get('model_verdict',text_verdict),
                                confidence=meta.get('model_confidence',result.confidence),
                                model_version=result.model_version, confidence_definition=meta.get('confidence_definition'))
    meta['links'] = links
    meta['fusion'] = dict(policy=POLICY, message_score=text_score, url_score=url_score,
        combined_score=combined, calibrated=False, links_found=len(links), links_assessed=len(assessed),
        status='NO_LINKS' if not links else 'PARTIAL' if incomplete else 'ASSESSED',
        definition='Maximum of message-branch warnings and assessed URL risk indices. A conservative warning index, not a calibrated fraud probability. Missing URL results never count as safe.',
        message_verdict=text_verdict)
    result.risk_score = combined
    if flagged:
        result.verdict = 'LIKELY_SCAM'
        meta['display_verdict'] = 'Phishing risk detected in an embedded link'
    elif needs_attention and text_verdict == 'NO_STRONG_INDICATORS':
        result.verdict = 'SUSPICIOUS'
        meta['display_verdict'] = 'Review recommended — embedded link checks need attention'
    if flagged or review:
        result.explanation = (result.explanation or '') + ' Embedded URL analysis also found a phishing risk or details requiring review.'
    meta['assessment_dimensions']['embedded_urls'] = dict(status=meta['fusion']['status'], score=url_score,
        found=len(links), assessed=len(assessed), definition='Offline URL model and link checks; websites are not opened during a message scan')
    if flagged:
        meta['assessment_dimensions']['message_category'] = dict(value='phishing/fraud', status='COMBINED_RISK',
            reason='An embedded link triggered phishing checks; this does not change the message model class probabilities.')
    result.analyzers = [a for a in result.analyzers if a.get('name') != 'Embedded URL analysis']
    result.analyzers.append(dict(name='Embedded URL analysis', category='links',
        status='SKIPPED' if not links else 'UNAVAILABLE' if not assessed else 'PARTIAL' if incomplete else 'APPLIED',
        finding=f'{len(assessed)} of {len(links)} unique links assessed; destinations not opened'))
    if links:
        result.confidence = 0
        meta['confidence_available'] = False
        meta['confidence_definition'] = 'Combined warning confidence is unavailable. Message-model confidence is recorded separately; fusion has not been calibrated.'
        meta['limitations'].append('Limited collection comparisons do not establish modern inbox accuracy or calibrate the combined warning as a probability. Message-class probabilities and confidence describe the message model only.')
    return result

async def fuse_links(result, request, service_url):
    started = time.monotonic()
    urls = extract_urls(request)
    links = await assess_links(urls, result.scan_id, service_url) if urls else []
    result = combine(result, links)
    result.processing_time_ms += round((time.monotonic() - started) * 1000)
    return result
