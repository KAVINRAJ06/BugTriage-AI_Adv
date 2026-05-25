import asyncio
from datetime import datetime, timezone

import pytest
from fastapi import BackgroundTasks, HTTPException
from starlette.requests import Request

from app.core.roles import UserRole
from app.core.user import CurrentUser
from app.tickets import router as tickets_router
from app.tickets.schemas import BugCreateRequest


class FakeCollection:
    def __init__(self, docs=None):
        self.docs = docs or []

    async def find_one(self, query):
        for doc in self.docs:
            if all(doc.get(key) == value for key, value in query.items()):
                return doc
        return None

    async def insert_one(self, doc):
        self.docs.append(doc)

    async def find_one_and_update(self, query, update, upsert=False, return_document=None):
        doc = await self.find_one(query)
        if not doc and upsert:
            doc = {**query}
            self.docs.append(doc)

        if doc:
            for key, value in update.get("$inc", {}).items():
                doc[key] = doc.get(key, 0) + value
            doc.update(update.get("$set", {}))
            for key, value in update.get("$push", {}).items():
                doc.setdefault(key, []).append(value)

        return doc


class FakeDb:
    def __init__(self):
        self.tickets = FakeCollection()
        self.counters = FakeCollection()


def _request():
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/report",
            "headers": [],
            "client": ("127.0.0.1", 50000),
        }
    )


def _ticket(ticket_id, reporter_email):
    now = datetime.now(timezone.utc)
    return {
        "ticket_id": ticket_id,
        "title": "Login button fails",
        "description": "Clicking the login button does nothing.",
        "reporter_email": reporter_email,
        "screenshot_urls": [],
        "status": "open",
        "assignee": None,
        "tags": [],
        "notes": None,
        "metadata": {},
        "sanitized_description": "Clicking the login button does nothing.",
        "security_flagged": False,
        "heuristic": {},
        "llm": {},
        "final_triage": {},
        "status_history": [],
        "created_at": now,
        "updated_at": now,
        "closed_at": None,
    }


def test_report_creation_uses_authenticated_reporter_email(monkeypatch):
    async def run():
        db = FakeDb()

        async def fake_run_classification(title, description, metadata):
            return {
                "sanitized_description": description,
                "security_flagged": False,
                "heuristic": {},
                "llm": {},
                "final_triage": {"severity": "P2", "summary": "Login failure"},
            }

        monkeypatch.setattr(tickets_router, "get_db", lambda: db)
        monkeypatch.setattr(tickets_router, "run_classification", fake_run_classification)

        body = BugCreateRequest(
            title="Login button fails",
            description="Clicking the login button does nothing.",
            reporter_email="other@example.com",
        )
        reporter = CurrentUser(email="owner@example.com", role=UserRole.VIEWER)

        result = await tickets_router.create_report(body, _request(), BackgroundTasks(), reporter)

        assert result.ticket_id == "BUG-9801"
        assert db.tickets.docs[0]["reporter_email"] == "owner@example.com"
        assert db.tickets.docs[0]["metadata"]["reporter_email"] == "owner@example.com"

    asyncio.run(run())


def test_admin_can_change_status_any_time_and_records_previous_status(monkeypatch):
    async def run():
        db = FakeDb()
        ticket = _ticket("BUG-9810", "owner@example.com")
        ticket["status"] = "closed"
        db.tickets.docs.append(ticket)
        monkeypatch.setattr(tickets_router, "get_db", lambda: db)

        admin = CurrentUser(email="admin@example.com", role=UserRole.ADMIN)
        body = tickets_router.StatusTransitionRequest(
            status="resolved",
            resolution_note="Reopened as resolved after verification.",
        )

        detail = await tickets_router.transition_status(
            "BUG-9810",
            body,
            BackgroundTasks(),
            admin,
        )

        assert detail.status == "resolved"
        assert detail.status_history[-1].previous_status == "closed"
        assert detail.status_history[-1].status == "resolved"
        assert detail.status_history[-1].resolution_note == "Reopened as resolved after verification."

    asyncio.run(run())


def test_read_only_ticket_requires_matching_reporter(monkeypatch):
    async def run():
        db = FakeDb()
        db.tickets.docs.append(_ticket("BUG-9808", "owner@example.com"))
        monkeypatch.setattr(tickets_router, "get_db", lambda: db)

        owner = CurrentUser(email="owner@example.com", role=UserRole.VIEWER)
        intruder = CurrentUser(email="other@example.com", role=UserRole.VIEWER)

        detail = await tickets_router.get_report_ticket("BUG-9808", owner)
        assert detail.ticket_id == "BUG-9808"
        assert detail.reporter_email == "owner@example.com"

        with pytest.raises(HTTPException) as exc:
            await tickets_router.get_report_ticket("BUG-9808", intruder)
        assert exc.value.status_code == 404

    asyncio.run(run())
