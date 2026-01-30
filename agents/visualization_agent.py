"""
Visualization Agent - Selects appropriate chart types and creates visualizations.
"""

import json
import re
from state import AnalyticsState, Visualization, log_state_transition
from config import get_llm, SYSTEM_PROMPT_VISUALIZER


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


def visualization_agent_node(state: AnalyticsState) -> AnalyticsState:
    """Create visualization configurations based on execution results and insights."""

    exec_results = state.get("execution_results")
    if not exec_results or not exec_results.result_data:
        state["error_state"] = "No data available for visualization"
        return log_state_transition(state, "failed", state["error_state"])

    result_data = exec_results.result_data  # dict: dataset_name -> analysis dict
    insights = state.get("insights", [])
    llm = get_llm()
    visualizations = []
    chart_idx = 0

    # Build a compact data summary for the LLM prompt
    data_summary_parts = []
    for ds_name, ds_result in result_data.items():
        part = f"Dataset: {ds_name}\n"
        if "groupby" in ds_result:
            gb = ds_result["groupby"]
            part += f"  GroupBy: {gb['dimension']} by {gb['metric']}\n"
            part += f"  Top rows: {json.dumps(gb['data'][:5], default=str)}\n"
        if "summary" in ds_result:
            part += f"  Summary stats (first 5): {json.dumps(ds_result['summary'][:5], default=str)}\n"
        data_summary_parts.append(part)
    data_summary = "\n".join(data_summary_parts)
    if len(data_summary) > 8000:
        data_summary = data_summary[:8000] + "\n... (truncated)"

    # If we have insights, generate per-insight charts
    if insights:
        for insight in insights[:3]:
            prompt = f"""{SYSTEM_PROMPT_VISUALIZER}

INSIGHT TO VISUALIZE:
Finding: {insight.finding}
Metric: {insight.metric}
Magnitude: {insight.magnitude}

AVAILABLE DATA:
{data_summary}

Recommend the best chart type and configuration for this insight.
Return JSON: {{"chart_type": "...", "title": "...", "dimensions": {{"x": "...", "y": "..."}}, "confidence": 0.85}}"""

            try:
                response = llm.invoke([{"role": "user", "content": prompt}])
                viz_data = _extract_json(response.content)
                viz = Visualization(
                    chart_id=f"chart_{chart_idx}",
                    chart_type=viz_data.get("chart_type", "bar"),
                    title=viz_data.get("title", f"Chart for: {insight.finding[:60]}"),
                    data_fields=viz_data.get("dimensions", {}),
                    description=f"Visualization for: {insight.finding}",
                    appropriateness_score=viz_data.get("confidence", 0.85),
                )
                visualizations.append(viz)
                chart_idx += 1
            except Exception as e:
                state["execution_errors"].append(
                    f"Failed to generate visualization {chart_idx}: {str(e)}"
                )
    else:
        # No insights — generate charts directly from groupby data
        for ds_name, ds_result in result_data.items():
            if "groupby" in ds_result:
                gb = ds_result["groupby"]
                viz = Visualization(
                    chart_id=f"chart_{chart_idx}",
                    chart_type="bar",
                    title=f"{gb['metric']} by {gb['dimension']} ({ds_name})",
                    data_fields={"x": gb["dimension"], "y": gb["metric"], "dataset": ds_name},
                    description=f"Auto-generated bar chart from groupby on {ds_name}",
                    appropriateness_score=0.80,
                )
                visualizations.append(viz)
                chart_idx += 1

    state["visualizations"] = visualizations
    state = log_state_transition(
        state,
        "completed",
        f"Generated {len(visualizations)} visualizations",
    )

    return state
