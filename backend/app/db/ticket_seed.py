import asyncio
from datetime import datetime, timedelta, timezone

from pymongo import ReturnDocument

from app.db.mongodb import get_db, init_db

SEVERITIES = ("P0", "P1", "P2", "P3")
COMPONENTS = ("Backend", "Frontend", "Database", "General")
STATUSES = ("open", "in_progress", "resolved", "closed")
SEED_BATCH = "sample-bug-reports-v1"

SAMPLE_TITLES = [
    ("Checkout service down for all users", "P0", "Backend", "all_users"),
    ("Authentication failure blocks login", "P0", "Backend", "all_users"),
    ("Database corruption after import job", "P0", "Database", "multiple_users"),
    ("Security breach warning in session logs", "P0", "Backend", "multiple_users"),
    ("Production API returns 503 during checkout", "P0", "Backend", "all_users"),
    ("Cannot login after password reset", "P0", "Backend", "multiple_users"),
    ("Mobile app crash on payment confirmation", "P1", "Frontend", "multiple_users"),
    ("NullPointerException in order export", "P1", "Backend", "multiple_users"),
    ("Dashboard crashes when loading filters", "P1", "Frontend", "multiple_users"),
    ("Segment fault in image processor", "P1", "Backend", "multiple_users"),
    ("Exception when saving account settings", "P1", "Backend", "multiple_users"),
    ("Bulk upload fails with traceback", "P1", "Backend", "multiple_users"),
    ("Notifications worker crash loop", "P1", "Backend", "multiple_users"),
    ("Search page has slow performance", "P2", "Backend", "multiple_users"),
    ("Submit button unresponsive on Safari", "P2", "Frontend", "single_user"),
    ("Validation error on optional phone field", "P2", "Frontend", "single_user"),
    ("UI misaligned in ticket detail panel", "P2", "Frontend", "single_user"),
    ("Report export times out on large range", "P2", "Backend", "multiple_users"),
    ("Webhook retries create duplicate logs", "P2", "Backend", "multiple_users"),
    ("Dropdown closes before selection", "P2", "Frontend", "single_user"),
    ("Incorrect error message on invite form", "P2", "Frontend", "single_user"),
    ("Typo in password reset email", "P3", "General", "single_user"),
    ("Color mismatch on severity badge", "P3", "Frontend", "single_user"),
    ("Documentation link points to old page", "P3", "General", "single_user"),
    ("Cosmetic spacing issue in footer", "P3", "Frontend", "single_user"),
    ("Tooltip capitalization is inconsistent", "P3", "Frontend", "single_user"),
    ("Settings page help text is outdated", "P3", "General", "single_user"),
    ("Empty state copy needs punctuation", "P3", "General", "single_user"),
    ("Icon alignment is off by two pixels", "P3", "Frontend", "single_user"),
    ("Release notes mention old product name", "P3", "General", "single_user"),
]


def _description(title: str, severity: str, component: str, blast_radius: str) -> str:
    return (
        f"{title}. Reproduced in the {component.lower()} area. "
        f"Expected behavior differs from actual behavior. "
        f"Impact appears to affect {blast_radius.replace('_', ' ')}."
    )


async def _next_seed_ticket_id() -> str:
    counter = await get_db().counters.find_one_and_update(
        {"_id": "seed_ticket"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return f"SEED-{counter['seq']:04d}"


def _ticket_doc(
    ticket_id: str,
    title: str,
    severity: str,
    component: str,
    blast_radius: str,
    status_value: str,
    created_at: datetime,
) -> dict:
    description = _description(title, severity, component, blast_radius)
    resolved_at = created_at + timedelta(hours=18) if status_value in ("resolved", "closed") else None
    closed_at = created_at + timedelta(hours=24) if status_value == "closed" else None
    duplicate_likelihood = 0.18 if severity in ("P0", "P1") else 0.04
    return {
        "ticket_id": ticket_id,
        "title": title,
        "description": description,
        "reporter_email": f"seed-{ticket_id.lower()}@example.com",
        "screenshot_urls": [],
        "status": status_value,
        "assignee": None,
        "tags": [severity, component],
        "notes": "Seeded sample ticket for dashboard and KPI testing.",
        "metadata": {
            "seed_batch": SEED_BATCH,
            "reporter_email": f"seed-{ticket_id.lower()}@example.com",
            "submitted_at": created_at.isoformat(),
        },
        "sanitized_description": description,
        "security_flagged": severity == "P0" and "Security" in title,
        "heuristic": {
            "severity": severity,
            "component": component,
            "tags": [f"{severity}-Critical"] if severity in ("P0", "P1") else [component],
            "confidence": 0.95 if severity in ("P0", "P1") else 0.8 if severity == "P2" else 0.5,
            "explicit_critical_trigger": severity in ("P0", "P1"),
            "gatekeeper_active": severity in ("P0", "P1"),
        },
        "llm": {
            "one_line_summary": title,
            "suggested_severity": severity,
            "blast_radius": blast_radius,
            "suggested_assignee_group": component,
            "duplicate_likelihood": duplicate_likelihood,
            "heuristic_mode": "critical" if severity in ("P0", "P1") else "neutral",
        },
        "final_triage": {
            "severity": severity,
            "base_severity": severity,
            "heuristic_severity": severity,
            "agent_severity": severity,
            "component": component,
            "summary": title,
            "tags": [severity, component],
            "assignee_group": component,
            "blast_radius": blast_radius,
            "duplicate_likelihood": duplicate_likelihood,
            "routing_action": "Seeded sample triage decision.",
            "confidence": 0.9,
            "gatekeeper_active": severity in ("P0", "P1"),
        },
        "status_history": [],
        "created_at": created_at,
        "updated_at": created_at,
        "closed_at": closed_at,
        "resolved_at": resolved_at,
    }


async def seed_sample_tickets(replace: bool = True) -> int:
    await init_db()
    db = get_db()
    if replace:
        await db.tickets.delete_many({"metadata.seed_batch": SEED_BATCH})

    now = datetime.now(timezone.utc)
    docs = []
    for index, (title, severity, component, blast_radius) in enumerate(SAMPLE_TITLES):
        ticket_id = await _next_seed_ticket_id()
        created_at = now - timedelta(hours=8 * index)
        docs.append(
            _ticket_doc(
                ticket_id=ticket_id,
                title=title,
                severity=severity,
                component=component,
                blast_radius=blast_radius,
                status_value=STATUSES[index % len(STATUSES)],
                created_at=created_at,
            )
        )

    if docs:
        await db.tickets.insert_many(docs)
    return len(docs)


async def main() -> None:
    count = await seed_sample_tickets()
    print(f"Seeded {count} sample bug reports.")


if __name__ == "__main__":
    asyncio.run(main())
