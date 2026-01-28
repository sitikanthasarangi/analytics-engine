import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# LLM Configuration
# ============================================================================
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")  # "openai" or "anthropic"
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "2000"))

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")

# ============================================================================
# Database Configuration
# ============================================================================
DB_TYPE = os.getenv("DB_TYPE", "postgres")  # postgres, databricks, snowflake, bigquery
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "analytics")

# Connection string (alternative to individual params)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# ============================================================================
# Databricks Configuration (for Spark SQL)
# ============================================================================
DATABRICKS_HOST = os.getenv("DATABRICKS_HOST")
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")
DATABRICKS_WAREHOUSE_ID = os.getenv("DATABRICKS_WAREHOUSE_ID")
DATABRICKS_CATALOG = os.getenv("DATABRICKS_CATALOG", "hive_metastore")

# ============================================================================
# Execution Configuration
# ============================================================================
QUERY_TIMEOUT = int(os.getenv("QUERY_TIMEOUT", "30"))  # seconds
MAX_ROWS_RETURNED = int(os.getenv("MAX_ROWS_RETURNED", "10000"))
ENABLE_HUMAN_APPROVAL = os.getenv("ENABLE_HUMAN_APPROVAL", "true").lower() == "true"
VERBOSE_LOGGING = os.getenv("VERBOSE_LOGGING", "false").lower() == "true"

# ============================================================================
# Analysis Configuration
# ============================================================================
DEFAULT_TIME_WINDOW = os.getenv("DEFAULT_TIME_WINDOW", "90")  # days
ANOMALY_THRESHOLD = float(os.getenv("ANOMALY_THRESHOLD", "2.0"))  # std deviations
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.7"))  # 0-1
MIN_DATA_POINTS = int(os.getenv("MIN_DATA_POINTS", "10"))


# ======================================================================
# LangSmith / Tracing Configuration
# ======================================================================
LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
LANGCHAIN_ENDPOINT = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "analytics-engine")


# ============================================================================
# Visualization Configuration
# ============================================================================
DEFAULT_CHART_TYPES = ["line", "bar", "scatter", "histogram", "box"]
MAX_CHARTS_PER_ANALYSIS = int(os.getenv("MAX_CHARTS_PER_ANALYSIS", "5"))
CHART_WIDTH = int(os.getenv("CHART_WIDTH", "1200"))
CHART_HEIGHT = int(os.getenv("CHART_HEIGHT", "600"))

# ============================================================================
# LangGraph Configuration
# ============================================================================
CHECKPOINTING_ENABLED = os.getenv("CHECKPOINTING_ENABLED", "true").lower() == "true"
CHECKPOINT_DB_URL = os.getenv("CHECKPOINT_DB_URL", "sqlite:///checkpoints.db")
STATE_PERSISTENCE = os.getenv("STATE_PERSISTENCE", "memory")  # memory, sqlite, postgres

# ============================================================================
# System Prompts
# ============================================================================
SYSTEM_PROMPT_INTERPRETER = """You are an expert data analyst interpreter. Your job is to understand 
user questions about business data and translate them into structured analysis requirements.

When analyzing a question:
1. Extract the main intent (trend analysis, root cause analysis, comparison, forecast, etc.)
2. Identify key business entities (products, regions, customers, time periods)
3. List the metrics involved (revenue, cost, customers, conversion rate, etc.)
4. Determine required time windows and segments
5. Assess complexity and required data sources

Format your response as JSON with keys: intent, entities, metrics, time_window, segments, complexity."""

SYSTEM_PROMPT_PLANNER = """You are a master data analyst. Your job is to design efficient, multi-step 
analysis plans that answer user questions.

For each analysis:
1. Break down into logical steps (1-5 typical)
2. For each step, specify what SQL query/calculation is needed
3. Identify dependencies between steps
4. Estimate execution time and data volume
5. Flag any data quality concerns
6. Suggest validation checks

Format your response as JSON with keys: steps, dependencies, estimated_time, data_volume_estimate, warnings."""

