import re
from difflib import SequenceMatcher

URL_PATTERN = re.compile(r"https?://\S+", re.I)
BUG_ID_PATTERN = re.compile(r"bug-\d+", re.I)


def normalize_text(text: str) -> str:
    t = text.lower()
    t = URL_PATTERN.sub("[url]", t)
    t = BUG_ID_PATTERN.sub("[id]", t)
    t = re.sub(r"[^a-z0-9\s.,;:!?'\-]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def similarity(a: str, b: str) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def weighted_duplicate_score(
    title: str,
    body: str,
    existing_title: str,
    existing_body: str,
    title_weight: float = 0.65,
) -> float:
    nt, nb = normalize_text(title), normalize_text(body)
    et, eb = normalize_text(existing_title), normalize_text(existing_body)
    body_weight = 1.0 - title_weight
    return title_weight * similarity(nt, et) + body_weight * similarity(nb, eb)
