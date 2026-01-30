import streamlit as st
from state import state_to_dict
from main import run_analysis
from data_manager import list_datasets, register_dataset, DATASETS_DIR
import pandas as pd
try:
    import plotly.express as px
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False
from pathlib import Path
from agents.data_advisor import AVAILABLE_DATA_SOURCES  # static ones (optional)
from data_manager import list_datasets, register_dataset, DATASETS_DIR


st.set_page_config(page_title="Analytics Assistant", page_icon="📊", layout="wide")

st.title("📊 Autonomous Analytics Recommendation Engine")

st.sidebar.header("Datasets")
user_id = st.sidebar.text_input("User ID", value="user-1")

# 1) Show static sources (from AVAILABLE_DATA_SOURCES)
if AVAILABLE_DATA_SOURCES:
    st.sidebar.subheader("Built-in sources")
    for name, meta in AVAILABLE_DATA_SOURCES.items():
        st.sidebar.markdown(f"- `{name}` → `{meta['table']}`")

# 2) Show user datasets
st.sidebar.header("Datasets")

datasets = list_datasets()
if not datasets:
    st.sidebar.caption("No datasets yet. Upload a CSV below.")
else:
    for ds in datasets:
        cols = ds.get("schema", {}).get("columns", [])
        st.sidebar.markdown(
            f"- `{ds['name']}` ({len(cols)} columns) → `{ds.get('location')}`"
        )

st.sidebar.subheader("Upload dataset")
uploaded = st.sidebar.file_uploader(
    "Upload CSV",
    type=["csv"],
    help="CSV only for now. It will be saved under data/datasets/.",
)

if uploaded is not None:
    # Save file
    DATASETS_DIR.mkdir(parents=True, exist_ok=True)
    target_path = DATASETS_DIR / uploaded.name
    with open(target_path, "wb") as f:
        f.write(uploaded.getbuffer())

    # Infer basic schema
    df = pd.read_csv(target_path, nrows=500)  # sample for speed
    columns = list(df.columns)
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    categorical_cols = [c for c in columns if c not in numeric_cols]

    # Build per-column metadata
    column_meta = {}
    for c in columns:
        info = {"dtype": str(df[c].dtype)}
        if c in numeric_cols:
            info["role"] = "metric"
            info["min"] = float(df[c].min()) if df[c].notna().any() else None
            info["max"] = float(df[c].max()) if df[c].notna().any() else None
        else:
            info["role"] = "dimension"
            info["n_unique"] = int(df[c].nunique())
            info["sample_values"] = df[c].dropna().unique()[:5].tolist()
        column_meta[c] = info

    # Auto-generate a human-readable description from the columns
    description = f"Dataset with {len(columns)} columns ({len(numeric_cols)} numeric, {len(categorical_cols)} categorical). Columns: {', '.join(columns[:15])}"

    schema = {
        "columns": columns,
        "rows": int(df.shape[0]),
        "primary_keys": [],  # user can edit later if needed
        "quality_score": 0.9,
        "column_metadata": column_meta,
        "description": description,
    }

    logical_name = st.sidebar.text_input(
        "Logical name for this dataset", value=uploaded.name.rsplit(".", 1)[0]
    )

    if st.sidebar.button("Register dataset"):
        register_dataset(logical_name, uploaded.name, schema)
        st.sidebar.success(f"Registered dataset '{logical_name}'")
        st.rerun()

# Main question input

default_question = "What were our top products last month?"

question = st.text_area(
    "Ask an analytics question:",
    value=default_question,
    height=100,
    help="Examples: 'Why did revenue drop last quarter?' or 'Which regions underperformed?'",
)

# Dataset selector
dataset_names = [ds["name"] for ds in list_datasets()]
selected_datasets = st.multiselect(
    "Select dataset(s) to analyze:",
    options=dataset_names,
    default=None,
    help="Leave empty to let the engine auto-detect relevant datasets.",
)

run_button = st.button("Run Analysis")

