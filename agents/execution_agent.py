"""
Execution Agent - Generates and (mock) executes queries or file-based analysis.

For now:
- If a dataset is file-backed (data/datasets/*.csv), load via pandas
  and compute summary statistics + sample rows.
- Otherwise, simulate execution and return mocked results.

This keeps the system usable without requiring a real database,
and makes uploaded CSVs (like taxi_tripdata) actually analyzable.
"""

import time
from typing import List, Dict, Any
from pathlib import Path

import pandas as pd

from state import (
    AnalyticsState,
    AnalysisPlan,
    ExecutionResults,
    QueryExecutionRecord,
    log_state_transition,
)
from data_manager import list_datasets
from state import (
    AnalyticsState,
    AnalysisPlan,
    ExecutionResults,
    QueryExecutionRecord,
    log_state_transition,
)
from langchain_core.messages import SystemMessage, HumanMessage
from config import get_llm, SYSTEM_PROMPT_SQL


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def build_schema_context(data_sources) -> str:
    lines = []
    for src in data_sources.sources:
        cols = ", ".join(src.columns)
        lines.append(f"TABLE {src.name} ({cols})")
    return "\n".join(lines)


def generate_sql_for_step(step, state: AnalyticsState, data_sources) -> str:
    llm = get_llm()
    schema_text = build_schema_context(data_sources)

    system_msg = SystemMessage(content=SYSTEM_PROMPT_SQL)
    user_msg = HumanMessage(
        content=(
            f"QUESTION:\n{state['question']}\n\n"
            f"ANALYSIS STEP:\n{step.description}\n\n"
            f"AVAILABLE TABLES:\n{schema_text}\n\n"
            "Return only the SQL query."
        )
    )
    response = llm.invoke([system_msg, user_msg])
    return response.content.strip()

def _is_file_backed_table(table_name: str) -> bool:
    """
    Determine if a table_name/location refers to a local CSV file.
    """
    if not table_name:
        return False
    # Common patterns we use in catalog/location
    return table_name.startswith("data/datasets/") or table_name.startswith("file://data/datasets/")

def build_schema_context(data_sources) -> str:
    lines = []
    for src in data_sources.sources:
        cols = ", ".join(src.columns)
        lines.append(f"TABLE {src.name} ({cols})")
    return "\n".join(lines)

def _load_dataframe_from_table_name(table_name: str) -> pd.DataFrame:
    """
    Load a pandas DataFrame for a file-backed dataset.
    Supports:
        - "data/datasets/xyz.csv"
        - "file://data/datasets/xyz.csv"
    """
    if table_name.startswith("file://"):
        path_str = table_name[len("file://") :]
    else:
        path_str = table_name

    path = Path(path_str)
    if not path.exists():
        raise FileNotFoundError(f"Dataset file not found at {path}")

    # Sample up to N rows to avoid huge memory usage for large files
    # You can tune this as needed.
    return pd.read_csv(path)  # you can add nrows=50000 if files are huge

def _infer_schema_roles(df: pd.DataFrame) -> Dict[str, Any]:
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    non_numeric_cols = [c for c in df.columns if c not in numeric_cols]

    dims = []
    for c in non_numeric_cols:
        nunique = df[c].nunique(dropna=True)
        if 1 < nunique <= 50:  # small enough to group by
            dims.append(c)

    return {"metrics": numeric_cols, "dimensions": dims}

