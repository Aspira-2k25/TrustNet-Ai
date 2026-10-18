"""Frozen offline message/URL comparison; never trains or changes thresholds.

Raw data and substantial row output must stay outside the application repository.
Input: JSON list of text/label rows and its provenance manifest with frozen_sha256.
Phishing/Spam/Valid map to the source's fraud/spam/ham labels; spam is not relabelled
as fraud. Metrics describe review alerts and report missing URL coverage explicitly.
"""
import argparse
import asyncio
import copy
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def normalized(text):
    return re.sub(r'\s+', ' ', text).strip().casefold()


def metrics(rows, name):
    eligible = [row for row in rows if row.get(name) is not None]
    tp = sum(row['positive'] and row[name] for row in eligible)
    tn = sum(not row['positive'] and not row[name] for row in eligible)
    fp = sum(not row['positive'] and row[name] for row in eligible)
    fn = sum(row['positive'] and not row[name] for row in eligible)
    precision = tp / (tp + fp) if tp + fp else 0
    recall = tp / (tp + fn) if tp + fn else 0
    return dict(n=len(eligible), total=len(rows), coverage=len(eligible)/len(rows) if rows else 0,
                confusion_matrix={'tn':tn, 'fp':fp, 'fn':fn, 'tp':tp},
                accuracy=(tp+tn)/len(eligible) if eligible else None,
                precision=precision, recall=recall, f1=2*precision*recall/(precision+recall) if precision+recall else 0,
                false_positive_rate=fp/(fp+tn) if fp+tn else None)


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--training-csv', type=Path, action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--url-service', default='http://127.0.0.1:8007')
    args = parser.parse_args()
    output = args.output.resolve()
    if output.is_relative_to(ROOT):
        raise SystemExit('Keep row-level evaluation output outside the main repository.')
    provenance = json.loads(args.manifest.read_text(encoding='utf-8'))
    digest = hashlib.sha256(args.data.read_bytes()).hexdigest()
    if digest != provenance['frozen_sha256']:
        raise SystemExit('Dataset differs from its frozen provenance manifest.')
    data = json.loads(args.data.read_text(encoding='utf-8'))
    training_texts = set()
    training_groups = set()
    training_checksums = {}
    for path in args.training_csv:
        training_checksums[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        with path.open(encoding='utf-8-sig', newline='') as stream:
            for row in csv.DictReader(stream):
                training_texts.add(normalized(row['text']))
                if row.get('group'): training_groups.add(row['group'])
    output.mkdir(parents=True, exist_ok=True)
    report_path = output/'summary.json'
    if report_path.exists(): raise SystemExit('This evaluation is already complete; choose a new output folder explicitly.')
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    import torch
    torch.set_num_threads(2)
    import httpx
    from models.scam_message.detector import ScamDetector
    from models.scam_message.presentation import enrich
    from services.scam_message.app.link_fusion import extract_urls, assess_links, combine
    from shared.schemas.detection_result import DetectionResult
    from shared.schemas.message_input import MessageInput
    detector = ScamDetector()
    with httpx.Client(timeout=10) as client: client.get(args.url_service.rstrip('/')+'/ready').raise_for_status()
    rows, exclusions = [], []
    seen = set()
    for index, row in enumerate(data):
        text = row['text']; text_hash = hashlib.sha256(text.encode()).hexdigest()
        reason = None
        if normalized(text) in training_texts or row.get('group') in training_groups:
            reason = 'Exact normalized text or recorded group overlaps supplied training data'
        elif normalized(text) in seen: reason = 'Duplicate normalized evaluation text'
        elif row['label'] not in ('Phishing', 'Spam', 'Valid'): reason = 'Unsupported source label'
        seen.add(normalized(text))
        try:
            request = MessageInput(text=text, message_type='email')
            detector.semantic.validate(request.canonical_text())
        except ValueError as exc:
            reason = 'Runtime input rejected: ' + str(exc)
        if reason:
            exclusions.append({'index':index, 'text_sha256':text_hash, 'label':row['label'], 'reason':reason})
            continue
        # The same deployed probability path, with no expensive masked explanations.
        p, windows = detector.semantic.probabilities(request.canonical_text())
        message = DetectionResult(scan_id=f'evaluation-{index}', module='scam_message',
            detector_id=detector.manifest['detector_id'], model_version=detector.manifest['model_version'],
            preprocessing_version=detector.manifest['preprocessing_version'], native_score=float(p[1]),
            native_score_semantics='probability_of_positive_class', risk_score=float(p[1])*100,
            confidence=float(max(p)), label=detector.semantic.config['labels'][int(p.argmax())],
            status='SUCCESS', timestamp=datetime.now(timezone.utc).isoformat(),
            metadata={'threshold':detector.semantic.config['threshold'], 'coverage':{'windows':windows},
                      'limitations':[], 'evaluated_domains':detector.manifest['evaluated_domains']})
        message = enrich(message, request)
        if not rows:
            actual = enrich(detector.predict(request.canonical_text(), message.scan_id), request)
            assert abs(actual.risk_score-message.risk_score) < 1e-6 and actual.verdict == message.verdict
        urls = extract_urls(request)
        links = await assess_links(urls, message.scan_id, args.url_service) if urls else []
        fused = combine(copy.deepcopy(message), links)
        available = [link for link in links if link.get('risk_score') is not None]
        alerts = {'LIKELY_SCAM', 'SUSPICIOUS'}
        rows.append(dict(index=index, text_sha256=text_hash, source_label=row['label'],
            positive=row['label']=='Phishing', origin=row.get('origin'),
            message_alert=None if message.verdict=='UNABLE_TO_ASSESS' else message.verdict in alerts,
            url_alert=None if not available else any(link.get('label')=='phishing' or link.get('verdict')=='REVIEW_RECOMMENDED' for link in available),
            fusion_alert=None if fused.verdict=='UNABLE_TO_ASSESS' else fused.verdict in alerts,
            message_score=message.risk_score, fusion_score=fused.risk_score,
            urls_found=len(urls), urls_assessed=len(available),
            incomplete_links=len(available)<len(urls)))
        with (output/'predictions.jsonl').open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(rows[-1])+'\n')
        if (index+1)%25 == 0: print(f'Evaluated {index+1}/{len(data)} frozen records', flush=True)
    common = [row for row in rows if all(row[name] is not None for name in ('message_alert','url_alert','fusion_alert'))]
    report = dict(dataset_sha256=digest, provenance=provenance, training_checksums=training_checksums,
        message_model=detector.manifest['model_version'], input_rows=len(data), assessed_rows=len(rows), excluded_rows=len(exclusions),
        urls_present_rows=sum(row['urls_found']>0 for row in rows), incomplete_link_rows=sum(row['incomplete_links'] for row in rows),
        policy='Review alert: LIKELY_SCAM or SUSPICIOUS. UNABLE_TO_ASSESS is an abstention. URL-only without an assessed link abstains.',
        all_assessed={name:metrics(rows,name) for name in ('message_alert','url_alert','fusion_alert')},
        common_url_subset={name:metrics(common,name) for name in ('message_alert','url_alert','fusion_alert')},
        limitations=['Previously inspected, source-held-out curated collection, not a new untouched prospective test.',
            'Human and LLM-origin examples have uncertain upstream real-world provenance; results do not establish modern inbox accuracy.',
            'Source Spam is treated as non-phishing for this binary comparison, not declared safe.',
            'Training overlap audit covers the supplied training files, not every unknown upstream source.',
            'Offline URL checks only. Website inspection is separate and is not evaluated here.',
            'No training, threshold selection, model promotion or probability calibration was performed.'])
    report_path.write_text(json.dumps(report,indent=2),encoding='utf-8')
    (output/'exclusions.json').write_text(json.dumps(exclusions,indent=2),encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('input_rows','assessed_rows','excluded_rows','urls_present_rows','all_assessed','common_url_subset')},indent=2))


if __name__ == '__main__': asyncio.run(main())
