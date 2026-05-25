import re

from app.pipeline.state import GraphState

MIN_CONTENT_LEN = 20

INJECTION_PATTERNS = [
    re.compile(r"\bignore\s+(all\s+)?(previous|prior)\s+instructions\b", re.I),
    re.compile(r"\bdisregard\s+(all\s+)?(previous|prior)\s+instructions\b", re.I),
    re.compile(r"\bignore\s+rules\b", re.I),
    re.compile(r"\bignore\s+previous\s+instructions\b", re.I),
    re.compile(r"\bset\s+(severity\s+)?to\s+p0\b", re.I),
    re.compile(r"\boverride\s+system\s+rules\b", re.I),
    re.compile(r"\bsystem\s*:\s*", re.I),
    re.compile(r"\badmin\s+override\b", re.I),
]


def _strip_injection(text: str) -> tuple[str, bool]:
    flagged = False
    cleaned = text
    for pattern in INJECTION_PATTERNS:
        if pattern.search(cleaned):
            flagged = True
            cleaned = pattern.sub("", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return cleaned, flagged


def security_guard_node(state: GraphState) -> dict:
    raw = f"{state.get('title', '')}\n{state.get('description', '')}".strip()
    sanitized, flagged = _strip_injection(raw)

    if flagged and len(sanitized) < MIN_CONTENT_LEN:
        placeholder = (
            f"[Content removed due to security policy. "
            f"Original length: {len(raw)} characters.]"
        )
        return {"sanitized_description": placeholder, "security_flagged": True}

    if flagged:
        return {"sanitized_description": sanitized or raw, "security_flagged": True}

    return {"sanitized_description": raw, "security_flagged": False}
