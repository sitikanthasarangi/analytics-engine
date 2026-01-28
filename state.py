from typing import TypedDict, Optional, List, Any
from pydantic import BaseModel, Field
import json
from typing import List, Optional, Any
from pydantic import BaseModel, Field

# ============================================================================
# Pydantic Models (for validation & serialization)
# ============================================================================

class Intent(BaseModel):
    """Interpreted user intent from question."""
    task_type: str = Field(..., description="Type: trend_analysis, root_cause, comparison, forecast, anomaly_detection, custom")
    entities: List[str] = Field(default_factory=list)
    metrics: List[str] = Field(default_factory=list)
    time_window: str = Field(default="90d")
    segments: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.8, ge=0, le=1)
    is_generic: bool = Field(default=False, description="True if question is generic like 'what can you do'")

class DataSource(BaseModel):
    """Available data source definition."""
    name: str
    table_name: str
    columns: List[str]
    primary_keys: List[str]
    quality_score: float = Field(default=0.9, ge=0, le=1)
    last_updated: str
    record_count: Optional[int] = None

class DataSources(BaseModel):
    """Available data sources for analysis."""
    sources: List[DataSource] = Field(default_factory=list)
    total_sources: int = 0
    coverage_score: float = Field(default=0.0, ge=0, le=1)
    warnings: List[str] = Field(default_factory=list)

class AnalysisStep(BaseModel):
    step_number: int
    description: str
    required_tables: List[str]
    sql_template: Optional[str] = None
    # Allow strings or ints from the model; we treat them as opaque IDs
    depends_on: List[Any] = Field(default_factory=list)


class AnalysisPlan(BaseModel):
    """Complete multi-step analysis plan."""
    steps: List[AnalysisStep] = Field(default_factory=list)
    total_steps: int = 0
    estimated_runtime_seconds: float = 0
    estimated_rows_returned: int = 0
    warnings: List[str] = Field(default_factory=list)
    data_quality_issues: List[str] = Field(default_factory=list)

class QueryExecution(BaseModel):
    """Record of executed query."""
    query_id: str
    sql: str
    status: str  # pending, approved, executing, completed, failed
    rows_affected: int = 0
    execution_time_ms: float = 0
    error_message: Optional[str] = None

class QueryResults(BaseModel):
    """Results from executed queries."""
    queries_executed: List[QueryExecution] = Field(default_factory=list)
    result_data: List[dict] = Field(default_factory=list)
    row_count: int = 0
    execution_time_total_ms: float = 0
    success: bool = True

class Insight(BaseModel):
    """Single insight extracted from results."""
    finding: str
    metric: str
    magnitude: str  # e.g., "+15%", "-2.3%", "3.5x"
    confidence: float = Field(default=0.8, ge=0, le=1)
    supporting_evidence: Optional[str] = None
    business_impact: str = Field(default="medium")  # high, medium, low

class Anomaly(BaseModel):
    """Detected anomaly in data."""
    description: str
    severity: str = Field(default="medium")  # high, medium, low
    affected_metric: str
    affected_segment: Optional[str] = None
    magnitude: str
    confidence: float = Field(default=0.75, ge=0, le=1)

class Visualization(BaseModel):
    """Chart or visualization definition."""
    chart_id: str
    chart_type: str  # line, bar, scatter, histogram, heatmap, treemap, etc.
    title: str
    data_fields: dict = Field(default_factory=dict)  # x, y, color, size, etc.
    description: str = ""
    appropriateness_score: float = Field(default=0.85, ge=0, le=1)

class ConfidenceMetrics(BaseModel):
    """Confidence assessment of analysis results."""
    overall_confidence: float = Field(default=0.75, ge=0, le=1)
    data_freshness: str = Field(default="recent")  # recent, moderate, stale
    sample_size_adequate: bool = True
    completeness_score: float = Field(default=0.9, ge=0, le=1)
    caveats: List[str] = Field(default_factory=list)
    data_quality_issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)



class QueryExecutionRecord(BaseModel):
    step_number: int
    description: str
    sql: str
    executed: bool = False
    success: Optional[bool] = None
    rows_returned: Optional[int] = None
    error_message: Optional[str] = None


class ExecutionResults(BaseModel):
    """Results of executing the analysis plan."""
    queries_executed: List[QueryExecutionRecord]
    row_count: int = 0
    execution_time_total_ms: int = 0
    success: bool = True
    errors: List[str] = Field(default_factory=list)
    # Arbitrary per-dataset results, e.g. summaries & samples from pandas
    result_data: Any = None

# ============================================================================
# LangGraph State Schema (TypedDict)
# ============================================================================

class AnalyticsState(TypedDict):
    """
    Main state object that flows through the LangGraph.
    Each node receives this state, optionally modifies fields, and returns updates.
    """
    # Input
    question: str
    user_id: str
    
    # Interpretation stage
    interpreted_intent: Optional[Intent]
    
    # Data validation stage
    available_data_sources: Optional[DataSources]
    
    # Planning stage
    analysis_plan: Optional[AnalysisPlan]
    
    # Approval stage (human-in-the-loop)
    plan_approved: bool
    approval_notes: Optional[str]
    
    # Execution stage
    execution_results: Optional[ExecutionResults]
    execution_errors: List[str]
    
    # Insight generation stage
    insights: List[Insight]
    anomalies: List[Anomaly]
    
    # Visualization stage
    visualizations: List[Visualization]
    
    # Final assessment
    confidence_assessment: Optional[ConfidenceMetrics]
    
    # Tracking & metadata
    conversation_history: List[Any]
    execution_log: List[str]
    status: str  # created, interpreting, validating, planning, awaiting_approval, executing, analyzing, visualizing, completed, failed
    error_state: Optional[str]

# ============================================================================
# Helper Functions
# ============================================================================

def create_initial_state(question: str, user_id: str = "anonymous") -> AnalyticsState:
    """Create initial state for new analysis."""
    return {
        "question": question,
        "user_id": user_id,
        "interpreted_intent": None,
        "available_data_sources": None,
        "analysis_plan": None,
        "plan_approved": False,
        "approval_notes": None,
        "execution_results": None,
        "execution_errors": [],
        "insights": [],
        "anomalies": [],
        "visualizations": [],
        "confidence_assessment": None,
        "conversation_history": [],
        "execution_log": [],
        "status": "created",
        "error_state": None,
    }

def state_to_dict(state: AnalyticsState) -> dict:
    """Convert state to JSON-serializable dict."""
    result = {}
    for key, value in state.items():
        if isinstance(value, BaseModel):
            result[key] = value.model_dump()
        elif isinstance(value, list) and value and isinstance(value[0], BaseModel):
            result[key] = [item.model_dump() if isinstance(item, BaseModel) else item for item in value]
        else:
            try:
                result[key] = value
            except:
                result[key] = str(value)
    return result

def log_state_transition(state: AnalyticsState, new_status: str, message: str) -> AnalyticsState:
    """Log state transition for debugging."""
    state["execution_log"].append(f"[{new_status}] {message}")
    state["status"] = new_status
    return state
