# Autonomous Analytics Recommendation Engine
**LangGraph-based Multi-Agent System for Intelligent Data Analysis & Insights**

## Overview
This is a production-ready multi-agent orchestration system that automates analytics workflows. It interprets natural language questions, plans analyses, executes queries, generates insights, and builds visualizations—mimicking how professional data analysts work.

### Architecture
```
User Question
    ↓
[Question Interpreter] → Understand intent & translate to data terms
    ↓
[Data Advisor] → Validate available sources & flag quality issues
    ↓
[Analysis Planner] → Design multi-step analysis approach
    ↓
[Execution Agent] → Generate & run SQL/Spark queries (with approval gate)
    ↓
[Insight Generator] → Analyze results for patterns & anomalies
    ↓
[Visualization Agent] → Create appropriate charts & dashboards
    ↓
[Confidence & Guardrails] → Add disclaimers, uncertainty flags
    ↓
Final Analytics Package (SQL, Insights, Visualizations, Caveats)
```

## Key Features
- **Question Interpretation**: NLP-based intent recognition
- **Data Source Validation**: Knows available tables, granularity, reliability
- **Intelligent Planning**: Multi-step analysis design
- **Safe Execution**: Human-in-the-loop approval for queries
- **Insight Generation**: Pattern detection, trend analysis, anomaly flagging
- **Visualization**: Chart type selection & dashboard generation
- **Confidence Metrics**: Uncertainty quantification & guardrails
- **Stateful Orchestration**: LangGraph-based state management with checkpointing

## Directory Structure
```
analytics-engine/
├── main.py                 # Entry point & CLI
├── config.py               # Configuration, API keys, model settings
├── state.py                # State schema & type definitions
├── agents/
│   ├── __init__.py
│   ├── question_interpreter.py
│   ├── data_advisor.py
│   ├── analysis_planner.py
│   ├── execution_agent.py
│   ├── insight_generator.py
│   ├── visualization_agent.py
│   └── confidence_guardrails.py
├── graph.py                # LangGraph state machine definition
├── db_connector.py         # Database connection & query execution
├── utils.py                # Helper functions
├── examples/
│   ├── example_queries.txt
│   └── sample_schema.sql
├── tests/
│   └── test_integration.py
├── .env.example            # Environment variables template
├── README.md               # This file
└── requirements.txt        # Python dependencies
```

## Installation & Setup

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/analytics-engine.git
cd analytics-engine
```

### 2. Create Virtual Environment
```bash
python3.10 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
```bash
cp .env.example .env
# Edit .env with your:
# - OpenAI API key (or Anthropic)
# - Database connection string
# - Data warehouse connection (Databricks/Snowflake/BigQuery)
# - LangChain API key (for debugging)
```

### 5. Run the System
```bash
python main.py
```

## Usage Examples

### Example 1: Revenue Analysis
```
Question: "Why did our revenue drop 15% last quarter?"

Flow:
1. Interpreter: Extracts intent → "Revenue trend analysis + Root cause investigation"
2. Data Advisor: Validates revenue tables, customer tables, product tables exist
3. Planner: "Compare current vs prior quarter, segment by geography/product/channel"
4. Executor: Runs aggregation queries (human approves SQL)
5. Insight Generator: Identifies largest drop is in EMEA region, automotive products
6. Visualizer: Creates comparison charts + drill-down dashboard
7. Guardrails: "Based on 90 days data. 5% confidence interval. Potential data quality issue in APAC."
```

### Example 2: Product Performance
```
Question: "Which products are underperforming?"

Flow:
1. Interpreter: "Product performance ranking"
2. Data Advisor: Locates product sales, profitability, customer acquisition data
3. Planner: "Calculate growth rate, profit margin, customer cohort analysis"
4. Executor: Generates comparative analysis (approved by user)
5. Insight Generator: Finds 3 products with declining adoption + decreasing margins
6. Visualizer: Creates heat map + trend lines
7. Guardrails: "Analysis excludes new products <3 months old. Limited sample size for LATAM region."
```

### Example 3: Cost Anomaly (Multi-Agent Coordination)
```
Question: "Our operational costs spiked last week. What happened?"

Flow:
1. Interpreter: "Cost trend analysis + Anomaly detection"
2. Data Advisor: Identifies cost ledger, resource usage tables; flags data freshness
3. Planner: "Time-series analysis, compare to baseline, segment by cost center"
4. Executor: Retrieves cost data + compares to moving average (user reviews)
5. Insight Generator: Identifies spike in cloud infrastructure costs, specific to ML training
6. Visualizer: Time-series chart with anomaly highlighted + drill-down by cost center
7. Guardrails: "Based on 30 days historical data. May be noisy. Recommend manual review of infrastructure changes."
```

## Architecture Details

