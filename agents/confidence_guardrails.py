"""
Confidence & Guardrails Agent - Quantifies uncertainty and adds caveats.
"""

import json
import re
from state import AnalyticsState, ConfidenceMetrics, log_state_transition
from config import get_llm, SYSTEM_PROMPT_GUARDRAILS, CONFIDENCE_THRESHOLD, MIN_DATA_POINTS


def _extract_json(text: str) -> dict:
    """Extract JSON from LLM response, handling markdown fences."""
    cleaned = re.sub(r"```(?:json)?\s*", "", text).strip()
    cleaned = cleaned.rstrip("`").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {}


def confidence_guardrails_node(state: AnalyticsState) -> AnalyticsState:
    """Assess confidence in results and add appropriate disclaimers."""

    results = state.get("execution_results")
    insights = state.get("insights", [])

    if not results:
        state["error_state"] = "No execution results to assess"
        return log_state_transition(state, "failed", state["error_state"])

    llm = get_llm()
    row_count = results.row_count

    # Assess data characteristics
    caveats = []
    data_quality_issues = []

    # Check sample size
    if row_count < MIN_DATA_POINTS:
        caveats.append(f"Limited sample size ({row_count} rows). Results may be noisy.")
        data_quality_issues.append("insufficient_sample_size")

    caveats.append("Analysis based on data from last 24 hours")

    # Call LLM for confidence assessment
    insights_dump = json.dumps(
        [i.model_dump() for i in insights[:2]], indent=2, default=str
    ) if insights else "[]"

    prompt = f"""{SYSTEM_PROMPT_GUARDRAILS}

ANALYSIS RESULTS:
Row Count: {row_count}
Query Count: {len(results.queries_executed)}
Execution Time: {results.execution_time_total_ms}ms
Insights Found: {len(insights)}

SAMPLE INSIGHTS:
{insights_dump}

Assess confidence and identify any concerns.
Return JSON: {{"overall_confidence": 0.85, "caveats": [...], "data_quality_issues": [...], "recommendations": [...]}}"""

    try:
        response = llm.invoke([{"role": "user", "content": prompt}])
        confidence_data = _extract_json(response.content)

        confidence_metrics = ConfidenceMetrics(
            overall_confidence=confidence_data.get("overall_confidence", 0.75),
            sample_size_adequate=row_count >= MIN_DATA_POINTS,
            completeness_score=0.90,
            caveats=caveats + confidence_data.get("caveats", []),
            data_quality_issues=data_quality_issues
            + confidence_data.get("data_quality_issues", []),
            recommendations=confidence_data.get("recommendations", []),
        )

        state["confidence_assessment"] = confidence_metrics
        state = log_state_transition(
            state,
            "completed",
            f"Confidence assessment complete: {confidence_metrics.overall_confidence:.0%} confidence",
        )

        return state

    except Exception as e:
        # Fallback: still produce a basic confidence assessment
        state["confidence_assessment"] = ConfidenceMetrics(
            overall_confidence=0.5,
            sample_size_adequate=row_count >= MIN_DATA_POINTS,
            completeness_score=0.7,
            caveats=caveats + [f"LLM assessment unavailable: {e}"],
            data_quality_issues=data_quality_issues,
            recommendations=["Re-run analysis for a more detailed confidence assessment"],
        )
        state = log_state_transition(
            state,
            "completed",
            f"Confidence assessment completed with fallback (LLM error: {e})",
        )
        return state