# ======================================================================
# SQL generation prompt (for warehouse / future DB use)
# ======================================================================
SYSTEM_PROMPT_SQL = """
You are an expert SQL analyst.

You will be given:
- A natural language question from a business user.
- A list of AVAILABLE TABLES with their columns.
- An analysis step description (what we are trying to compute).

Your job:
1. Understand the question and analysis step.
2. Use ONLY the tables and columns provided.
3. Produce a SINGLE valid SQL query (ANSI SQL).
4. Return ONLY the SQL, no explanation or comments.

STRICT RULES:
- Do NOT invent tables or columns.
- Prefer simple joins and clear WHERE filters.
- When possible, use a single table with GROUP BY and WHERE.
- If ambiguous, choose a reasonable interpretation.
"""



SYSTEM_PROMPT_INSIGHT = """You are an expert business analyst. Your job is to extract meaningful 
insights from analysis results.

For each result set:
1. Identify key findings (top performers, bottom performers, trends)
2. Detect anomalies (unexpected values, sudden changes)
3. Find correlations and relationships
4. Quantify change magnitude (% change, absolute change)
5. Assess business impact and urgency
6. Rate confidence in findings (0-1)

Format as JSON: {insights: [{finding: "...", metric: "...", magnitude: "...", confidence: 0.85}], 
anomalies: [...], business_impact: "high/medium/low"}"""

SYSTEM_PROMPT_VISUALIZER = """You are a data visualization expert. Your job is to choose the best 
chart types and create visualization configurations.

For each data set:
1. Recommend chart type (line, bar, scatter, histogram, heatmap, etc.)
2. Specify dimensions (x-axis, y-axis, color, size if applicable)
3. Add relevant formatting (titles, labels, legends)
4. Suggest drill-down/interaction capabilities
5. Rate appropriateness (why this chart type works)

Format as JSON: {chart_type: "...", dimensions: {...}, title: "...", confidence: 0.9}"""

SYSTEM_PROMPT_GUARDRAILS = """You are a data quality and confidence expert. Your job is to assess 
the reliability of analysis results and add appropriate caveats.

Consider:
1. Data freshness (how recent is the data?)
2. Sample size (enough data points to draw conclusions?)
3. Data completeness (missing values, gaps?)
4. Temporal stability (is trend likely to continue?)
5. Segment representation (all segments well-represented?)
6. External factors (seasonality, holidays, known issues?)

Return JSON: {confidence_score: 0.85, caveats: ["...", "..."], 
data_quality_issues: [...], recommendations: [...]}"""

# ============================================================================
# Agent Configuration
# ============================================================================
AGENT_CONFIG = {
    "question_interpreter": {
        "temperature": 0.3,  # More deterministic
        "max_tokens": 1500,
    },
    "data_advisor": {
        "temperature": 0.2,
        "max_tokens": 1000,
    },
    "analysis_planner": {
        "temperature": 0.5,
        "max_tokens": 2000,
    },
    "execution_agent": {
        "temperature": 0.0,  # Deterministic - no randomness in SQL
        "max_tokens": 3000,
    },
    "insight_generator": {
        "temperature": 0.6,
        "max_tokens": 2000,
    },
    "visualization_agent": {
        "temperature": 0.3,
        "max_tokens": 1500,
    },
    "confidence_guardrails": {
        "temperature": 0.2,
        "max_tokens": 1000,
    },
}

# ============================================================================
# Logging Configuration
# ============================================================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "analytics_engine.log")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# ============================================================================
# Demo/Test Configuration
# ============================================================================
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
MOCK_RESULTS = os.getenv("MOCK_RESULTS", "false").lower() == "true"  # Return fake data for testing

# ============================================================================
# Validation Functions
# ============================================================================
def validate_config():
    """Validate that all required configuration is present."""
    if not OPENAI_API_KEY and not ANTHROPIC_API_KEY:
        raise ValueError("Either OPENAI_API_KEY or ANTHROPIC_API_KEY must be set")
    
    if LLM_PROVIDER not in ["openai", "anthropic"]:
        raise ValueError(f"Invalid LLM_PROVIDER: {LLM_PROVIDER}")
    
    if LLM_PROVIDER == "openai" and not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY required when LLM_PROVIDER=openai")
    
    if LLM_PROVIDER == "anthropic" and not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY required when LLM_PROVIDER=anthropic")

def get_llm():
    """Factory function to get configured LLM."""
    if LLM_PROVIDER == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=LLM_MODEL,
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_TOKENS,
            api_key=OPENAI_API_KEY,
        )
    elif LLM_PROVIDER == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=LLM_MODEL,
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_TOKENS,
            api_key=ANTHROPIC_API_KEY,
        )
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {LLM_PROVIDER}")
