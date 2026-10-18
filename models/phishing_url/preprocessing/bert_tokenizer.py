"""BERT serialization shared by training/runtime; no content fetching."""
BERT_MODEL = "google-bert/bert-base-uncased"
BERT_REVISION = "86b5e0934494bd15c9632b12f734a8a67f723594"
BERT_PREPROCESSING = "raw-url-bert-v1"
MAX_LENGTH = 128

def serialize_url(url):
    from .url_parser import parse_url
    parse_url(url)
    return url
