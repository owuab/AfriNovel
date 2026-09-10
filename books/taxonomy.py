"""Normalization and controlled classification for Asian catalogue records."""

from __future__ import annotations

import re
import unicodedata

from .models import CatalogBook, CatalogCategory


LANGUAGE_SUBCATEGORY = {
    'zh': 'chinese', 'zh-cn': 'chinese', 'zh-tw': 'chinese', 'cmn': 'chinese',
    'ko': 'korean', 'kor': 'korean',
    'ja': 'japanese', 'jpn': 'japanese',
    'hi': 'south_asian', 'hin': 'south_asian', 'bn': 'south_asian', 'ben': 'south_asian',
    'ur': 'south_asian', 'urd': 'south_asian', 'ta': 'south_asian', 'tam': 'south_asian',
    'te': 'south_asian', 'tel': 'south_asian', 'mr': 'south_asian', 'mar': 'south_asian',
    'ne': 'south_asian', 'nep': 'south_asian',
    'id': 'southeast_asian', 'ind': 'southeast_asian', 'ms': 'southeast_asian', 'msa': 'southeast_asian',
    'vi': 'southeast_asian', 'vie': 'southeast_asian', 'th': 'southeast_asian', 'tha': 'southeast_asian',
    'tl': 'southeast_asian', 'fil': 'southeast_asian',
}

SUBCATEGORY_TERMS = {
    'chinese': ('china', 'chinese', 'mandarin', 'sinitic', 'taiwan', 'hong kong'),
    'korean': ('korea', 'korean', 'hangul', 'joseon'),
    'japanese': ('japan', 'japanese', 'nihon', 'nippon', 'tokyo'),
    'south_asian': ('india', 'indian', 'pakistan', 'pakistani', 'bangladesh', 'nepal', 'sri lanka', 'bengali', 'sanskrit'),
    'southeast_asian': ('vietnam', 'vietnamese', 'indonesia', 'indonesian', 'malaysia', 'malay', 'thailand', 'thai', 'philippines', 'tagalog'),
}


def normalize_text(value: str) -> str:
    value = unicodedata.normalize('NFKC', value or '')
    return re.sub(r'\s+', ' ', value).strip()


def normalize_language(value: str) -> str:
    return normalize_text(value).casefold().replace('_', '-')


def classify_asian_book(book: CatalogBook) -> str | None:
    """Return one controlled subcategory using language first, then subject metadata."""
    for language in book.languages or []:
        subcategory = LANGUAGE_SUBCATEGORY.get(normalize_language(str(language)))
        if subcategory:
            return subcategory
    haystack = normalize_text(' '.join([book.title, *book.authors, *book.subjects])).casefold()
    for subcategory, terms in SUBCATEGORY_TERMS.items():
        if any(term in haystack for term in terms):
            return subcategory
    return None


def assign_asian_category(book: CatalogBook) -> CatalogCategory | None:
    subcategory = classify_asian_book(book)
    if not subcategory:
        return None
    return CatalogCategory.objects.update_or_create(
        book=book,
        category=CatalogCategory.ASIAN,
        subcategory=subcategory,
        defaults={'confidence': 1, 'rule_version': 'asian-v1'},
    )[0]