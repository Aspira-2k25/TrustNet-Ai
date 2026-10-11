"""Input coverage guard; preserves original Unicode and explanation offsets."""
import re


def validate_text(text):
    if not text.strip() or len(text) > 10000 or '\x00' in text:
        raise ValueError('Message must contain 1–10000 characters and no NUL bytes')
    words = re.findall(r'\b(?:aap|apna|hai|karo|paisa|bhejo|turant)\b', text, re.I)
    if len(set(w.lower() for w in words)) >= 2:
        raise ValueError('Possible Hinglish: unsupported language coverage; review manually')
    letters = [c for c in text if c.isalpha()]
    latin = sum('a' <= c.lower() <= 'z' for c in letters) / max(1, len(letters))
    if not letters or latin < .8:
        raise ValueError('Unsupported script/language: trained for English messages only')
