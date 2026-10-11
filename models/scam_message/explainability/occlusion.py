"""Bounded signed sensitivity measured through the complete deployed predictor."""
import time


def measure_spans(predictor, text, score, candidates, budget_seconds, estimated_call_seconds=0):
    started = time.perf_counter()
    spans, evidence = [], []
    for start, end in candidates:
        if time.perf_counter() - started + estimated_call_seconds >= budget_seconds:
            break
        masked = text[:start] + '[MASK]' + text[end:]
        probabilities, _ = predictor(masked)
        delta = score - float(probabilities[1])
        feature = text[start:end]
        spans.append({'start': start, 'end': end, 'kind': 'model',
                      'note': feature.lower(), 'contribution': delta,
                      'direction': 'support' if delta > 0 else 'counterevidence'})
        evidence.append({'feature_or_region': feature, 'contribution': delta,
                         'human_readable_note': 'Original smishing probability minus probability after masking this span; partial sensitivity, not causal proof'})
    return spans, evidence, len(evidence) < len(candidates), time.perf_counter() - started
