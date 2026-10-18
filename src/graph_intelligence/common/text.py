"""Deterministic text normalization, stemming, squashing, and tokenization utilities."""

import re
from typing import List, Set

# Built-in stop words list (~120 common English words)
STOP_WORDS: Set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
    "aren't", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both",
    "but", "by", "can", "cannot", "could", "did", "didn't", "do", "does", "doesn't", "doing",
    "don't", "down", "during", "each", "few", "for", "from", "further", "had", "hadn't", "has",
    "hasn't", "have", "haven't", "having", "he", "her", "here", "hers", "herself", "him", "himself",
    "his", "how", "i", "im", "if", "in", "into", "is", "isn't", "it", "its", "itself", "let's",
    "me", "more", "most", "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only",
    "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "ready", "same",
    "she", "should", "shouldn't", "so", "some", "such", "than", "that", "the", "their", "theirs",
    "them", "themselves", "then", "there", "these", "they", "this", "those", "through", "to",
    "too", "under", "until", "up", "very", "was", "wasn't", "we", "were", "weren't", "what",
    "when", "where", "which", "while", "who", "whom", "why", "will", "with", "won't", "would",
    "wouldn't", "you", "your", "yours", "yourself", "yourselves"
}

GENERIC_KEYWORD_FILLER: Set[str] = {
    "thing", "things", "stuff", "item", "items", "general", "etc", "test", "testing",
    "note", "notes", "misc", "information", "info", "overview"
}


def _stem_token(token: str) -> str:
    """Light stemming per token: ies -> y, trailing s removed if len > 3 and not ss."""
    if token.endswith("ies") and len(token) > 4:
        return token[:-3] + "y"
    if token.endswith("s") and not token.endswith("ss") and len(token) > 3:
        return token[:-1]
    return token


def normalize_term(s: str) -> str:
    """
    Lowercase, strip, strip possessive 's, replace _/punctuation with space
    (treat hyphen inside words as space too), collapse spaces, and apply light stemming per token.
    """
    if not s:
        return ""
    text = s.lower().strip()
    # Strip possessives like 's or ’s
    text = re.sub(r"['’]s\b", "", text)
    # Replace non-alphanumeric chars (including _, -, punctuation) with spaces
    text = re.sub(r"[^a-z0-9]+", " ", text)
    tokens = text.split()
    stemmed = [_stem_token(t) for t in tokens]
    return " ".join(stemmed)


def squash(s: str) -> str:
    """Lowercase alphanumerics only (e.g., 'Payment Service' -> 'paymentservice')."""
    if not s:
        return ""
    return re.sub(r"[^a-z0-9]", "", s.lower())


def tokenize(s: str) -> List[str]:
    """
    Extract normalized tokens minus stop words, minimum length 2.
    """
    if not s:
        return []
    normalized = normalize_term(s)
    tokens = normalized.split()
    return [t for t in tokens if len(t) >= 2 and t not in STOP_WORDS]


def extract_keywords(terms: List[str]) -> List[str]:
    """
    Normalize, deduplicate, drop generic filler and stop words, cap to 20 keywords.
    """
    seen = set()
    result: List[str] = []
    for term in terms:
        norm = normalize_term(term)
        if not norm:
            continue
        # Check against stop words and generic filler
        tokens = [t for t in norm.split() if t not in STOP_WORDS and t not in GENERIC_KEYWORD_FILLER]
        cleaned_term = " ".join(tokens)
        if cleaned_term and cleaned_term not in seen and len(cleaned_term) >= 2:
            seen.add(cleaned_term)
            result.append(cleaned_term)
        if len(result) >= 20:
            break
    return result
