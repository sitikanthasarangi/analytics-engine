"""
Data Advisor Agent - Validates data sources and flags quality issues.
"""

from datetime import datetime
from state import AnalyticsState, DataSources, DataSource, log_state_transition
from data_manager import list_datasets


# ---------------------------------------------------------------------------
# Static (built-in) data sources
# ---------------------------------------------------------------------------

AVAILABLE_DATA_SOURCES = {
    "revenue_fact": {
        "table": "analytics.revenue_fact",
        "columns": ["date", "region", "product_id", "revenue", "units_sold", "customer_count"],
        "primary_keys": ["date", "region", "product_id"],
        "quality_score": 0.95,
        "record_count": 500_000,
    },
    "customer_dim": {
        "table": "analytics.customer_dim",
        "columns": ["customer_id", "name", "segment", "lifetime_value", "signup_date", "region"],
        "primary_keys": ["customer_id"],
        "quality_score": 0.92,
        "record_count": 100_000,
    },
    "product_dim": {
        "table": "analytics.product_dim",
        "columns": ["product_id", "name", "category", "subcategory", "launch_date", "status"],
        "primary_keys": ["product_id"],
        "quality_score": 0.98,
        "record_count": 5_000,
    },
    "cost_ledger": {
        "table": "analytics.cost_ledger",
        "columns": ["date", "cost_center", "cost_type", "amount", "project_id"],
        "primary_keys": ["date", "cost_center", "cost_type"],
        "quality_score": 0.88,
        "record_count": 1_000_000,
    },
}


# ---------------------------------------------------------------------------
# Helper: merge built-in sources with user-registered datasets
# ---------------------------------------------------------------------------

def get_all_available_sources():
    """
    Build a dict of all datasets from the catalog.
    Keys: dataset name
    Values: table/location, columns, primary_keys, quality_score, record_count
    """
    sources = {}
    for ds in list_datasets():
        schema = ds.get("schema", {})
        sources[ds["name"]] = {
            "location": ds.get("location"),
            "columns": schema.get("columns", []),
            "primary_keys": schema.get("primary_keys", []),
            "quality_score": schema.get("quality_score", 0.9),
            "record_count": schema.get("rows", 0),
        }
    return sources


# ---------------------------------------------------------------------------
# Main node
# ---------------------------------------------------------------------------

def data_advisor_node(state: AnalyticsState) -> AnalyticsState:
    intent = state["interpreted_intent"]

    if not intent:
        state["error_state"] = "No interpreted intent available"
        return log_state_transition(state, "failed", state["error_state"])

    all_sources = get_all_available_sources()
    relevant_sources = []
    warnings = []

    metrics_lower = [m.lower() for m in intent.metrics]
    entities_lower = [e.lower() for e in intent.entities]

    # Simple heuristic: look for metrics/entities in column names
    for name, meta in all_sources.items():
        cols = [c.lower() for c in meta["columns"]]
        if any(m in " ".join(cols) for m in metrics_lower) or any(
            e in " ".join(cols) for e in entities_lower
        ):
            relevant_sources.append(name)

    # If generic or nothing matched, default to all datasets
    if not relevant_sources or intent.is_generic:
        relevant_sources = list(all_sources.keys())
        warnings.append(
            "No specific datasets matched intent clearly - using all available datasets"
        )

    # Build DataSources object
    sources = []
    for source_key in relevant_sources:
        source_info = all_sources[source_key]
        location = source_info.get("location") or source_key  # fallback to name\
        source = DataSource(
            name=source_key,
            table_name=location,
            columns=source_info.get("columns", []),
            primary_keys=source_info.get("primary_keys", []),
            quality_score=source_info.get("quality_score", 0.9),
            last_updated=datetime.now().isoformat(),
            record_count=source_info.get("record_count", 0),
        )

        sources.append(source)

    low_quality_sources = [s for s in sources if s.quality_score < 0.85]
    if low_quality_sources:
        warnings.append(
            f"Low quality datasets detected: {[s.name for s in low_quality_sources]}"
        )

    avg_quality = (
        sum(s.quality_score for s in sources) / len(sources) if sources else 0.0
    )

    data_sources = DataSources(
        sources=sources,
        total_sources=len(sources),
        coverage_score=0.9 if sources else 0.0,
        warnings=warnings,
    )

    state["available_data_sources"] = data_sources
    state = log_state_transition(
        state,
        "validating",
        f"Found {len(sources)} relevant datasets with avg quality {avg_quality:.2f}"
        if sources
        else "No datasets available",
    )
    return state


    # Build DataSources object
    sources = []
    for source_key in relevant_sources:
        source_info = all_sources[source_key]
        source = DataSource(
            name=source_key,
            table_name=source_info["table"],
            columns=source_info["columns"],
            primary_keys=source_info["primary_keys"],
            quality_score=source_info["quality_score"],
            last_updated=datetime.now().isoformat(),
            record_count=source_info["record_count"],
        )
        sources.append(source)

    # Check for low-quality sources
    low_quality_sources = [s for s in sources if s.quality_score < 0.85]
    if low_quality_sources:
        warnings.append(
            f"Low quality sources detected: {[s.name for s in low_quality_sources]}"
        )

    if not sources:
        warnings.append("No data sources found at all")

    avg_quality = (
        sum(s.quality_score for s in sources) / len(sources) if sources else 0.0
    )

    data_sources = DataSources(
        sources=sources,
        total_sources=len(sources),
        coverage_score=0.9 if sources else 0.0,
        warnings=warnings,
    )

    state["available_data_sources"] = data_sources
    state = log_state_transition(
        state,
        "validating",
        f"Found {len(sources)} relevant data sources with avg quality {avg_quality:.2f}"
        if sources
        else "No data sources available",
    )

    return state
