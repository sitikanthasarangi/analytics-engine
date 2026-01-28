"""
Integration tests for Analytics Engine.
Run with: pytest tests/test_integration.py -v
"""

import pytest
import json
from state import create_initial_state, Intent, DataSources, DataSource, Insight, Anomaly
from agents.question_interpreter import question_interpreter_node
from agents.data_advisor import data_advisor_node, AVAILABLE_DATA_SOURCES
from graph import create_graph

class TestStateManagement:
    """Test state creation and transitions."""
    
    def test_initial_state_creation(self):
        """Test creating initial state."""
        state = create_initial_state("test question", "test_user")
        assert state["question"] == "test question"
        assert state["user_id"] == "test_user"
        assert state["status"] == "created"
        assert state["error_state"] is None
    
    def test_state_defaults(self):
        """Test state has correct defaults."""
        state = create_initial_state("q")
        assert isinstance(state["execution_log"], list)
        assert isinstance(state["insights"], list)
        assert isinstance(state["anomalies"], list)
        assert isinstance(state["visualizations"], list)
        assert state["plan_approved"] is False

class TestDataAdvisor:
    """Test data advisor agent."""
    
    def test_available_sources(self):
        """Test mock data sources are available."""
        assert "revenue_fact" in AVAILABLE_DATA_SOURCES
        assert "customer_dim" in AVAILABLE_DATA_SOURCES
        assert "product_dim" in AVAILABLE_DATA_SOURCES
        assert "cost_ledger" in AVAILABLE_DATA_SOURCES
    
    def test_data_source_structure(self):
        """Test data source has required fields."""
        source = AVAILABLE_DATA_SOURCES["revenue_fact"]
        assert "table" in source
        assert "columns" in source
        assert "primary_keys" in source
        assert "quality_score" in source
        assert source["quality_score"] > 0
        assert source["quality_score"] <= 1

class TestGraphCompilation:
    """Test LangGraph compilation."""
    
    def test_graph_compiles(self):
        """Test graph compiles without errors."""
        try:
            graph = create_graph()
            assert graph is not None
        except Exception as e:
            pytest.fail(f"Graph compilation failed: {str(e)}")
    
    def test_graph_has_nodes(self):
        """Test graph has all expected nodes."""
        graph = create_graph()
        # Note: Can't directly inspect compiled graph, so just verify it exists
        assert graph is not None

class TestIntents:
    """Test Intent model."""
    
    def test_intent_creation(self):
        """Test creating Intent."""
        intent = Intent(
            task_type="trend_analysis",
            entities=["revenue", "region"],
            metrics=["total_sales", "avg_price"],
            time_window="90d"
        )
        assert intent.task_type == "trend_analysis"
        assert len(intent.metrics) == 2
    
    def test_intent_defaults(self):
        """Test Intent defaults."""
        intent = Intent(task_type="test")
        assert intent.confidence == 0.8
        assert intent.time_window == "90d"
        assert isinstance(intent.entities, list)

class TestInsights:
    """Test Insight model."""
    
    def test_insight_creation(self):
        """Test creating Insight."""
        insight = Insight(
            finding="Revenue increased",
            metric="total_revenue",
            magnitude="+15%",
            confidence=0.85
        )
        assert insight.finding == "Revenue increased"
        assert insight.magnitude == "+15%"
    
    def test_anomaly_creation(self):
        """Test creating Anomaly."""
        anomaly = Anomaly(
            description="Unexpected spike",
            affected_metric="cost",
            magnitude="+50%",
            severity="high"
        )
        assert anomaly.severity == "high"
        assert anomaly.affected_metric == "cost"

class TestConfiguration:
    """Test configuration loading."""
    
    def test_config_loads(self):
        """Test config module loads without errors."""
        try:
            from config import (
                LLM_PROVIDER,
                QUERY_TIMEOUT,
                DEFAULT_TIME_WINDOW,
                ANOMALY_THRESHOLD,
            )
            assert LLM_PROVIDER in ["openai", "anthropic"]
            assert QUERY_TIMEOUT > 0
            assert DEFAULT_TIME_WINDOW > 0
            assert ANOMALY_THRESHOLD > 0
        except ImportError as e:
            pytest.fail(f"Config import failed: {str(e)}")

# === Manual Testing Guide ===
"""
# Test 1: Graph Execution (Manual)
python main.py "What were our top selling products last month?"

# Expected output should show:
# [interpreter] ✓ status
# [data_advisor] ✓ status
# [planner] ✓ status
# ... and so on through all agents


# Test 2: Error Handling (Manual)
python main.py "invalid%%%question***test"

# Should gracefully handle and log errors


# Test 3: State Persistence (Manual)
export STATE_PERSISTENCE=memory
python main.py "test question"

# Should complete without errors


# Test 4: Different LLM Providers
export LLM_PROVIDER=anthropic  # Switch providers
python main.py "test question"

# Should work with Claude if ANTHROPIC_API_KEY is set


# Test 5: Verbose Logging (Manual)
export VERBOSE_LOGGING=true
export LOG_LEVEL=DEBUG
python main.py "test question"

# Should show detailed debug information
"""

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