### State Machine (LangGraph)
The system uses a stateful graph where:
- **State**: Accumulates question context, available data sources, analysis plan, execution results, insights, visualizations, and confidence metrics
- **Nodes**: Each agent is a node that receives state, processes, and returns updated state
- **Edges**: Sequential flow + conditional routing (e.g., "Did execution fail? Route to error handler")
- **Checkpointing**: Human-in-the-loop approval before executing queries

### Agent Responsibilities

| Agent | Purpose | Input | Output |
|-------|---------|-------|--------|
| **Question Interpreter** | Understand user intent | Raw question | Structured intent: `{"task": "...", "entities": [...], "metrics": [...]}` |
| **Data Advisor** | Validate data sources | Intent, available schema | `{"tables": [...], "confidence": 0.9, "warnings": [...]}` |
| **Analysis Planner** | Design approach | Intent + Data sources | `{"steps": [...], "queries_needed": N, "estimated_time": "..."}` |
| **Execution Agent** | Run queries | Plan + Approval | Query results + execution logs |
| **Insight Generator** | Find patterns | Results | `{"insights": [...], "anomalies": [...], "confidence": 0.85}` |
| **Visualization Agent** | Create charts | Insights + Data | Chart configs + dashboard definition |
| **Confidence & Guardrails** | Quantify uncertainty | All upstream outputs | Disclaimers + uncertainty bounds |

### Human-in-the-Loop Pattern
Before executing queries, the graph pauses and presents:
```
📊 ANALYSIS PLAN SUMMARY
────────────────────────
Task: Revenue trend analysis + Root cause investigation
Data Sources: revenue_fact, customer_dim, product_dim
Planned SQL Queries: 3
Estimated Execution Time: 45 seconds

PROPOSED QUERIES:
1. SELECT DATE, SUM(revenue) FROM revenue_fact WHERE date > '2024-01-01' GROUP BY DATE
2. SELECT product_category, SUM(revenue) FROM revenue_fact...
...

[APPROVE] [MODIFY PLAN] [CANCEL]
```

User can approve, modify plan, or cancel before any data is queried.

## Implementation Highlights

### 1. Type-Safe State Management (Pydantic + LangGraph)
```python
# Ensures all state transitions are validated
class AnalyticsState(TypedDict):
    question: str
    interpreted_intent: Optional[Intent]
    available_data_sources: Optional[DataSources]
    analysis_plan: Optional[AnalysisPlan]
    execution_results: Optional[QueryResults]
    insights: Optional[List[Insight]]
    visualizations: Optional[List[Visualization]]
    confidence_assessment: Optional[ConfidenceMetrics]
```

### 2. Agent Pattern (LLM + Tools)
Each agent uses an LLM (GPT-4 or Claude) plus specialized tools:
```python
# Question Interpreter Agent
tools = [
    extract_entities_tool,
    identify_metrics_tool,
    detect_time_periods_tool,
]
agent = create_tool_calling_agent(llm, tools, prompt)
```

### 3. Safe Query Execution
```python
# Before executing user-approved queries:
1. Validate SQL syntax (SQLparse)
2. Check for dangerous patterns (DELETE, DROP)
3. Add LIMIT to prevent runaway queries
4. Log all executed statements
5. Timeout protection (30s default)
```

### 4. Insight Generation Strategy
```python
# Pattern Detection:
- Time-series trend analysis
- Segment-level comparison
- Anomaly detection (Z-score + IQR)
- Correlation analysis
- Growth rate calculation

# Output: Human-readable insights
"Revenue in EMEA dropped 23% QoQ, driven by automotive segment (-31%) and 
 travel segment (-18%). This contrasts with APAC growth of 12% and LATAM 
 of 8%. Confidence: 85% (based on 90 days data)."
```

### 5. Visualization Intelligence
System selects chart types based on data:
- **Time-series** → Line chart with confidence intervals
- **Comparison** → Bar chart with sorting
- **Distribution** → Histogram + box plot
- **Correlation** → Scatter plot
- **Categorical breakdown** → Stacked bar + drill-down
- **Hierarchical** → Sunburst or tree map

## Development Workflow

### Running Locally
```bash
# Start interactive CLI
python main.py

# Ask a question:
> What drove our revenue changes last quarter?

# Monitor execution:
[Interpreter] Analyzing: "revenue changes last quarter" → Intent: REVENUE_TREND_ANALYSIS
[Data Advisor] Found: revenue_fact, customer_dim, product_dim (confidence: 0.95)
[Planner] Designed 4-step analysis plan
[Executor] Generated 3 SQL queries - AWAITING YOUR APPROVAL

[Present queries for human review...]

[User approves]

[Executor] Query 1/3 executed (0.3s)
[Executor] Query 2/3 executed (0.5s)
[Executor] Query 3/3 executed (0.4s)
[Insight Generator] Found 5 insights + 2 anomalies
[Visualizer] Generated 3 charts
[Guardrails] Confidence: 88%, Disclaimers: 3
```