if run_button and question.strip():
    with st.spinner("Running multi-agent analysis..."):
        state = run_analysis(
            question.strip(),
            user_id=user_id,
            selected_datasets=selected_datasets if selected_datasets else None,
        )

    if not state:
        st.error("Analysis failed. Check server logs.")
    else:
        s = state  # shorthand

        # Direct answer — show first and prominently
        if s.get("direct_answer"):
            st.subheader("💬 Answer")
            st.markdown(s["direct_answer"])
            st.divider()

        # Query results tables (from DuckDB SQL execution)
        if s.get("execution_results") and s["execution_results"].result_data:
            qr = s["execution_results"].result_data.get("query_results")
            if qr:
                st.subheader("🔍 Query Results")
                for step_key, step_result in qr.items():
                    with st.expander(step_key, expanded=True):
                        if step_result.get("data"):
                            st.dataframe(pd.DataFrame(step_result["data"]))
                        else:
                            st.caption("No rows returned.")
                        st.code(step_result.get("sql", ""), language="sql")

        # Show interpreted intent
        if s.get("interpreted_intent"):
            intent = s["interpreted_intent"]
            st.subheader("🔎 Interpreted Intent")
            st.write(
                {
                    "task_type": intent.task_type,
                    "metrics": intent.metrics,
                    "entities": intent.entities,
                    "time_window": intent.time_window,
                    "segments": intent.segments,
                    "confidence": intent.confidence,
                }
            )

        # Data sources
        if s.get("available_data_sources"):
            ds = s["available_data_sources"]
            st.subheader("🗄️ Data Sources")
            st.write(
                {
                    "total_sources": ds.total_sources,
                    "coverage_score": ds.coverage_score,
                    "warnings": ds.warnings,
                }
            )
            with st.expander("View sources"):
                st.write([src.model_dump() for src in ds.sources])

        # Analysis plan
        if s.get("analysis_plan"):
            plan = s["analysis_plan"]
            st.subheader("📋 Analysis Plan")
            st.write(
                {
                    "total_steps": plan.total_steps,
                    "estimated_runtime_seconds": plan.estimated_runtime_seconds,
                    "warnings": plan.warnings,
                }
            )
            with st.expander("View steps"):
                st.write([step.model_dump() for step in plan.steps])

        # Execution results
        if s.get("execution_results"):
            res = s["execution_results"]
            if res.result_data:
                for ds_name, ds_result in res.result_data.items():
                    st.subheader(f"📊 Dataset: {ds_name}")

                    if "summary" in ds_result:
                        st.markdown("**Summary statistics**")
                        st.dataframe(pd.DataFrame(ds_result["summary"]))

                    if "groupby" in ds_result:
                        gb = ds_result["groupby"]
                        st.markdown(
                            f"**Top {gb['dimension']} by {gb['metric']} (sum, mean, count)**"
                        )
                        st.dataframe(pd.DataFrame(gb["data"]))

                    if "sample" in ds_result:
                        with st.expander("Sample rows"):
                            st.dataframe(pd.DataFrame(ds_result["sample"]))


        # Rendered charts from execution data
        if s.get("execution_results") and s["execution_results"].result_data:
            st.subheader("📈 Visualizations")
            for ds_name, ds_result in s["execution_results"].result_data.items():
                if "groupby" in ds_result:
                    gb = ds_result["groupby"]
                    gb_df = pd.DataFrame(gb["data"])
                    dim, metric = gb["dimension"], gb["metric"]

                    if dim in gb_df.columns and "sum" in gb_df.columns:
                        chart_df = gb_df.head(15)
                        if HAS_PLOTLY:
                            fig = px.bar(
                                chart_df, x=dim, y="sum",
                                title=f"{metric} (sum) by {dim} — {ds_name}",
                                labels={"sum": f"{metric} (sum)", dim: dim},
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.markdown(f"**{metric} (sum) by {dim} — {ds_name}**")
                            st.bar_chart(chart_df.set_index(dim)["sum"])

                    if dim in gb_df.columns and "mean" in gb_df.columns:
                        chart_df = gb_df.head(15)
                        if HAS_PLOTLY:
                            fig = px.bar(
                                chart_df, x=dim, y="mean",
                                title=f"{metric} (mean) by {dim} — {ds_name}",
                                labels={"mean": f"{metric} (mean)", dim: dim},
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.markdown(f"**{metric} (mean) by {dim} — {ds_name}**")
                            st.bar_chart(chart_df.set_index(dim)["mean"])

                # Summary: mean values per column
                if "summary" in ds_result:
                    summary_df = pd.DataFrame(ds_result["summary"])
                    if "mean" in summary_df.columns and "index" in summary_df.columns:
                        numeric_summary = summary_df.dropna(subset=["mean"]).head(12)
                        if not numeric_summary.empty:
                            if HAS_PLOTLY:
                                fig = px.bar(
                                    numeric_summary, x="index", y="mean",
                                    title=f"Mean values by column — {ds_name}",
                                    labels={"index": "Column", "mean": "Mean"},
                                    color_discrete_sequence=["#EF553B"],
                                )
                                st.plotly_chart(fig, use_container_width=True)
                            else:
                                st.markdown(f"**Mean values by column — {ds_name}**")
                                st.bar_chart(numeric_summary.set_index("index")["mean"])

        # Insights
        if s.get("insights"):
            st.subheader("💡 Insights")
            for ins in s["insights"]:
                st.markdown(
                    f"- **{ins.finding}**  \n"
                    f"  Metric: `{ins.metric}`, Magnitude: `{ins.magnitude}`, "
                    f"Confidence: `{ins.confidence:.0%}`, Impact: `{ins.business_impact}`"
                )
        # If it was a generic question, show capabilities text nicely
        intent = s.get("interpreted_intent")
        if intent and getattr(intent, "is_generic", False):
            st.subheader("ℹ️ Capabilities")
            for line in s.get("execution_log", []):
                if line.startswith("[capabilities]"):
                    st.markdown(line.replace("[capabilities] ", "").replace("\n", "  \n"))


        # Anomalies
        if s.get("anomalies"):
            st.subheader("⚠️ Anomalies")
            for an in s["anomalies"]:
                st.markdown(
                    f"- [{an.severity.upper()}] {an.description} "
                    f"(metric: `{an.affected_metric}`, magnitude: `{an.magnitude}`, "
                    f"confidence: `{an.confidence:.0%}`)"
                )

        # Confidence assessment
        if s.get("confidence_assessment"):
            conf = s["confidence_assessment"]
            st.subheader("🎯 Confidence Assessment")
            st.write(
                {
                    "overall_confidence": conf.overall_confidence,
                    "data_freshness": conf.data_freshness,
                    "sample_size_adequate": conf.sample_size_adequate,
                    "completeness_score": conf.completeness_score,
                }
            )
            if conf.caveats:
                st.markdown("**Caveats:**")
                for c in conf.caveats:
                    st.markdown(f"- {c}")

        # Execution log
        if s.get("execution_log"):
            with st.expander("📝 Execution Log"):
                for line in s["execution_log"]:
                    st.code(line)
