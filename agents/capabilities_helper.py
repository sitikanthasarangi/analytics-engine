from state import AnalyticsState, log_state_transition
from data_manager import list_datasets

def capabilities_helper_node(state: AnalyticsState) -> AnalyticsState:
    intent = state.get("interpreted_intent")
    if not intent or not getattr(intent, "is_generic", False):
        return state

    datasets = list_datasets()

    lines = []
    lines.append("I can help you analyze your data using multiple agents that:")
    lines.append("- Understand your question and map it to metrics/entities")
    lines.append("- Select relevant datasets and design an analysis plan")
    lines.append("- Generate and execute queries (or file-based analysis)")
    lines.append("- Extract insights, anomalies, and visualizations")

    if datasets:
        lines.append("")
        lines.append("I currently see these user datasets:")
        for ds in datasets:
            cols = ds.get("schema", {}).get("columns", [])
            lines.append(f"- {ds['name']} ({len(cols)} columns) from {ds['filename']}")
    else:
        lines.append("")
        lines.append("You haven't uploaded any datasets yet. You can upload CSVs in the left panel.")

    lines.append("")
    lines.append("Example questions you can ask:")
    lines.append('- "Show revenue trend by region in the last quarter"')
    lines.append('- "Which products are underperforming based on sales and margin?"')
    lines.append('- "Why did our infrastructure cost spike last week?"')
    lines.append('- "Analyze web_sessions by country over time"')

    state["execution_log"].append("[capabilities] " + "\n".join(lines))
    state = log_state_transition(
        state,
        "completed",
        "Answered generic capabilities question instead of running full analysis",
    )
    return state
