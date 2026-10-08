"""
Query normalization for catalogue search.

Shoppers do not type the words the catalogue uses. They write "grey" when the
descriptions say "gray", "jumper" for a sweater, "hoodei" when they are typing
fast. Before this module, each of those returned zero results from a shop that
had dozens of matching items.

Three passes, applied in order:

  1. Drop terms too short to be meaningful. "t shirt" splits into "t" and
     "shirt"; the bare "t" appears in nearly every description, so it used to
     match all 102 products.
  2. Map known variants onto the vocabulary the catalogue actually uses —
     spelling differences, plurals, and the words people use for a garment
     that the product copy does not.
  3. For a term that still matches nothing, try close spellings.
"""

from __future__ import annotations

import difflib
import re

# Terms shorter than this are dropped unless they are a known size or a word
# the catalogue genuinely uses on its own.
MIN_TERM_LENGTH = 3
KEEP_SHORT = {"xs", "s", "m", "l", "xl", "xxl", "tee", "zip", "art", "law", "cap", "mom", "dad"}

# Words with no discriminating power here — every product is Yale apparel, so
# matching on "yale" or "shirt" alone just returns the catalogue.
STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "for", "with", "in", "on", "to",
    "my", "me", "i", "you", "your", "some", "any", "do", "have", "got",
    "want", "need", "looking", "show", "find", "get", "buy", "something",
    "anything", "please", "thanks", "that", "this", "these", "those",
    "is", "are", "it", "its", "can", "could", "would", "like", "about",
}

# Shopper vocabulary -> the word the catalogue uses.
SYNONYMS: dict[str, str] = {
    # Spelling variants
    "grey": "gray",
    "colour": "color",
    "colours": "colors",
    "favourite": "favorite",
    # Garment names people use that the product copy does not
    "jumper": "sweater",
    "jumpers": "sweater",
    "pully": "pullover",
    "sweatshirts": "sweatshirt",
    "crew": "crewneck",
    "crewnecks": "crewneck",
    "hoody": "hoodie",
    "hoodys": "hoodie",
    "hoodies": "hoodie",
    "hooded": "hoodie",
    "tees": "tee",
    "tshirt": "t-shirt",
    "tshirts": "t-shirt",
    "teeshirt": "t-shirt",
    "quarterzip": "quarter-zip",
    "halfzip": "quarter-zip",
    "zipup": "full-zip",
    "zipper": "zip",
    "coat": "jacket",
    "coats": "jacket",
    "jackets": "jacket",
    "fleeces": "fleece",
    "joggers": "pants",
    "longsleeve": "long-sleeve",
    "longsleeves": "long-sleeve",
    # Plurals of common nouns
    "shirts": "shirt",
    "sweaters": "sweater",
    "pullovers": "pullover",
    "bulldogs": "bulldog",
    "colleges": "college",
    # Occasion words shoppers use
    "gift": "gift",
    "gifts": "gift",
    "present": "gift",
    "presents": "gift",
}

# Multi-word phrases, replaced before the query is split into terms.
PHRASES: dict[str, str] = {
    "t shirt": "t-shirt",
    "t shirts": "t-shirt",
    "tee shirt": "t-shirt",
    "quarter zip": "quarter-zip",
    "half zip": "quarter-zip",
    "1/4 zip": "quarter-zip",
    "zip up": "full-zip",
    "full zip": "full-zip",
    "long sleeve": "long-sleeve",
    "long sleeves": "long-sleeve",
    "crew neck": "crewneck",
    "mock neck": "mockneck",
}


def _fuzzy(term: str, vocabulary: set[str]) -> str | None:
    """Closest vocabulary word within one or two edits, or None."""
    if len(term) < 4:
        return None
    matches = difflib.get_close_matches(term, vocabulary, n=1, cutoff=0.82)
    return matches[0] if matches else None


def normalize_query(query: str, vocabulary: set[str] | None = None) -> list[str]:
    """
    Turn a raw shopper query into the terms search should actually look for.

    `vocabulary` is the set of words that appear in the catalogue; when given,
    it is used to rescue typos. Returns an empty list if nothing survives,
    which the caller should treat as "no usable search terms".
    """
    text = query.lower().strip()

    for phrase, replacement in PHRASES.items():
        text = text.replace(phrase, replacement)

    # Keep hyphens (quarter-zip) and apostrophes; drop other punctuation.
    text = re.sub(r"[^a-z0-9\-'\s]", " ", text)

    terms: list[str] = []
    for raw in text.split():
        term = raw.strip("-'")
        if not term or term in STOPWORDS:
            continue

        term = SYNONYMS.get(term, term)

        if len(term) < MIN_TERM_LENGTH and term not in KEEP_SHORT:
            continue

        if vocabulary and term not in vocabulary:
            corrected = _fuzzy(term, vocabulary)
            if corrected:
                term = corrected

        if term not in terms:
            terms.append(term)

    return terms


def build_vocabulary(products: list[dict]) -> set[str]:
    """Every word that appears in searchable catalogue text, for typo rescue."""
    words: set[str] = set()
    for p in products:
        blob = " ".join(
            [p["name"], p["description"], p["category"], " ".join(p["tags"]), " ".join(p["colors"])]
        ).lower()
        for w in re.findall(r"[a-z][a-z\-]{2,}", blob):
            words.add(w)
    return words
