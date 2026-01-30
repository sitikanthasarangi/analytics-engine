"""
Execution Agent - Generates and executes queries against file-backed datasets.

For CSV datasets:
- Loads data into DuckDB (in-memory) and executes LLM-generated SQL directly.
- Falls back to pandas summary analysis if SQL execution fails.
For warehouse datasets:
- Simulates execution with mock results.
"""

import re
import time
from typing import List, Dict, Any
from pathlib import Path

import pandas as pd

try:
    import duckdb
    HAS_DUCKDB = True
except ImportError:
    HAS_DUCKDB = False

from state import (
    AnalyticsState,
    AnalysisPlan,
    ExecutionResults,
    QueryExecutionRecord,
    log_state_transition,
)
from data_manager import list_datasets
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
    # Strip markdown code fences if present
    sql = response.content.strip()
    sql = re.sub(r"^```(?:sql)?\s*", "", sql)
    sql = re.sub(r"\s*```$", "", sql)
    return sql.strip()


def _is_file_backed_table(table_name: str) -> bool:
    if not table_name:
        return False
    return table_name.startswith("data/datasets/") or table_name.startswith("file://data/datasets/")


def _load_dataframe_from_table_name(table_name: str) -> pd.DataFrame:
    if table_name.startswith("file://"):
        path_str = table_name[len("file://"):]
    else:
        path_str = table_name

    path = Path(path_str)
    if not path.exists():
        raise FileNotFoundError(f"Dataset file not found at {path}")

    return pd.read_csv(path)


def _infer_schema_roles(df: pd.DataFrame) -> Dict[str, Any]:
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    non_numeric_cols = [c for c in df.columns if c not in numeric_cols]

    dims = []
    for c in non_numeric_cols:
        nunique = df[c].nunique(dropna=True)
        if 1 < nunique <= 50:
            dims.append(c)

    return {"metrics": numeric_cols, "dimensions": dims}


def _analyze_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    """Run a basic summary analysis on a DataFrame as fallback."""
    result: Dict[str, Any] = {}

    try:
        summary = df.describe(include="all").T
        result["summary"] = summary.reset_index().to_dict(orient="records")
    except Exception as e:
        result["summary_error"] = f"Failed to compute summary: {e}"

    try:
        sample = df.head(20)
        result["sample"] = sample.to_dict(orient="records")
    except Exception as e:
        result["sample_error"] = f"Failed to compute sample: {e}"

    roles = _infer_schema_roles(df)
    metrics = roles["metrics"]
    dims = roles["dimensions"]

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


def _execute_sql_on_csvs(
    queries: List[QueryExecutionRecord],
    file_backed_sources: list,
    log: list,
) -> Dict[str, Any]:
    """
    Execute SQL queries against file-backed CSVs using DuckDB.
    Returns a dict with query results keyed by step description.
    """
    if not HAS_DUCKDB:
        return {}

    con = duckdb.connect(":memory:")
    registered_tables = {}

    # Register each CSV as a DuckDB table
    for source in file_backed_sources:
        try:
            df = _load_dataframe_from_table_name(source.table_name)
            # Register with the logical name the LLM knows about
            con.register(source.name, df)
            registered_tables[source.name] = df
            log.append(f"[execute] Registered table '{source.name}' ({df.shape[0]} rows, {df.shape[1]} cols)")
        except Exception as e:
            log.append(f"[execute] Failed to register '{source.name}': {e}")

    if not registered_tables:
        con.close()
        return {}

    sql_results: Dict[str, Any] = {}

    for q in queries:
        sql = q.sql
        if not sql or sql.startswith("--"):
            q.executed = True
            q.success = False
            q.error_message = "No valid SQL generated"
            continue

        try:
            result_df = con.execute(sql).fetchdf()
            q.executed = True
            q.success = True
            q.rows_returned = len(result_df)

            sql_results[f"step_{q.step_number}: {q.description}"] = {
                "sql": sql,
                "data": result_df.head(50).to_dict(orient="records"),
                "row_count": len(result_df),
                "columns": list(result_df.columns),
            }
            log.append(
                f"[execute] SQL step {q.step_number} returned {len(result_df)} rows"
            )
        except Exception as e:
            q.executed = True
            q.success = False
            q.error_message = str(e)
            log.append(f"[execute] SQL step {q.step_number} failed: {e}")

    con.close()
    return sql_results


# ---------------------------------------------------------------------------
# Main execution nodes
# ---------------------------------------------------------------------------

def execution_agent_node(state: AnalyticsState) -> AnalyticsState:
    """Generate SQL queries based on the analysis plan."""
    plan: AnalysisPlan = state.get("analysis_plan")

    if not plan or not plan.steps:
        state["error_state"] = "No analysis plan available"
        return log_state_transition(state, "failed", state["error_state"])

    queries: List[QueryExecutionRecord] = []

    for step in plan.steps:
        description = step.description or "Analysis step"
        try:
            sql = generate_sql_for_step(step, state, state["available_data_sources"])
        except Exception as e:
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
        f"Prepared {len(queries)} queries for execution",
    )
    return state


def execute_queries_node(state: AnalyticsState) -> AnalyticsState:
    """
    Execute prepared queries against file-backed datasets using DuckDB,
    plus run generic pandas analysis as supplementary context.
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

    file_backed_sources = [
        s for s in data_sources.sources if _is_file_backed_table(s.table_name)
    ]

    # 1) Execute actual SQL against CSVs via DuckDB
    if file_backed_sources and HAS_DUCKDB:
        sql_results = _execute_sql_on_csvs(
            queries, file_backed_sources, state["execution_log"]
        )
        if sql_results:
            all_results["query_results"] = sql_results
            for key, res in sql_results.items():
                total_rows += res.get("row_count", 0)

    # 2) Also run generic pandas analysis for summary context
    for source in file_backed_sources:
        try:
            df = _load_dataframe_from_table_name(source.table_name)
            analysis_result = _analyze_dataframe(df)
            all_results[source.name] = analysis_result
            total_rows += int(df.shape[0])
            state["execution_log"].append(
                f"[execute] Summary analysis for '{source.name}' with {df.shape[0]} rows"
            )
        except Exception as e:
            msg = f"Failed to analyze dataset '{source.name}': {e}"
            execution_errors.append(msg)
            state["execution_log"].append(f"[execute] {msg}")

    # 3) Non-file datasets: simulated execution
    non_file_sources = [
        s for s in data_sources.sources if s not in file_backed_sources
    ]
    if non_file_sources:
        for q in queries:
            if not q.executed:
                q.executed = True
                q.success = True
                q.rows_returned = 100
        total_rows += len(non_file_sources) * 100
        state["execution_log"].append(
            f"[execute] Simulated execution for {len(non_file_sources)} warehouse datasets"
        )

    end_time = time.time()
    elapsed_ms = int((end_time - start_time) * 1000)

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
