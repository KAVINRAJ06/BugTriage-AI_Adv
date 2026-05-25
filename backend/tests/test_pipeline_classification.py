import asyncio

from app.pipeline import graph
from app.pipeline.nodes.reconciler import reconciler_node


def test_langgraph_classification_logic_with_mocked_llm(monkeypatch):
    async def run():
        async def fake_llm_node(state):
            return {
                "llm": {
                    "one_line_summary": "Checkout is down for all users",
                    "suggested_severity": "P0",
                    "blast_radius": "all_users",
                    "suggested_assignee_group": "Backend",
                    "duplicate_likelihood": 0.1,
                    "heuristic_mode": "critical",
                }
            }

        monkeypatch.setattr(graph, "llm_extraction_node", fake_llm_node)
        graph._pipeline = None

        result = await graph.run_classification(
            "Checkout outage",
            "Checkout is down and customers cannot login.",
            {"source": "test"},
        )

        assert result["heuristic"]["severity"] == "P0"
        assert result["heuristic"]["gatekeeper_active"] is True
        assert result["llm"]["one_line_summary"] == "Checkout is down for all users"
        assert result["final_triage"]["severity"] == "P0"
        assert "Heuristic supremacy" in result["final_triage"]["routing_action"]

    asyncio.run(run())


def test_llm_only_p0_caps_all_users_to_p1():
    result = reconciler_node(
        {
            "heuristic": {
                "severity": "P3",
                "component": "General",
                "tags": [],
                "confidence": 0.5,
                "explicit_critical_trigger": False,
            },
            "llm": {
                "one_line_summary": "Workspace unavailable globally",
                "suggested_severity": "P0",
                "blast_radius": "all_users",
                "suggested_assignee_group": "Backend",
                "duplicate_likelihood": 0.0,
            },
        }
    )

    final = result["final_triage"]
    assert final["severity"] == "P1"
    assert final["base_severity"] == "P0"
    assert final["routing_action"].startswith("LLM-solo P0 blocked")
