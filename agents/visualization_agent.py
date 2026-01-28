"""
Visualization Agent - Selects appropriate chart types and creates visualizations.
"""

import json
from state import AnalyticsState, Visualization, log_state_transition
from config import get_llm, SYSTEM_PROMPT_VISUALIZER

def visualization_agent_node(state: AnalyticsState) -> AnalyticsState:
    """Create visualization configurations based on insights."""
    
    if not state["execution_results"] or not state["insights"]:
        state["error_state"] = "No data or insights available for visualization"
        return log_state_transition(state, "failed", state["error_state"])
    
    results = state["execution_results"].result_data
    insights = state["insights"]
    llm = get_llm()
    
    visualizations = []
    
    # Generate visualization for each insight
    for i, insight in enumerate(insights[:3]):  # Max 3 visualizations
        prompt = f"""{SYSTEM_PROMPT_VISUALIZER}

INSIGHT TO VISUALIZE:
Finding: {insight.finding}
Metric: {insight.metric}
Magnitude: {insight.magnitude}

SAMPLE DATA:
{json.dumps(results[:5], indent=2)}

Recommend the best chart type and configuration for this insight.
Return JSON: {{chart_type: "...", title: "...", dimensions: {{x: "...", y: "..."}}, confidence: 0.85}}"""
        
        try:
            response = llm.invoke([{"role": "user", "content": prompt}])
            viz_data = json.loads(response.content.strip())
            
            viz = Visualization(
                chart_id=f"chart_{i}",
                chart_type=viz_data.get("chart_type", "bar"),
                title=viz_data.get("title", f"Chart {i}"),
                data_fields=viz_data.get("dimensions", {}),
                description=f"Visualization for: {insight.finding}",
                appropriateness_score=viz_data.get("confidence", 0.85),
            )
            visualizations.append(viz)
            
        except Exception as e:
            state["execution_errors"].append(f"Failed to generate visualization {i}: {str(e)}")
    
    state["visualizations"] = visualizations
    state = log_state_transition(
        state,
        "completed",
        f"Generated {len(visualizations)} visualizations"
    )
    
    return state