### Testing
```bash
# Run test suite
pytest tests/ -v

# Test specific agent
python tests/test_integration.py TestQuestionInterpreter -v

# Run with sample data
python main.py --demo
```

### Debugging
```bash
# Enable verbose logging
python main.py --verbose

# Stream graph execution
python main.py --debug-graph

# Export execution trace
python main.py --trace output.json
```

## Extensibility

### Adding a Custom Data Source
```python
# agents/data_advisor.py
class DataSource:
    name: str
    connector_type: str  # "databricks", "snowflake", "postgres"
    tables: List[str]
    quality_score: float

# Register new source
register_data_source(
    name="warehouse_bigquery",
    connector=BigQueryConnector(),
    tables=["events", "users", "products"],
    quality_score=0.92
)
```

### Adding a Custom Insight Pattern
```python
# agents/insight_generator.py
class CustomInsightDetector(InsightDetector):
    def detect(self, results: QueryResults) -> List[Insight]:
        # Your custom pattern recognition logic
        pass

insight_engine.register_detector(CustomInsightDetector())
```

### Adding a Visualization Type
```python
# agents/visualization_agent.py
class CustomChart(Chart):
    chart_type = "waterfall"
    
    def render(self, data: pd.DataFrame) -> dict:
        # Generate chart config
        pass

visualizer.register_chart(CustomChart())
```

## Production Deployment

### Option 1: FastAPI Server
```python
# Serve via REST API
from fastapi import FastAPI
app = FastAPI()

@app.post("/analyze")
async def analyze(question: str, user_id: str):
    # Runs graph with checkpointing
    # Streams results back
    pass
```

### Option 2: LangGraph Platform
```python
# Deploy to LangGraph Cloud (coming soon)
graph.deploy(
    name="analytics-engine",
    production=True,
    checkpointing=PostgreSQLSaver(),  # Persistent state
)
```

### Option 3: Databricks Jobs
```python
# Run as Databricks Job
%run ./main.py analyze --question "revenue trends" --output gs://bucket/results.json
```

## Monitoring & Observability

### Metrics Tracked
- Query execution time
- LLM token usage (cost attribution)
- Insight confidence scores
- User approval rates (% of plans approved without modification)
- Error rates by agent

### Logging
```
[2025-01-26 17:32:15] QUESTION_RECEIVED: "Why did costs spike?"
[2025-01-26 17:32:18] INTERPRETATION_COMPLETE: intent=ANOMALY_ANALYSIS
[2025-01-26 17:32:25] DATA_VALIDATION_COMPLETE: sources=3, confidence=0.92
[2025-01-26 17:32:28] PLAN_READY: steps=5, queries=4
[2025-01-26 17:32:28] AWAITING_APPROVAL: query_count=4, estimated_runtime=45s
[2025-01-26 17:32:35] USER_APPROVED
[2025-01-26 17:32:40] EXECUTION_COMPLETE: time=5.2s, results=1240 rows
[2025-01-26 17:32:45] INSIGHTS_GENERATED: count=6, anomalies=2
[2025-01-26 17:32:50] VISUALIZATION_COMPLETE: charts=3
[2025-01-26 17:32:51] RESPONSE_DELIVERED: confidence=0.88
```

## Troubleshooting

### Common Issues

**Issue**: "No data sources available"
- Check database connection in `.env`
- Verify schema discovery: `python utils.py --discover-schema`

**Issue**: "Query execution timeout"
- Increase timeout in `config.py`: `QUERY_TIMEOUT = 60`
- Check database performance

**Issue**: "Low confidence in insights"
- May indicate insufficient data. Check time window
- Planner suggested wrong analysis type

### Getting Help
- Docs: `/docs` (generated from docstrings)
- Issues: GitHub Issues
- Slack: [LangChain Community]

## Roadmap

### Phase 1 (Current)
- ✅ Core multi-agent orchestration
- ✅ Human-in-the-loop approval
- ✅ Basic insight generation
- ✅ Visualization generation

### Phase 2 (Q2 2026)
- [ ] Real-time streaming analytics
- [ ] Multi-database federation
- [ ] Advanced ML-based anomaly detection
- [ ] Natural language visualization descriptions

### Phase 3 (Q3 2026)
- [ ] Collaborative analytics (multiple users)
- [ ] Hypothesis testing automation
- [ ] Causal inference patterns
- [ ] Custom metric libraries

## Contributing
See `CONTRIBUTING.md` for development guidelines.

## License
MIT License - See `LICENSE` for details.

## Citation
If you use this in research/production, please cite:
```
@software{analytics_engine_2026,
  author = {Your Name},
  title = {Autonomous Analytics Recommendation Engine},
  year = {2026},
  url = {https://github.com/yourusername/analytics-engine}
}
```

## Credits
Built with [LangChain](https://langchain.com), [LangGraph](https://github.com/langchain-ai/langgraph), and [OpenAI](https://openai.com).
