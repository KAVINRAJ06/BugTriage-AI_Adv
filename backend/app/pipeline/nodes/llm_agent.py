import json
import re

import httpx

from app.core.config import settings
from app.db.mongodb import get_db
from app.pipeline.duplicate import weighted_duplicate_score
from app.pipeline.nodes.heuristic import is_gatekeeper_active
from app.pipeline.state import GraphState, LLMRegister

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
REQUIRED_LLM_FIELDS = {
    "one_line_summary",
    "suggested_severity",
    "blast_radius",
    "suggested_assignee_group",
}
VALID_SEVERITIES = {"P0", "P1", "P2", "P3"}
VALID_BLAST_RADIUS = {"all_users", "multiple_users", "single_user"}
VALID_ASSIGNEE_GROUPS = {"Frontend", "Backend", "Database", "General"}


class LLMServiceUnavailable(RuntimeError):
    pass


def _groq_error_detail(resp: httpx.Response) -> str:
    try:
        payload = resp.json()
    except ValueError:
        return resp.text[:300]
    error = payload.get("error")
    if isinstance(error, dict):
        return str(error.get("message") or error.get("code") or payload)[:300]
    return str(payload)[:300]


async def _duplicate_score(title: str, body: str, component: str) -> float:
    db = get_db()
    cursor = (
        db.tickets.find({}, {"title": 1, "description": 1, "heuristic": 1, "final_triage": 1})
        .sort("created_at", -1)
        .limit(50)
    )
    best = 0.0
    async for doc in cursor:
        existing_component = (
            doc.get("heuristic", {}).get("component")
            or doc.get("final_triage", {}).get("component")
            or ""
        )
        score = weighted_duplicate_score(
            title,
            body,
            doc.get("title", ""),
            doc.get("description", ""),
        )
        if existing_component == component and score >= 0.85:
            score = min(1.0, score + 0.05)
        best = max(best, score)
    return round(best, 3)


def _parse_json(content: str) -> dict:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def _build_prompt(text: str, heuristic: dict, critical_mode: bool) -> str:
    criteria = (
        "P0: complete outage, security vulnerability, widespread data corruption. "
        "P1: major feature broken, no workaround, multiple users. "
        "P2: functional bug with workaround. P3: cosmetic or documentation."
    )
    if critical_mode:
        return (
            "You are a bug triage enricher. Heuristic severity is AUTHORITATIVE. "
            "Do NOT escalate severity above the heuristic tier.\n"
            "Reply JSON only:\n"
            '{"one_line_summary":"string",'
            '"suggested_severity":"same as heuristic tier advisory",'
            '"blast_radius":"all_users|multiple_users|single_user",'
            '"suggested_assignee_group":"Frontend|Backend|Database|General"}\n\n'
            f"Heuristic (authoritative): severity={heuristic.get('severity')}, "
            f"component={heuristic.get('component')}, tags={heuristic.get('tags')}\n"
            f"Context criteria: {criteria}\n"
            f"Report:\n{text}"
        )
    return (
        "Extract bug triage fields. Reply JSON only:\n"
        '{"one_line_summary":"string","suggested_severity":"P0|P1|P2|P3",'
        '"blast_radius":"all_users|multiple_users|single_user",'
        '"suggested_assignee_group":"Frontend|Backend|Database|General"}\n\n'
        f"Heuristic baseline: severity={heuristic.get('severity')}, "
        f"component={heuristic.get('component')}\n"
        f"Context criteria: {criteria}\n"
        f"Report:\n{text}"
    )


def _split_sanitized_report(text: str) -> tuple[str, str]:
    title, _, body = text.partition("\n")
    return title.strip(), (body or title).strip()


def _fallback_llm_register(
    title: str,
    heuristic: dict,
    duplicate_likelihood: float,
    critical_mode: bool,
) -> LLMRegister:
    component = heuristic.get("component", "General")
    assignee_group = component if component in VALID_ASSIGNEE_GROUPS else "General"
    return {
        "one_line_summary": title[:160] or "Bug report requires triage",
        "suggested_severity": heuristic.get("severity", "P3"),
        "blast_radius": "multiple_users" if heuristic.get("severity") in {"P0", "P1"} else "single_user",
        "suggested_assignee_group": assignee_group,
        "duplicate_likelihood": duplicate_likelihood,
        "heuristic_mode": "critical" if critical_mode else "fallback",
    }


def _validate_llm_response(data: dict) -> dict:
    missing = REQUIRED_LLM_FIELDS - data.keys()
    if missing:
        raise LLMServiceUnavailable(
            f"Groq response missing required fields: {', '.join(sorted(missing))}"
        )

    severity = data["suggested_severity"]
    blast_radius = data["blast_radius"]
    assignee_group = data["suggested_assignee_group"]
    summary = data["one_line_summary"]

    if severity not in VALID_SEVERITIES:
        raise LLMServiceUnavailable("Groq response included an invalid severity")
    if blast_radius not in VALID_BLAST_RADIUS:
        raise LLMServiceUnavailable("Groq response included an invalid blast radius")
    if assignee_group not in VALID_ASSIGNEE_GROUPS:
        raise LLMServiceUnavailable("Groq response included an invalid assignee group")
    if not isinstance(summary, str) or not summary.strip():
        raise LLMServiceUnavailable("Groq response included an empty summary")

    return data


async def llm_extraction_node(state: GraphState) -> dict:
    text = state.get("sanitized_description", "")
    title, body = _split_sanitized_report(text)
    heuristic = state.get("heuristic", {})
    critical_mode = is_gatekeeper_active(heuristic)

    try:
        duplicate_likelihood = await _duplicate_score(
            title, body, heuristic.get("component", "General")
        )
    except Exception:
        duplicate_likelihood = 0.0

    if not settings.groq_configured:
        return {"llm": _fallback_llm_register(title, heuristic, duplicate_likelihood, critical_mode)}

    prompt = _build_prompt(text, heuristic, critical_mode)
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                json={
                    "model": settings.groq_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.0,
                    "max_tokens": 300,
                },
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            data = _validate_llm_response(_parse_json(content))
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 401:
            raise LLMServiceUnavailable("Groq API key is invalid or unauthorized") from exc
        raise LLMServiceUnavailable(
            f"Groq API request failed ({exc.response.status_code}): {_groq_error_detail(exc.response)}"
        ) from exc
    except LLMServiceUnavailable:
        raise
    except Exception as exc:
        raise LLMServiceUnavailable("Groq LLM enrichment failed") from exc

    agent_sev = data["suggested_severity"]
    if critical_mode:
        agent_sev = heuristic.get("severity", agent_sev)

    register: LLMRegister = {
        "one_line_summary": data["one_line_summary"],
        "suggested_severity": agent_sev,
        "blast_radius": data["blast_radius"],
        "suggested_assignee_group": data["suggested_assignee_group"],
        "duplicate_likelihood": duplicate_likelihood,
        "heuristic_mode": "critical" if critical_mode else "neutral",
    }
    return {"llm": register}
