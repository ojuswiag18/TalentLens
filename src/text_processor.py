"""Text preprocessing utilities: cleaning, tokenization, normalization,
stopword removal and keyword extraction."""

import re
from collections import Counter

STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "because", "as", "until",
    "while", "of", "at", "by", "for", "with", "about", "against", "between",
    "into", "through", "during", "before", "after", "above", "below", "to",
    "from", "up", "down", "in", "out", "on", "off", "over", "under", "again",
    "further", "then", "once", "here", "there", "when", "where", "why", "how",
    "all", "any", "both", "each", "few", "more", "most", "other", "some",
    "such", "no", "nor", "not", "only", "own", "same", "so", "than", "too",
    "very", "s", "t", "can", "will", "just", "don", "should", "now", "am",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "having", "do", "does", "did", "doing", "would", "could", "should",
    "may", "might", "must", "shall", "i", "you", "he", "she", "it", "we",
    "they", "them", "their", "his", "her", "its", "our", "your", "my", "me",
    "us", "him", "also", "well", "use", "used", "using", "job", "role",
    "position", "team", "company", "work", "working", "etc", "e.g", "i.e",
    "one", "two", "new", "good", "great", "per", "senior", "junior",
    "candidate", "candidates", "candidate's", "skill", "skills", "must",
    "required", "requirements", "require", "requires", "including", "etc",
    "including", "within", "across", "via", "please", "apply", "ability",
    "able", "strong", "solid", "familiar", "experience", "years", "year",
    "years'", "minimum", "preferred", "nice", "plus", "bonus", "ideally",
    "looking", "help", "support", "responsibilities", "responsibility",
    "qualifications", "qualification", "should", "shall", "may", "might",
}

_TOKEN_PATTERN = re.compile(r"[a-zA-Z][a-zA-Z0-9+#-]*")


def clean_text(text):
    """Remove URLs, emails and other noise while preserving meaningful words."""
    if not text:
        return ""
    text = re.sub(r"http\S+|www\.\S+", " ", text)
    text = re.sub(r"\S+@\S+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize(text):
    """Lowercase, strip punctuation to spaces and collapse whitespace."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^a-z0-9+.#\s-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def tokenize(text):
    """Return lowercase alphanumeric tokens from text."""
    if not text:
        return []
    return _TOKEN_PATTERN.findall(text.lower())


def remove_stopwords(tokens):
    """Filter out stopwords from a token list."""
    return [t for t in tokens if t not in STOPWORDS and len(t) > 1]


def extract_keywords(text, top_n=30):
    """Extract the most frequent non-stopword tokens as candidate keywords."""
    tokens = remove_stopwords(tokenize(text))
    counts = Counter(tokens)
    return [w for w, _ in counts.most_common(top_n)]


_SENTENCE_PATTERN = re.compile(r"[^.!?]+[.!?]*")


def sentence_around(text, position):
    """Return the lowercase sentence containing a character position."""
    for m in _SENTENCE_PATTERN.finditer(text):
        if m.start() <= position < m.end():
            return m.group(0).lower()
    return text.lower()


def window_around(text, position, radius=40):
    """Return a lowercase slice of text around a character position."""
    start = max(0, position - radius)
    end = min(len(text), position + radius)
    return text[start:end].lower()