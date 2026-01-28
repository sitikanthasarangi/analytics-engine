"""
Confidence & Guardrails Agent - Quantifies uncertainty and adds caveats.
"""

import json
from state import AnalyticsState, ConfidenceMetrics, log_state_transition
from config import get_llm, SYSTEM_PROMPT_GUARDRAILS, CONFIDENCE_THRESHOLD, MIN_DATA_POINTS

def confidence_guardrails_node(state: AnalyticsState) -> AnalyticsState:
    """Assess confidence in results and add appropriate disclaimers."""
    
    results = state["execution_results"]
    insights = state["insights"]
    
    if not results:
        state["error_state"] = "No execution results to assess"
        return log_state_transition(state, "failed", state["error_state"])
    
    llm = get_llm()
    row_count = results.row_count
    
    # Assess data characteristics
    caveats = []
    data_quality_issues = []
    recommendations = []
    
    # Check sample size
    if row_count < MIN_DATA_POINTS:
        caveats.append(f"Limited sample size ({row_count} rows). Results may be noisy.")
        data_quality_issues.append("insufficient_sample_size")
    
    # Check data freshness (mock)
    caveats.append("Analysis based on data from last 24 hours")
    
    # Call LLM for confidence assessment
    prompt = f"""{SYSTEM_PROMPT_GUARDRAILS}

ANALYSIS RESULTS:
Row Count: {row_count}
Query Count: {len(results.queries_executed)}
Execution Time: {results.execution_time_total_ms}ms
Insights Found: {len(insights)}

SAMPLE INSIGHTS:
{json.dumps([i.model_dump() for i in insights[:2]], indent=2)}

Assess confidence and identify any concerns.
Return JSON: {{overall_confidence: 0.85, caveats: [...], data_quality_issues: [...], recommendations: [...]}}"""
    
    try:
        response = llm.invoke([{"role": "user", "content": prompt}])
        confidence_data = json.loads(response.content.strip())
        
        confidence_metrics = ConfidenceMetrics(
            overall_confidence=confidence_data.get("overall_confidence", 0.75),
            sample_size_adequate=row_count >= MIN_DATA_POINTS,
            completeness_score=0.90,  # Mock value
            caveats=caveats + confidence_data.get("caveats", []),
            data_quality_issues=data_quality_issues + confidence_data.get("data_quality_issues", []),
            recommendations=confidence_data.get("recommendations", []),
        )
        
        state["confidence_assessment"] = confidence_metrics
        state = log_state_transition(
            state,
            "completed",
            f"Confidence assessment complete: {confidence_metrics.overall_confidence:.0%} confidence"
        )
        
        return state
        
    except Exception as e:
        state["error_state"] = f"Confidence assessment failed: {str(e)}"
        return log_state_transition(state, "failed", state["error_state"])
