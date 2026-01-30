# Autonomous Analytics Recommendation Engine

A multi-agent system built with **LangGraph** that interprets natural language questions, executes SQL against your data, and returns direct answers with insights and visualizations.

## Architecture

```
User Question
    ↓
[Question Interpreter] → Parse intent, metrics, entities, time window
    ↓
[Data Advisor] → Select relevant datasets using enriched metadata
    ↓
[Analysis Planner] → Design multi-step SQL analysis plan
    ↓
[Execution Agent] → Generate SQL from plan
    ↓
[Execute Queries] → Run SQL via DuckDB against CSV datasets
    ↓
[Answer Synthesizer] → Produce a direct natural-language answer
    ↓
[Insight Generator] → Extract patterns, trends, anomalies
    ↓
[Visualization Agent] → Recommend chart types for the data
    ↓
[Confidence & Guardrails] → Add caveats, confidence scores
    ↓
Final Output (Answer, Tables, Charts, Insights, Caveats)
```

Generic questions (e.g. "what can you do?") are routed to a **Capabilities Helper** that skips the analysis pipeline.

## Features

- **Direct answers** — asks a question, gets a plain-English answer backed by query results
- **DuckDB SQL execution** — LLM-generated SQL runs against CSV files loaded into DuckDB
- **Smart dataset selection** — enriched metadata (column types, roles, sample values, descriptions) lets the advisor pick the right dataset automatically
- **Manual dataset selection** — UI widget to explicitly choose which datasets to analyze
- **Interactive Streamlit UI** — upload CSVs, register datasets, run analyses, view results and charts
- **Plotly charts** with `st.bar_chart` fallback when Plotly is unavailable
- **Robust JSON parsing** — handles markdown-fenced LLM responses gracefully
- **Pydantic state models** — typed state flows through the LangGraph with validation
- **Confidence guardrails** — every result includes caveats and quality flags

## Project Structure

```
analytics-engine/
├── main.py                  # Entry point (run_analysis)
├── config.py                # LLM config, API keys, model settings
├── state.py                 # Pydantic models & AnalyticsState TypedDict
├── graph.py                 # LangGraph state machine wiring
├── data_manager.py          # Dataset catalog (register, list, lookup)
├── ui_streamlit.py          # Streamlit web UI
├── agents/
│   ├── question_interpreter.py
│   ├── capabilities_helper.py
│   ├── data_advisor.py
│   ├── analysis_planner.py
│   ├── execution_agent.py   # SQL generation + DuckDB execution
│   ├── answer_synthesizer.py
│   ├── insight_generator.py
│   ├── visualization_agent.py
│   └── confidence_guardrails.py
├── data/
│   ├── catalog.json         # Dataset registry with metadata
│   └── datasets/            # Uploaded CSV files
└── requirements.txt
```

## Setup

```bash
git clone https://github.com/sitikanthasarangi/analytics-engine.git
cd analytics-engine
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file with your API key:

```
OPENAI_API_KEY=sk-...
# or ANTHROPIC_API_KEY / GOOGLE_API_KEY depending on config.py
```

## Running

### Streamlit UI
```bash
streamlit run ui_streamlit.py
```

### CLI
```bash
python main.py
```

## How It Works

1. **Upload a CSV** via the sidebar and register it with a logical name. The system auto-generates column metadata (types, roles, min/max, sample values, cardinality).

2. **Ask a question** like *"Which pickup locations had the highest average fare?"*

3. The **interpreter** extracts intent, metrics, entities, and time window.

4. The **data advisor** matches your question against dataset metadata to select relevant sources (or uses your manual selection).

5. The **planner** designs a multi-step SQL analysis plan.

6. The **execution agent** generates SQL for each step. **DuckDB** executes the SQL against CSV data loaded as in-memory tables.

7. The **answer synthesizer** reads query results and produces a direct answer.

8. **Insights**, **visualizations**, and **confidence metrics** are generated from the results.

## Tech Stack

- **LangGraph** — multi-agent state machine orchestration
- **LangChain** — LLM integration (OpenAI, Anthropic, Google)
- **DuckDB** — in-process SQL execution on CSV data
- **Pydantic** — typed state validation
- **Streamlit** — interactive web UI
- **Plotly** — chart rendering
- **Pandas** — data manipulation

## License

MIT
