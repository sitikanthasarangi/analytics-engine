import streamlit as st
from state import state_to_dict
from main import run_analysis
from data_manager import list_datasets, register_dataset, DATASETS_DIR
import pandas as pd
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
    schema = {
        "columns": list(df.columns),
        "rows": int(df.shape[0]),
        "primary_keys": [],  # user can edit later if needed
        "quality_score": 0.9,
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

run_button = st.button("Run Analysis")

if run_button and question.strip():
    with st.spinner("Running multi-agent analysis..."):
        state = run_analysis(question.strip(), user_id=user_id)

    if not state:
        st.error("Analysis failed. Check server logs.")
    else:
        s = state  # shorthand

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