def _analyze_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Run a basic analysis on a DataFrame:
    - summary statistics for all columns
    - top 10 rows as sample
    """
    result: Dict[str, Any] = {}

    # Summary stats
    try:
        summary = df.describe(include="all").T  # rows = columns, [web:97][web:103]
        result["summary"] = summary.reset_index().to_dict(orient="records")
    except Exception as e:
        result["summary_error"] = f"Failed to compute summary: {e}"

    # Sample rows
    try:
        sample = df.head(20)
        result["sample"] = sample.to_dict(orient="records")
    except Exception as e:
        result["sample_error"] = f"Failed to compute sample: {e}"

    # You can extend with simple group-bys later:
    # e.g., if "trip_distance" in df.columns: group by bins, etc. [web:92][web:94]
    roles = _infer_schema_roles(df)
    metrics = roles["metrics"]
    dims = roles["dimensions"]

    # Heuristic: pick first metric and first dimension when present
    if metrics and dims:
        metric = metrics[0]
        dim = dims[0]

        try:
            grouped = (
                df.groupby(dim)[metric]
                .agg(["count", "mean", "sum"])
                .reset_index()
                .sort_values("sum", ascending=False)
                .head(20)
            )
            result["groupby"] = {
                "dimension": dim,
                "metric": metric,
                "data": grouped.to_dict(orient="records"),
            }
        except Exception as e:
            result["groupby_error"] = f"Failed groupby on {dim},{metric}: {e}"

    return result


# ---------------------------------------------------------------------------
# Main execution nodes
# ---------------------------------------------------------------------------

def execution_agent_node(state: AnalyticsState) -> AnalyticsState:
    """
    Generate "queries" based on the analysis plan.

    For now, we treat each AnalysisStep as a pseudo-query description.
    """
    plan: AnalysisPlan = state.get("analysis_plan")

    if not plan or not plan.steps:
        state["error_state"] = "No analysis plan available"
        return log_state_transition(state, "failed", state["error_state"])

    queries: List[QueryExecutionRecord] = []

    for step in plan.steps:
        # In a real system, you'd render SQL from step.sql_template + context.
        # For now, we create a descriptive pseudo-query.
        description = step.description or "Analysis step"
        try:
            sql = generate_sql_for_step(step, state, state["available_data_sources"])
        except Exception as e:
            # fallback if LLM fails
            sql = step.sql_template or f"-- Pseudo query for: {description} (SQL generation failed: {e})"


        record = QueryExecutionRecord(
            step_number=step.step_number,
            description=description,
            sql=sql,
            executed=False,
            success=None,
            rows_returned=None,
            error_message=None,
        )
        queries.append(record)

    state["pending_queries"] = queries
    state = log_state_transition(
        state,
        "planning",
        f"Prepared {len(queries)} pseudo-queries for execution",
    )
    return state


def execute_queries_node(state: AnalyticsState) -> AnalyticsState:
    """
    Execute prepared queries or run file-based analysis for selected datasets.

    Behavior:
    - If any available_data_sources are file-backed (data/datasets/*.csv),
      load each and compute summary/sample via pandas.
    - Otherwise, simulate execution with mock metrics.
    """
    queries: List[QueryExecutionRecord] = state.get("pending_queries", [])
    data_sources = state.get("available_data_sources")

    if not data_sources or not data_sources.sources:
        state["error_state"] = "No data sources available for execution"
        return log_state_transition(state, "failed", state["error_state"])

    start_time = time.time()
    all_results: Dict[str, Any] = {}
    total_rows = 0
    execution_errors: List[str] = []

    # Determine which datasets are file-backed
    file_backed_sources = [
        s for s in data_sources.sources if _is_file_backed_table(s.table_name)
    ]

    # 1) File-backed datasets: real pandas analysis
    for source in file_backed_sources:
        try:
            df = _load_dataframe_from_table_name(source.table_name)
            analysis_result = _analyze_dataframe(df)
            all_results[source.name] = analysis_result
            total_rows += int(df.shape[0])
            state["execution_log"].append(
                f"[execute] Analyzed file dataset '{source.name}' with {df.shape[0]} rows"
            )
        except Exception as e:
            msg = f"Failed to analyze dataset '{source.name}': {e}"
            execution_errors.append(msg)
            state["execution_log"].append(f"[execute] {msg}")

    # 2) Non-file datasets: simulated execution
    non_file_sources = [
        s for s in data_sources.sources if s not in file_backed_sources
    ]
    if non_file_sources:
        # Simulate that each query returns some rows
        for q in queries:
            q.executed = True
            q.success = True
            q.rows_returned = 100  # dummy
        total_rows += len(non_file_sources) * 100
        state["execution_log"].append(
            f"[execute] Simulated execution for {len(non_file_sources)} warehouse datasets"
        )

    end_time = time.time()
    elapsed_ms = int((end_time - start_time) * 1000)

    # Build ExecutionResults object
    exec_results = ExecutionResults(
        queries_executed=queries,
        row_count=total_rows,
        execution_time_total_ms=elapsed_ms,
        success=len(execution_errors) == 0,
        errors=execution_errors,
        result_data=all_results,
    )

    state["execution_results"] = exec_results
    state["execution_errors"] = execution_errors

    if execution_errors:
        state["error_state"] = "; ".join(execution_errors)

    state = log_state_transition(
        state,
        "executing",
        f"Executed analysis on {len(data_sources.sources)} datasets "
        f"in {elapsed_ms}ms, total rows ~{total_rows}",
    )
    return state
