"""Identical text-only normalization and routing for training and CPU inference."""
import re
import unicodedata

HINGLISH=re.compile(r'\b(?:aap(?:ka|ki|ko)?|tum(?:hara)?|hai|hain|karo|karna|paisa|paise|bhej\w*|turant|abhi|jayega|nahi|nahin|mat|mera|mujhe)\b',re.I)


def normalize_message(text):
    value=unicodedata.normalize('NFKC',text).casefold()
    value=re.sub(r'https?://\S+|www\.\S+',' link ',value)
    value=re.sub(r'\b\S+@\S+\b',' email ',value)
    value=re.sub(r'\d+',' number ',value)
    return ' '.join(value.split())


def message_language(text):
    if re.search('[\u0900-\u097f]',text):return 'Hindi'
    return 'Hinglish' if len({m.group().casefold() for m in HINGLISH.finditer(text)})>=2 else 'English'
