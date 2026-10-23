"""Only the configured binary label contract can produce an applied score."""
import math

def parse_binary_predictions(predictions):
    if not isinstance(predictions, list):
        raise ValueError('Classifier must return the full real/fake distribution')
    values = {}
    for prediction in predictions:
        label = str(prediction.get('label', '')).strip().lower()
        if label not in {'real', 'fake'} or label in values:
            raise ValueError('Unknown or duplicate classifier label')
        score = prediction.get('score')
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score) or not 0 <= score <= 1:
            raise ValueError('Invalid classifier probability')
        values[label] = score
    if set(values) != {'real', 'fake'} or abs(sum(values.values()) - 1) > .01:
        raise ValueError('Incomplete or unnormalized classifier distribution')
    return round(values['fake'] * 100, 2)
