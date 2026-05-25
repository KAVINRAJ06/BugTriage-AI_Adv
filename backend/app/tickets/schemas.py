from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field

TicketStatus = Literal["open", "in_progress", "resolved", "closed"]


class BugCreateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10, max_length=5000)
    reporter_email: EmailStr
    screenshot_urls: list[str] = Field(default_factory=list, max_length=5)


class StatusTransitionRequest(BaseModel):
    status: TicketStatus
    resolution_note: str | None = Field(None, max_length=2000)


class BugPatchRequest(BaseModel):
    assignee: str | None = Field(None, max_length=120)
    tags: list[str] | None = None
    notes: str | None = Field(None, max_length=5000)


class StatusAuditEntry(BaseModel):
    status: TicketStatus
    previous_status: TicketStatus | None = None
    changed_by: str
    changed_at: datetime
    resolution_note: str | None = None


class BugCreateResponse(BaseModel):
    ticket_id: str
    status: TicketStatus
    final_triage: dict[str, Any]
    heuristic: dict[str, Any]
    llm: dict[str, Any]
    security_flagged: bool
    created_at: datetime


class BugListItem(BaseModel):
    ticket_id: str
    title: str
    reporter_email: str
    status: TicketStatus
    severity: str
    component: str
    created_at: datetime
    updated_at: datetime


class BugDetail(BaseModel):
    ticket_id: str
    title: str
    description: str
    reporter_email: str
    screenshot_urls: list[str]
    status: TicketStatus
    assignee: str | None
    tags: list[str]
    notes: str | None
    metadata: dict[str, Any]
    security: dict[str, Any]
    heuristic: dict[str, Any]
    llm: dict[str, Any]
    final_triage: dict[str, Any]
    status_history: list[StatusAuditEntry]
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None


class PaginatedBugs(BaseModel):
    items: list[BugListItem]
    total: int
    page: int
    page_size: int
