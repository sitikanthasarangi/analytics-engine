"""
Answer Synthesizer Agent - Produces a direct natural-language answer to the user's question
based on the SQL query results and execution data.
"""

import json
import re
from state import AnalyticsState, log_state_transition
from config import get_llm


def answer_synthesizer_node(state: AnalyticsState) -> AnalyticsState:
    """Synthesize a direct answer to the user's question from query results."""

    exec_results = state.get("execution_results")
    if not exec_results or not exec_results.result_data:
        state["direct_answer"] = "No data was available to answer this question."
        return log_state_transition(state, "answering", "No data for answer synthesis")

    result_data = exec_results.result_data
    question = state["question"]
    llm = get_llm()

    # Collect the SQL query results (the actual answers)
    query_results_text = ""
    if "query_results" in result_data:
        for step_key, step_result in result_data["query_results"].items():
            query_results_text += f"\n--- {step_key} ---\n"
            query_results_text += f"SQL: {step_result.get('sql', 'N/A')}\n"
            query_results_text += f"Columns: {step_result.get('columns', [])}\n"
            query_results_text += f"Rows returned: {step_result.get('row_count', 0)}\n"
            data_str = json.dumps(step_result.get("data", [])[:30], indent=2, default=str)
            query_results_text += f"Data:\n{data_str}\n"

    # Also include summary context from pandas analysis
    summary_text = ""
    for key, val in result_data.items():
        if key == "query_results":
            continue
        if isinstance(val, dict) and "summary" in val:
            summary_text += f"\nDataset '{key}' summary stats available.\n"

    # Truncate if too long
    if len(query_results_text) > 10000:
        query_results_text = query_results_text[:10000] + "\n... (truncated)"

    prompt = f"""You are a data analyst. The user asked:

QUESTION: {question}

Here are the SQL query results from the actual data:

{query_results_text}

{summary_text}

Based on these results, provide a clear, direct answer to the user's question.
- Lead with the answer (numbers, names, rankings).
- Be specific: cite actual values from the data.
- If the query returned no rows or failed, explain what that means.
- Keep it concise but complete (2-5 sentences for simple questions, more for complex ones).
- Use markdown formatting for readability (bold key numbers, use bullet points for lists)."""

    try:
        response = llm.invoke([{"role": "user", "content": prompt}])
        state["direct_answer"] = response.content.strip()
    except Exception as e:
        state["direct_answer"] = f"Could not synthesize answer: {e}"

    state = log_state_transition(
        state, "answering",
        f"Generated direct answer ({len(state['direct_answer'])} chars)"
    )
    return state
