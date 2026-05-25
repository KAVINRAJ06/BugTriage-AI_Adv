from app.core.config import settings
from app.pipeline.nodes.heuristic import is_gatekeeper_active
from app.pipeline.state import FinalTriage, GraphState

SEVERITY_RANK = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}


def _worse(a: str, b: str) -> str:
    return a if SEVERITY_RANK[a] <= SEVERITY_RANK[b] else b


def reconciler_node(state: GraphState) -> dict:
    heuristic = state.get("heuristic", {})
    llm = state.get("llm", {})

    h_sev = heuristic.get("severity", "P3")
    h_component = heuristic.get("component", "General")
    h_tags = heuristic.get("tags", [])
    h_conf = heuristic.get("confidence", 0.5)

    agent_sev = llm.get("suggested_severity", h_sev)
    blast = llm.get("blast_radius", "single_user")
    duplicate = llm.get("duplicate_likelihood", 0.0)
    summary = llm.get("one_line_summary", "")
    assignee = llm.get("suggested_assignee_group", h_component)
    dup_threshold = settings.duplicate_likelihood_threshold

    gatekeeper = is_gatekeeper_active(heuristic)

    if gatekeeper:
        base_sev = _worse(h_sev, agent_sev)
        routing = "Heuristic supremacy: gatekeeper active on critical signals."
    else:
        base_sev = agent_sev if agent_sev in SEVERITY_RANK else h_sev
        routing = "Semantic cross-validation: neutral heuristic baseline."

    final_sev = base_sev

    # LLM-solo P0 cap
    if not gatekeeper and h_sev in ("P2", "P3") and final_sev == "P0":
        final_sev = "P1" if blast in ("all_users", "multiple_users") else "P2"
        routing = "LLM-solo P0 blocked: heuristic baseline prevents unilateral escalation."

    # Blast radius suppressor
    if not gatekeeper and final_sev == "P0" and blast == "single_user" and duplicate < dup_threshold:
        final_sev = "P2"
        routing = "Blast radius suppressor: isolated impact downgraded from P0."

    # Duplicate mitigation
    elif not gatekeeper and final_sev == "P1" and blast == "multiple_users" and duplicate >= dup_threshold:
        final_sev = "P2"
        routing = "Duplicate mitigation: normalized similarity exceeds threshold."

    elif not gatekeeper and final_sev == "P1" and blast == "multiple_users" and duplicate < dup_threshold:
        routing = "Semantic approval: high impact across multiple users confirmed."

    triage: FinalTriage = {
        "severity": final_sev,
        "base_severity": base_sev,
        "heuristic_severity": h_sev,
        "agent_severity": agent_sev,
        "component": h_component,
        "summary": summary,
        "tags": h_tags,
        "assignee_group": assignee,
        "blast_radius": blast,
        "duplicate_likelihood": duplicate,
        "routing_action": routing,
        "confidence": h_conf,
        "gatekeeper_active": gatekeeper,
    }
    return {"final_triage": triage}
