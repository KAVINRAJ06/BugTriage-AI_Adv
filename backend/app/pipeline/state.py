from typing import Any, TypedDict


class RequestMetadata(TypedDict, total=False):
    reporter_email: str
    client_ip: str
    user_agent: str
    submitted_at: str


class HeuristicRegister(TypedDict, total=False):
    severity: str
    component: str
    tags: list[str]
    confidence: float
    explicit_critical_trigger: bool
    gatekeeper_active: bool


class LLMRegister(TypedDict, total=False):
    one_line_summary: str
    suggested_severity: str
    blast_radius: str
    suggested_assignee_group: str
    duplicate_likelihood: float
    heuristic_mode: str


class FinalTriage(TypedDict, total=False):
    severity: str
    base_severity: str
    heuristic_severity: str
    agent_severity: str
    component: str
    summary: str
    tags: list[str]
    assignee_group: str
    blast_radius: str
    duplicate_likelihood: float
    routing_action: str
    confidence: float
    gatekeeper_active: bool


class GraphState(TypedDict, total=False):
    title: str
    description: str
    metadata: RequestMetadata
    sanitized_description: str
    security_flagged: bool
    heuristic: HeuristicRegister
    llm: LLMRegister
    final_triage: FinalTriage
