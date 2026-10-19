"""Phishing presentation routes all valid inputs through the current policy."""
def present(result, url, threshold):
    if result.error_code == 'INVALID_URL' or not url:
        result.verdict = 'UNABLE_TO_ASSESS'
        result.metadata['display_verdict'] = 'Check incomplete'
        result.explanation = result.error_message or 'Enter a valid HTTP or HTTPS URL.'
        result.metadata['reasons'] = [result.explanation]
        return result
    from .forensics import apply_policy
    return apply_policy(result, url, threshold)
