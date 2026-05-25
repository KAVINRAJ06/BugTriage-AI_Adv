import asyncio
from datetime import datetime, timedelta, timezone

from app.kpi import router as kpi_router


class FakeAggregate:
    def __init__(self, rows):
        self.rows = rows

    async def to_list(self, _length):
        return self.rows


class FakeTickets:
    def __init__(self, docs):
        self.docs = docs

    def aggregate(self, pipeline):
        match = pipeline[0].get("$match", {})
        docs = [doc for doc in self.docs if self._matches(doc, match)]

        if any("$count" in stage for stage in pipeline):
            count_key = next(stage["$count"] for stage in pipeline if "$count" in stage)
            return FakeAggregate([{count_key: len(docs)}] if docs else [])

        group_id = pipeline[1]["$group"]["_id"]
        grouped = {}
        for doc in docs:
            if group_id == "$final_triage.severity":
                key = doc["final_triage"]["severity"]
            else:
                key = doc["created_at"].strftime("%Y-%m-%d")
            grouped[key] = grouped.get(key, 0) + 1

        return FakeAggregate([{"_id": key, "count": grouped[key]} for key in sorted(grouped)])

    def _matches(self, doc, match):
        for key, expected in match.items():
            value = self._value(doc, key)
            if isinstance(expected, dict):
                if "$in" in expected and value not in expected["$in"]:
                    return False
                if "$gte" in expected and value < expected["$gte"]:
                    return False
                if "$lt" in expected and value >= expected["$lt"]:
                    return False
            elif value != expected:
                return False
        return True

    def _value(self, doc, dotted):
        value = doc
        for part in dotted.split("."):
            value = value[part]
        return value


class FakeDb:
    def __init__(self, docs):
        self.tickets = FakeTickets(docs)


def test_kpi_aggregation(monkeypatch):
    async def run():
        now = datetime.now(timezone.utc)
        docs = [
            {
                "created_at": now - timedelta(hours=25),
                "status": "open",
                "final_triage": {"severity": "P0"},
            },
            {
                "created_at": now - timedelta(hours=10),
                "status": "in_progress",
                "final_triage": {"severity": "P0"},
            },
            {
                "created_at": now - timedelta(hours=80),
                "status": "open",
                "final_triage": {"severity": "P1"},
            },
            {
                "created_at": now - timedelta(hours=5),
                "status": "closed",
                "final_triage": {"severity": "P2"},
            },
        ]
        monkeypatch.setattr(kpi_router, "get_db", lambda: FakeDb(docs))

        volume = await kpi_router.kpi_volume(days=4, _admin=None)
        severity = await kpi_router.kpi_severity(_admin=None)
        sla = await kpi_router.kpi_sla(_admin=None)

        assert len(volume["series"]) == 4
        assert sum(point["count"] for point in volume["series"]) == 4
        assert severity["open_by_severity"] == {"P0": 2, "P1": 1}
        assert severity["total_open"] == 3
        assert sla["P0"]["breach_count"] == 1
        assert sla["P0"]["breach_percent"] == 50.0
        assert sla["P1"]["breach_count"] == 1
        assert sla["P1"]["breach_percent"] == 100.0

    asyncio.run(run())
