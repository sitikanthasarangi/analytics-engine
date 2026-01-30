"""
Graph definition for the Autonomous Analytics Recommendation Engine.

This file wires together:
- interpreter
- capabilities_helper (for generic "what can you do" questions)
- data_advisor
- planner
- execution_agent
- execute_queries
- insight_generator
- visualization_agent
- confidence_guardrails
"""

from typing import TypedDict, Optional, Any

from langgraph.graph import StateGraph, START, END

from state import AnalyticsState
from agents import (
    question_interpreter_node,
    data_advisor_node,
    analysis_planner_node,
    execution_agent_node,
    execute_queries_node,
    answer_synthesizer_node,
    insight_generator_node,
    visualization_agent_node,
    confidence_guardrails_node,
)
from agents.capabilities_helper import capabilities_helper_node


# ---------------------------------------------------------------------------
# Routing logic
# ---------------------------------------------------------------------------

def route_after_interpreter(state: AnalyticsState) -> str:
    """
    Route after interpreter:
    - If the question is generic (what can you help with, etc.), go to capabilities_helper.
    - Otherwise, continue to data_advisor for normal analysis.
    """
    intent = state.get("interpreted_intent")
    if intent and getattr(intent, "is_generic", False):
        return "capabilities_helper"
    return "data_advisor"


def route_after_execution(state: AnalyticsState) -> str:
    """
    Route after execution:
    - If execution_results is missing or failed, go directly to guardrails.
    - Otherwise continue to insights.
    """
    exec_results = state.get("execution_results")
    if not exec_results or not getattr(exec_results, "success", True):
        return "guardrails"
    return "insights"


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def create_graph():
    """
    Build and return the LangGraph state machine for the analytics engine.
    """
    graph_builder = StateGraph(AnalyticsState)

    # Nodes
    graph_builder.add_node("interpreter", question_interpreter_node)
    graph_builder.add_node("capabilities_helper", capabilities_helper_node)
    graph_builder.add_node("data_advisor", data_advisor_node)
    graph_builder.add_node("planner", analysis_planner_node)
    graph_builder.add_node("execution_agent", execution_agent_node)
    graph_builder.add_node("execute_queries", execute_queries_node)
    graph_builder.add_node("answer_synthesizer", answer_synthesizer_node)
    graph_builder.add_node("insights", insight_generator_node)
    graph_builder.add_node("visualizations", visualization_agent_node)
    graph_builder.add_node("guardrails", confidence_guardrails_node)

    # Entry point
    graph_builder.add_edge(START, "interpreter")

    # After interpreter: either capabilities helper or normal analysis
    graph_builder.add_conditional_edges(
        "interpreter",
        route_after_interpreter,
        {
            "capabilities_helper": "capabilities_helper",
            "data_advisor": "data_advisor",
        },
    )

    # Capabilities helper ends the run
    graph_builder.add_edge("capabilities_helper", END)

    # Normal analysis path
    graph_builder.add_edge("data_advisor", "planner")
    graph_builder.add_edge("planner", "execution_agent")
    graph_builder.add_edge("execution_agent", "execute_queries")

    # After execution: synthesize a direct answer, then route to insights or guardrails
    graph_builder.add_edge("execute_queries", "answer_synthesizer")

    graph_builder.add_conditional_edges(
        "answer_synthesizer",
        route_after_execution,
        {
            "insights": "insights",
            "guardrails": "guardrails",
        },
    )

    # Insights → visualizations → guardrails → END
    graph_builder.add_edge("insights", "visualizations")
    graph_builder.add_edge("visualizations", "guardrails")
    graph_builder.add_edge("guardrails", END)

    # Compile WITHOUT checkpointing (simpler for local/dev)
    graph = graph_builder.compile()
    return graph


# Cached graph instance for reuse
_graph_instance: Optional[Any] = None


def get_graph():
    """
    Get a singleton instance of the compiled graph.
    """
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = create_graph()
    return _graph_instance
