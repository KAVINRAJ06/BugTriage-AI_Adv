from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from pymongo import ReturnDocument

from app.core.deps import require_admin, require_reporter
from app.core.user import CurrentUser
from app.db.mongodb import get_db
from app.pipeline.graph import run_classification
from app.pipeline.nodes.llm_agent import LLMServiceUnavailable
from app.services.notifications import notify_ticket_created, notify_ticket_status_changed
from app.tickets.schemas import (
    BugCreateRequest,
    BugCreateResponse,
    BugDetail,
    BugListItem,
    BugPatchRequest,
    PaginatedBugs,
    StatusAuditEntry,
    StatusTransitionRequest,
    TicketStatus,
)

router = APIRouter(prefix="/bugs", tags=["bugs"])
public_router = APIRouter(prefix="/report", tags=["report"])

async def _next_ticket_id() -> str:
    counter = await get_db().counters.find_one_and_update(
        {"_id": "ticket"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return f"BUG-{9800 + counter['seq']}"


def _doc_to_list_item(doc: dict) -> BugListItem:
    triage = doc.get("final_triage", {})
    return BugListItem(
        ticket_id=doc["ticket_id"],
        title=doc["title"],
        reporter_email=doc["reporter_email"],
        status=doc["status"],
        severity=triage.get("severity", "P3"),
        component=triage.get("component", "General"),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


def _doc_to_detail(doc: dict) -> BugDetail:
    return BugDetail(
        ticket_id=doc["ticket_id"],
        title=doc["title"],
        description=doc["description"],
        reporter_email=doc["reporter_email"],
        screenshot_urls=doc.get("screenshot_urls", []),
        status=doc["status"],
        assignee=doc.get("assignee"),
        tags=doc.get("tags", []),
        notes=doc.get("notes"),
        metadata=doc.get("metadata", {}),
        security={
            "sanitized_description": doc.get("sanitized_description"),
            "security_flagged": doc.get("security_flagged", False),
        },
        heuristic=doc.get("heuristic", {}),
        llm=doc.get("llm", {}),
        final_triage=doc.get("final_triage", {}),
        status_history=[StatusAuditEntry(**e) for e in doc.get("status_history", [])],
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
        closed_at=doc.get("closed_at"),
    )


async def _create_bug(
    body: BugCreateRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    reporter_email: str | None = None,
) -> BugCreateResponse:
    now = datetime.now(timezone.utc)
    ticket_id = await _next_ticket_id()
    effective_reporter_email = (reporter_email or str(body.reporter_email)).lower()

    metadata = {
        "reporter_email": effective_reporter_email,
        "client_ip": request.client.host if request.client else "",
        "user_agent": request.headers.get("user-agent", ""),
        "submitted_at": now.isoformat(),
    }

    try:
        graph_result = await run_classification(body.title, body.description, metadata)
    except LLMServiceUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    final = graph_result.get("final_triage", {})

    doc = {
        "ticket_id": ticket_id,
        "title": body.title,
        "description": body.description,
        "reporter_email": effective_reporter_email,
        "screenshot_urls": body.screenshot_urls,
        "status": "open",
        "assignee": None,
        "tags": final.get("tags", []),
        "notes": None,
        "metadata": metadata,
        "sanitized_description": graph_result.get("sanitized_description"),
        "security_flagged": graph_result.get("security_flagged", False),
        "heuristic": graph_result.get("heuristic", {}),
        "llm": graph_result.get("llm", {}),
        "final_triage": final,
        "status_history": [],
        "created_at": now,
        "updated_at": now,
        "closed_at": None,
        "resolved_at": None,
    }
    await get_db().tickets.insert_one(doc)

    background_tasks.add_task(
        notify_ticket_created,
        effective_reporter_email,
        ticket_id,
        final.get("summary", ""),
        final.get("severity", "P3"),
    )

    return BugCreateResponse(
        ticket_id=ticket_id,
        status="open",
        final_triage=final,
        heuristic=graph_result.get("heuristic", {}),
        llm=graph_result.get("llm", {}),
        security_flagged=graph_result.get("security_flagged", False),
        created_at=now,
    )


@router.post("", response_model=BugCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_bug(
    body: BugCreateRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    _admin: CurrentUser = Depends(require_admin),
):
    return await _create_bug(body, request, background_tasks)


@public_router.post("", response_model=BugCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    body: BugCreateRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    reporter: CurrentUser = Depends(require_reporter),
):
    return await _create_bug(body, request, background_tasks, reporter.email)


@public_router.get("", response_model=PaginatedBugs)
async def list_report_tickets(
    reporter: CurrentUser = Depends(require_reporter),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    query = {"reporter_email": reporter.email}
    db = get_db()
    total = await db.tickets.count_documents(query)
    skip = (page - 1) * page_size
    cursor = db.tickets.find(query).sort("created_at", -1).skip(skip).limit(page_size)
    items = [_doc_to_list_item(doc) async for doc in cursor]
    return PaginatedBugs(items=items, total=total, page=page, page_size=page_size)


@public_router.get("/{ticket_id}", response_model=BugDetail)
async def get_report_ticket(ticket_id: str, reporter: CurrentUser = Depends(require_reporter)):
    doc = await get_db().tickets.find_one(
        {"ticket_id": ticket_id, "reporter_email": reporter.email}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return _doc_to_detail(doc)


@router.get("", response_model=PaginatedBugs)
async def list_bugs(
    _admin: CurrentUser = Depends(require_admin),
    status_filter: TicketStatus | None = Query(None, alias="status"),
    severity: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_dir: int = Query(-1, ge=-1, le=1),
):
    query: dict = {}
    if status_filter:
        query["status"] = status_filter
    if severity:
        query["final_triage.severity"] = severity.upper()
    if date_from or date_to:
        query["created_at"] = {}
        if date_from:
            query["created_at"]["$gte"] = date_from
        if date_to:
            query["created_at"]["$lte"] = date_to
    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"ticket_id": {"$regex": search, "$options": "i"}},
            {"reporter_email": {"$regex": search, "$options": "i"}},
        ]

    allowed_sort = {"created_at", "updated_at", "ticket_id", "status"}
    field = sort_by if sort_by in allowed_sort else "created_at"
    db = get_db()
    total = await db.tickets.count_documents(query)
    skip = (page - 1) * page_size
    cursor = db.tickets.find(query).sort(field, sort_dir).skip(skip).limit(page_size)

    items = [_doc_to_list_item(doc) async for doc in cursor]
    return PaginatedBugs(items=items, total=total, page=page, page_size=page_size)


@router.get("/{ticket_id}", response_model=BugDetail)
async def get_bug(ticket_id: str, _admin: CurrentUser = Depends(require_admin)):
    doc = await get_db().tickets.find_one({"ticket_id": ticket_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return _doc_to_detail(doc)


@router.patch("/{ticket_id}/status", response_model=BugDetail)
async def transition_status(
    ticket_id: str,
    body: StatusTransitionRequest,
    background_tasks: BackgroundTasks,
    admin: CurrentUser = Depends(require_admin),
):
    now = datetime.now(timezone.utc)
    doc = await get_db().tickets.find_one({"ticket_id": ticket_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Ticket not found")

    current = doc["status"]
    audit = {
        "status": body.status,
        "previous_status": current,
        "changed_by": admin.email,
        "changed_at": now,
        "resolution_note": body.resolution_note,
    }
    set_fields = {"status": body.status, "updated_at": now}
    if body.status in ("resolved", "closed"):
        set_fields["resolved_at"] = now
        set_fields["closed_at"] = now
    elif body.status in ("open", "in_progress"):
        set_fields["resolved_at"] = None
        set_fields["closed_at"] = None

    result = await get_db().tickets.find_one_and_update(
        {"ticket_id": ticket_id},
        {"$set": set_fields, "$push": {"status_history": audit}},
        return_document=ReturnDocument.AFTER,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Ticket not found")

    background_tasks.add_task(
        notify_ticket_status_changed,
        result["reporter_email"],
        ticket_id,
        body.status,
        body.resolution_note,
    )

    return _doc_to_detail(result)


@router.patch("/{ticket_id}", response_model=BugDetail)
async def patch_bug(
    ticket_id: str,
    body: BugPatchRequest,
    _admin: CurrentUser = Depends(require_admin),
):
    updates = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates["updated_at"] = datetime.now(timezone.utc)
    result = await get_db().tickets.find_one_and_update(
        {"ticket_id": ticket_id},
        {"$set": updates},
        return_document=ReturnDocument.AFTER,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return _doc_to_detail(result)
