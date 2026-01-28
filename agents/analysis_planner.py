"""
Analysis Planner Agent - Designs multi-step analysis approach.
"""

import json
from state import AnalyticsState, AnalysisPlan, AnalysisStep, log_state_transition
from config import get_llm, SYSTEM_PROMPT_PLANNER
from langchain_core.messages import HumanMessage, SystemMessage


def analysis_planner_node(state: AnalyticsState) -> AnalyticsState:
    """Design multi-step analysis plan based on intent and available data."""
    intent = state["interpreted_intent"]
    data_sources = state["available_data_sources"]

    if not intent or not data_sources:
        state["error_state"] = "Missing intent or data sources"
        return log_state_transition(state, "failed", state["error_state"])

    # Build planning prompt
    sources_desc = "\n".join(
        [
            f"- {s.name}: {s.table_name} (quality: {s.quality_score}, rows: {s.record_count})"
            for s in data_sources.sources
        ]
    )

    system_msg = SystemMessage(
        content=(
            SYSTEM_PROMPT_PLANNER
            + "\n\nIMPORTANT:\n"
            + "You MUST respond with VALID JSON ONLY. "
            + "Do not include any commentary, markdown, or text outside the JSON.\n"
            + 'Example:\n'
            + '{\n'
            + '  "steps": [\n'
            + '    {\n'
            + '      "description": "Compare revenue by region QoQ",\n'
            + '      "required_tables": ["revenue_fact"],\n'
            + '      "sql_template": "SELECT ...",\n'
            + '      "depends_on": []\n'
            + '    }\n'
            + '  ],\n'
            + '  "estimated_time": 30,\n'
            + '  "warnings": []\n'
            + '}\n'
        )
    )

    user_msg = HumanMessage(
        content=(
            "ANALYSIS REQUEST:\n"
            f"Task Type: {intent.task_type}\n"
            f"Metrics: {', '.join(intent.metrics)}\n"
            f"Entities: {', '.join(intent.entities)}\n"
            f"Time Window: {intent.time_window}\n"
            f"Segments: {', '.join(intent.segments)}\n\n"
            "AVAILABLE DATA SOURCES:\n"
            f"{sources_desc}\n\n"
            "Design a detailed multi-step analysis plan.\n"
            "Respond with a single JSON object only."
        )
    )

    llm = get_llm()

    try:
        response = llm.invoke([system_msg, user_msg])
        response_text = response.content.strip()

        # Handle ```json fenced blocks if present
        if response_text.startswith("```"):
            lines = response_text.splitlines()
            lines = [ln for ln in lines if not ln.strip().startswith("```")]
            response_text = "\n".join(lines).strip()

        # print("RAW PLANNER RESPONSE:", repr(response_text))  # optional debug

        plan_data = json.loads(response_text)

        steps = []
        for i, step_data in enumerate(plan_data.get("steps", []), 1):
            step = AnalysisStep(
                step_number=i,
                description=step_data.get("description", ""),
                required_tables=step_data.get("required_tables", []),
                sql_template=step_data.get("sql_template"),
                depends_on=step_data.get("depends_on", []),
            )
            steps.append(step)

        plan = AnalysisPlan(
            steps=steps,
            total_steps=len(steps),
            estimated_runtime_seconds=plan_data.get("estimated_time", 30),
            warnings=plan_data.get("warnings", []),
        )

        state["analysis_plan"] = plan
        state = log_state_transition(
            state,
            "planning",
            f"Created {len(steps)}-step analysis plan (est. {plan.estimated_runtime_seconds}s)",
        )
        return state

    except Exception as e:
        # Fallback: simple 1‑step plan so downstream nodes can still work
        fallback_step = AnalysisStep(
            step_number=1,
            description="Basic aggregation over primary metric",
            required_tables=[s.name for s in data_sources.sources],
            sql_template=None,
            depends_on=[],
        )
        plan = AnalysisPlan(
            steps=[fallback_step],
            total_steps=1,
            estimated_runtime_seconds=10,
            warnings=[f"Planner JSON parse error, using fallback plan: {str(e)}"],
        )
        state["analysis_plan"] = plan
        state["error_state"] = f"Planning failed to parse JSON cleanly: {str(e)}"
        state = log_state_transition(
            state,
            "planning",
            "Fell back to default single-step analysis plan due to JSON parse error",
        )
        return state
