import re

from app.pipeline.state import GraphState, HeuristicRegister

SEVERITY_RANK = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}

# P0 triggers
P0_PATTERNS = [
    re.compile(r"data\s+loss", re.I),
    re.compile(r"corrupt\s+database", re.I),
    re.compile(r"security\s+breach", re.I),
    re.compile(r"\bdown\b", re.I),
    re.compile(r"auth\s+failure", re.I),
    re.compile(r"cannot\s+login", re.I),
]

# P1 triggers
P1_PATTERNS = [
    re.compile(r"\bcrash\b", re.I),
    re.compile(r"nullpointerexception", re.I),
    re.compile(r"segment\s+fault", re.I),
    re.compile(r"traceback|exception|at\s+\w+\.\w+\(", re.I),
]

# P2 triggers
P2_PATTERNS = [
    re.compile(r"ui\s+misaligned", re.I),
    re.compile(r"slow\s+performance", re.I),
    re.compile(r"button\s+unresponsive", re.I),
    re.compile(r"validation\s+error", re.I),
]

# P3 triggers
P3_PATTERNS = [
    re.compile(r"\btypo\b", re.I),
    re.compile(r"color\s+mismatch", re.I),
    re.compile(r"\bcosmetic\b", re.I),
    re.compile(r"\bdocumentation\b", re.I),
]

STACK_TRACE = re.compile(r"(traceback|exception|at\s+\w+\.\w+\(|Error:\s)", re.I)
HTTP_5XX = re.compile(r"\b(500|502|503)\b|500\s+internal\s+server\s+error|gateway\s+timeout", re.I)
URL_PATTERN = re.compile(r"https?://", re.I)

FRONTEND_PATTERNS = [
    re.compile(r"uncaught\s+typeerror", re.I),
    re.compile(r"\bcss\b", re.I),
    re.compile(r"\breact\b", re.I),
    re.compile(r"\.jsx\b", re.I),
    re.compile(r"\.tsx\b", re.I),
    re.compile(r"\b(chrome|safari|ios|firefox|android)\b", re.I),
]

BACKEND_PATTERNS = [
    re.compile(r"500\s+internal\s+server\s+error", re.I),
    re.compile(r"gateway\s+timeout", re.I),
    re.compile(r"axioserror", re.I),
    re.compile(r"\bsequelize\b", re.I),
    re.compile(r"\bmongoose\b", re.I),
]

DATABASE_PATTERNS = [
    re.compile(r"mongoservererror", re.I),
    re.compile(r"\bindex\b", re.I),
    re.compile(r"mongooseerror", re.I),
    re.compile(r"\bbson\b", re.I),
    re.compile(r"\bdeadlock\b", re.I),
]


def _tier_from_patterns(text: str) -> tuple[str, float]:
    """Return worst matching tier and confidence."""
    if any(p.search(text) for p in P0_PATTERNS):
        return "P0", 0.95
    if any(p.search(text) for p in P1_PATTERNS):
        return "P1", 0.95
    if any(p.search(text) for p in P2_PATTERNS):
        return "P2", 0.80
    if any(p.search(text) for p in P3_PATTERNS):
        return "P3", 0.50
    if STACK_TRACE.search(text) or HTTP_5XX.search(text):
        return "P2", 0.80
    return "P3", 0.50


def _detect_component(text: str) -> str:
    if any(p.search(text) for p in DATABASE_PATTERNS):
        return "Database"
    if any(p.search(text) for p in BACKEND_PATTERNS):
        return "Backend"
    if any(p.search(text) for p in FRONTEND_PATTERNS):
        return "Frontend"
    return "General"


def is_gatekeeper_active(heuristic: HeuristicRegister) -> bool:
    sev = heuristic.get("severity", "P3")
    conf = heuristic.get("confidence", 0.0)
    return bool(heuristic.get("explicit_critical_trigger")) or (
        conf >= 0.8 and sev in ("P0", "P1")
    )


def heuristic_rules_node(state: GraphState) -> dict:
    text = state.get("sanitized_description", "")
    severity, confidence = _tier_from_patterns(text)

    tags: list[str] = []
    if STACK_TRACE.search(text):
        tags.append("Stack-Trace")
    if HTTP_5XX.search(text):
        tags.append("HTTP-5xx")
    if any(p.search(text) for p in FRONTEND_PATTERNS):
        tags.append("Client-Telemetry")
    if URL_PATTERN.search(text):
        tags.append("URL")
    if severity in ("P0", "P1"):
        tags.append(f"{severity}-Critical")

    explicit_critical = confidence >= 0.8 and severity in ("P0", "P1")

    register: HeuristicRegister = {
        "severity": severity,
        "component": _detect_component(text),
        "tags": tags,
        "confidence": confidence,
        "explicit_critical_trigger": explicit_critical,
        "gatekeeper_active": is_gatekeeper_active(
            {
                "severity": severity,
                "confidence": confidence,
                "explicit_critical_trigger": explicit_critical,
            }
        ),
    }
    return {"heuristic": register}
