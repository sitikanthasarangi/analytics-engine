"""
Question Interpreter Agent - Translates user questions into structured intent.
"""

import json
from typing import Optional
from state import AnalyticsState, Intent, log_state_transition
from config import get_llm, SYSTEM_PROMPT_INTERPRETER, AGENT_CONFIG
from langchain_core.messages import HumanMessage, SystemMessage


def question_interpreter_node(state: AnalyticsState) -> AnalyticsState:
    """
    Interpret user question and extract structured intent.

    Understands:
    - Task type (trend_analysis, root_cause, comparison, forecast, anomaly_detection)
    - Key business entities (products, regions, customers, time periods)
    - Metrics involved (revenue, cost, customers, conversion rate)
    - Required segments and time windows
    """
    question = state["question"]

    llm = get_llm()
    _ = AGENT_CONFIG["question_interpreter"]  # kept for future tuning

    # Strict JSON-only system prompt
    system_msg = SystemMessage(
        content=(
            SYSTEM_PROMPT_INTERPRETER
            + "\n\nIMPORTANT:\n"
            + "You MUST respond with VALID JSON ONLY. "
            + "Do not include any commentary, markdown, or text outside the JSON.\n"
            + 'Example:\n'
            + '{\n'
            + '  "intent": "trend_analysis",\n'
            + '  "entities": ["product", "region"],\n'
            + '  "metrics": ["revenue"],\n'
            + '  "time_window": "90d",\n'
            + '  "segments": ["region"],\n'
            + '  "confidence": 0.85\n'
            + '}\n'
        )
    )

    user_msg = HumanMessage(
        content=(
            "USER QUESTION:\n"
            f"{question}\n\n"
            "Respond with a single JSON object only, no explanation."
        )
    )

    try:
        response = llm.invoke([system_msg, user_msg])
        response_text = response.content.strip()

        # Debug: if model accidentally wraps JSON in fences, strip them
        if response_text.startswith("```"):
            # remove ```json ... ``` or ``` ... ```
            lines = response_text.splitlines()
            lines = [ln for ln in lines if not ln.strip().startswith("```")]
            response_text = "\n".join(lines).strip()

        intent_data = json.loads(response_text)

        generic_phrases = [
            "what can you do",
            "what can you help with",
            "how can you help",
            "what are your capabilities",
    ]

        q_lower = question.lower()
        is_generic = any(p in q_lower for p in generic_phrases)

        intent = Intent(
            task_type=intent_data.get("intent", "custom"),
            entities=intent_data.get("entities", []),
            metrics=intent_data.get("metrics", []),
            time_window=intent_data.get("time_window", "90d"),
            segments=intent_data.get("segments", []),
            confidence=float(intent_data.get("confidence", 0.8)),
            is_generic=is_generic,
        )


        state["interpreted_intent"] = intent
        state = log_state_transition(
            state,
            "interpreting",
            f"Parsed question as {intent.task_type} analysis with {len(intent.metrics)} metrics",
        )
        return state

    except Exception as e:
        # Fallback: create a very simple Intent so the rest of the graph can proceed
        q_lower = question.lower()
        is_generic = any(p in q_lower for p in generic_phrases)

        fallback_intent = Intent(
            task_type="custom",
            entities=[],
            metrics=[],
            time_window="90d",
            segments=[],
            confidence=0.5,
            is_generic=is_generic,
        )

        state["interpreted_intent"] = fallback_intent
        state["error_state"] = f"Failed to parse interpreter response cleanly: {str(e)}"
        state = log_state_transition(
            state,
            "interpreting",
            "Fell back to default intent due to JSON parse error",
        )
        return state
