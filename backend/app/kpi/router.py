from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query

from app.core.deps import require_admin
from app.core.user import CurrentUser
from app.db.mongodb import get_db

router = APIRouter(prefix="/kpis", tags=["kpis"])

SEVERITY_RANK = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}


@router.get("/volume")
async def kpi_volume(
    days: int = Query(7, ge=1, le=90),
    _admin: CurrentUser = Depends(require_admin),
):
    today = datetime.now(timezone.utc).date()
    start_date = today - timedelta(days=days - 1)
    start = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
    pipeline = [
        {"$match": {"created_at": {"$gte": start}}},
        {
            "$group": {
                "_id": {
                    "$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"},
                },
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"_id": 1}},
    ]
    rows = await get_db().tickets.aggregate(pipeline).to_list(None)
    counts = {r["_id"]: r["count"] for r in rows}
    series = [
        {
            "date": (start_date + timedelta(days=offset)).isoformat(),
            "count": counts.get((start_date + timedelta(days=offset)).isoformat(), 0),
        }
        for offset in range(days)
    ]
    return {"days": days, "series": series}


@router.get("/severity")
async def kpi_severity(_admin: CurrentUser = Depends(require_admin)):
    pipeline = [
        {"$match": {"status": {"$in": ["open", "in_progress"]}}},
        {"$group": {"_id": "$final_triage.severity", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]
    rows = await get_db().tickets.aggregate(pipeline).to_list(None)
    return {
        "open_by_severity": {r["_id"] or "unknown": r["count"] for r in rows},
        "total_open": sum(r["count"] for r in rows),
    }


@router.get("/sla")
async def kpi_sla(_admin: CurrentUser = Depends(require_admin)):
    now = datetime.now(timezone.utc)
    thresholds = {"P0": 24, "P1": 72}
    results = {}

    for sev, hours in thresholds.items():
        cutoff = now - timedelta(hours=hours)
        pipeline = [
            {
                "$match": {
                    "final_triage.severity": sev,
                    "status": {"$in": ["open", "in_progress"]},
                    "created_at": {"$lt": cutoff},
                }
            },
            {"$count": "breach"},
        ]
        rows = await get_db().tickets.aggregate(pipeline).to_list(1)
        breach = rows[0]["breach"] if rows else 0

        total_pipeline = [
            {
                "$match": {
                    "final_triage.severity": sev,
                    "status": {"$in": ["open", "in_progress"]},
                }
            },
            {"$count": "total"},
        ]
        total_rows = await get_db().tickets.aggregate(total_pipeline).to_list(1)
        total = total_rows[0]["total"] if total_rows else 0

        pct = round(100.0 * (total - breach) / total, 1) if total else 100.0
        breach_pct = round(100.0 * breach / total, 1) if total else 0.0
        results[sev] = {
            "sla_hours": hours,
            "open_total": total,
            "breach_count": breach,
            "breach_percent": breach_pct,
            "within_sla_percent": pct,
        }

    return results
