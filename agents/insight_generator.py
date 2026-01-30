"""
Insight Generator Agent - Extracts patterns and anomalies from results.
"""

import json
import re
from typing import List
from state import AnalyticsState, Insight, Anomaly, log_state_transition
from config import get_llm, SYSTEM_PROMPT_INSIGHT, ANOMALY_THRESHOLD


def _extract_json(text: str) -> dict:
    """Extract JSON from LLM response, handling markdown fences and preamble."""
    # Strip markdown code fences
    cleaned = re.sub(r"```(?:json)?\s*", "", text).strip()
    cleaned = cleaned.rstrip("`").strip()

    # Try parsing the whole thing first
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Try to find first { ... } block
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return {}


def insight_generator_node(state: AnalyticsState) -> AnalyticsState:
    """Extract insights and detect anomalies from query results."""

    if not state["execution_results"] or not state["execution_results"].result_data:
        state["error_state"] = "No data available for insight generation"
        return log_state_transition(state, "failed", state["error_state"])

    results = state["execution_results"].result_data
    llm = get_llm()

    # Truncate large payloads to avoid token limits
    results_summary = json.dumps(results, indent=2, default=str)
    if len(results_summary) > 12000:
        results_summary = results_summary[:12000] + "\n... (truncated)"

    prompt = f"""{SYSTEM_PROMPT_INSIGHT}

DATA RESULTS:
{results_summary}

Analyze these results and extract key insights, anomalies, and findings.
Format response as JSON with: insights (list), anomalies (list), business_impact."""

    try:
        response = llm.invoke([{"role": "user", "content": prompt}])
        insight_data = _extract_json(response.content)

        # Parse insights
        insights = []
        for insight_obj in insight_data.get("insights", []):
            insight = Insight(
                finding=insight_obj.get("finding", ""),
                metric=insight_obj.get("metric", "unknown"),
                magnitude=insight_obj.get("magnitude", "N/A"),
                confidence=insight_obj.get("confidence", 0.75),
                business_impact=insight_obj.get("business_impact", "medium"),
            )
            insights.append(insight)

        # Parse anomalies
        anomalies = []
        for anomaly_obj in insight_data.get("anomalies", []):
            anomaly = Anomaly(
                description=anomaly_obj.get("description", ""),
                affected_metric=anomaly_obj.get("affected_metric", "unknown"),
                magnitude=anomaly_obj.get("magnitude", "N/A"),
                confidence=anomaly_obj.get("confidence", 0.75),
                severity=anomaly_obj.get("severity", "medium"),
            )
            anomalies.append(anomaly)

        state["insights"] = insights
        state["anomalies"] = anomalies

        state = log_state_transition(
            state,
            "visualizing",
            f"Generated {len(insights)} insights and detected {len(anomalies)} anomalies",
        )

        return state

    except Exception as e:
        state["error_state"] = f"Insight generation failed: {str(e)}"
        return log_state_transition(state, "failed", state["error_state"])
