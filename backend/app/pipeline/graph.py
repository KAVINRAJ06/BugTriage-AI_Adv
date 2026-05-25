from langgraph.graph import END, StateGraph

from app.pipeline.nodes.heuristic import heuristic_rules_node
from app.pipeline.nodes.llm_agent import llm_extraction_node
from app.pipeline.nodes.reconciler import reconciler_node
from app.pipeline.nodes.security import security_guard_node
from app.pipeline.state import GraphState


def build_pipeline():
    graph = StateGraph(GraphState)
    graph.add_node("security_guard", security_guard_node)
    graph.add_node("heuristic_rules", heuristic_rules_node)
    graph.add_node("llm_extraction", llm_extraction_node)
    graph.add_node("reconciler", reconciler_node)

    graph.set_entry_point("security_guard")
    graph.add_edge("security_guard", "heuristic_rules")
    graph.add_edge("heuristic_rules", "llm_extraction")
    graph.add_edge("llm_extraction", "reconciler")
    graph.add_edge("reconciler", END)
    return graph.compile()


_pipeline = None


def get_pipeline():
    global _pipeline
    if _pipeline is None:
        _pipeline = build_pipeline()
    return _pipeline


async def run_classification(
    title: str,
    description: str,
    metadata: dict | None = None,
) -> GraphState:
    initial: GraphState = {
        "title": title,
        "description": description,
        "metadata": metadata or {},
    }
    return await get_pipeline().ainvoke(initial)
