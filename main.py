#!/usr/bin/env python3
"""
Autonomous Analytics Recommendation Engine - Main Entry Point
LangGraph-based Multi-Agent System for Intelligent Data Analysis
"""

import sys
import json
import logging
from typing import Optional
from colorama import Fore, Style, init
from state import create_initial_state, state_to_dict
from config import validate_config, VERBOSE_LOGGING, LOG_LEVEL, LOG_FORMAT
from graph import get_graph

# Initialize colorama for pretty terminal output
init(autoreset=True)

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
)
logger = logging.getLogger(__name__)


def print_banner():
    """Print welcome banner."""
    print(f"{Fore.CYAN}")
    print(
        """
    ╔═══════════════════════════════════════════════════════════════╗
    ║   🔍 AUTONOMOUS ANALYTICS RECOMMENDATION ENGINE 🔍            ║
    ║   Multi-Agent LangGraph Orchestration System                  ║
    ║   Intelligent Data Analysis & Insight Generation              ║
    ╚═══════════════════════════════════════════════════════════════╝
    """
    )
    print(f"{Style.RESET_ALL}")


def print_section(title: str):
    """Print formatted section header."""
    print(f"\n{Fore.GREEN}{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}{Style.RESET_ALL}\n")


def print_status(agent: str, status: str, color: str = Fore.CYAN):
    """Print agent status."""
    print(f"{color}[{agent:20}] {status}{Style.RESET_ALL}")


def format_results(state) -> str:
    """Format final results for display."""
    output = []

    # Header
    output.append(f"\n{Fore.GREEN}{'=' * 70}")
    output.append(f"ANALYSIS COMPLETE{Style.RESET_ALL}\n")

    # Intent
    if state.get("interpreted_intent"):
        intent = state["interpreted_intent"]
        output.append(f"{Fore.YELLOW}📊 INTERPRETED INTENT:{Style.RESET_ALL}")
        output.append(f"  • Task Type: {intent.task_type}")
        output.append(f"  • Metrics: {', '.join(intent.metrics)}")
        output.append(f"  • Entities: {', '.join(intent.entities)}")
        output.append(f"  • Time Window: {intent.time_window}")
        output.append("")

    # Data Sources
    if state.get("available_data_sources"):
        sources = state["available_data_sources"]
        output.append(f"{Fore.YELLOW}🗄️  DATA SOURCES:{Style.RESET_ALL}")
        output.append(f"  • Found {sources.total_sources} relevant sources")
        for source in sources.sources:
            output.append(
                f"    - {source.name} (quality: {source.quality_score:.0%}, {source.record_count} rows)"
            )
        output.append("")

    # Plan
    if state.get("analysis_plan"):
        plan = state["analysis_plan"]
        output.append(f"{Fore.YELLOW}📋 ANALYSIS PLAN:{Style.RESET_ALL}")
        output.append(f"  • Steps: {plan.total_steps}")
        output.append(f"  • Est. Runtime: {plan.estimated_runtime_seconds}s")
        if plan.warnings:
            output.append("  • Warnings:")
            for w in plan.warnings:
                output.append(f"    - {w}")
        output.append("")

    # Execution
    if state.get("execution_results"):
        results = state["execution_results"]
        output.append(f"{Fore.YELLOW}⚙️  EXECUTION RESULTS:{Style.RESET_ALL}")
        output.append(f"  • Queries: {len(results.queries_executed)}")
        output.append(f"  • Rows: {results.row_count}")
        output.append(f"  • Time: {results.execution_time_total_ms}ms")
        output.append("")

    # Insights
    if state.get("insights"):
        insights = state["insights"]
        output.append(f"{Fore.YELLOW}💡 INSIGHTS ({len(insights)}):{Style.RESET_ALL}")
        for insight in insights[:5]:
            output.append(f"  • {insight.finding}")
            output.append(
                f"    Metric: {insight.metric} | Magnitude: {insight.magnitude} | Confidence: {insight.confidence:.0%}"
            )
        output.append("")

    # Anomalies
    if state.get("anomalies"):
        anomalies = state["anomalies"]
        output.append(f"{Fore.CYAN}⚠️  ANOMALIES ({len(anomalies)}):{Style.RESET_ALL}")
        for anomaly in anomalies:
            severity_color = {
                "high": Fore.RED,
                "medium": Fore.YELLOW,
                "low": Fore.GREEN,
            }.get(anomaly.severity, Fore.WHITE)
            output.append(
                f"{severity_color}  • [{anomaly.severity.upper()}] {anomaly.description}{Style.RESET_ALL}"
            )
        output.append("")

    # Visualizations
    if state.get("visualizations"):
        visualizations = state["visualizations"]
        output.append(f"{Fore.YELLOW}📈 VISUALIZATIONS ({len(visualizations)}):{Style.RESET_ALL}")
        for viz in visualizations:
            output.append(f"  • {viz.title} ({viz.chart_type})")
        output.append("")

    # Confidence
    if state.get("confidence_assessment"):
        conf = state["confidence_assessment"]
        output.append(f"{Fore.YELLOW}🎯 CONFIDENCE ASSESSMENT:{Style.RESET_ALL}")
        output.append(f"  • Overall Confidence: {conf.overall_confidence:.0%}")
        if conf.caveats:
            output.append(f"  • Caveats: {len(conf.caveats)}")
            for caveat in conf.caveats[:3]:
                output.append(f"    - {caveat}")
        output.append("")

    # Execution log
    if state.get("execution_log"):
        output.append(f"{Fore.CYAN}📝 EXECUTION LOG:{Style.RESET_ALL}")
        for log_entry in state["execution_log"][-10:]:
            output.append(f"  {log_entry}")

    return "\n".join(output)


def run_analysis(question: str, user_id: str = "user", stream: bool = False):
    """
    Run the analytics engine on a question.

    Args:
        question: User's analytical question
        user_id: Unique identifier for user
        stream: (currently unused, streaming disabled for simplicity)

    Returns:
        Final state dictionary
    """
    print_banner()
    print_section("INITIALIZING ANALYSIS")

    # Validate configuration
    try:
        validate_config()
        print_status("Config", "✓ Configuration validated")
    except Exception as e:
        print_status("Config", f"✗ Configuration error: {e}", Fore.RED)
        return None

    # Create initial state
    state = create_initial_state(question, user_id)
    print_status("State", "✓ Initial state created")

    # Get compiled graph
    try:
        graph = get_graph()
        print_status("Graph", "✓ LangGraph compiled")
    except Exception as e:
        print_status("Graph", f"✗ Failed to compile graph: {e}", Fore.RED)
        return None

    print_section("EXECUTING ANALYSIS WORKFLOW")

    # Run to completion without streaming (simpler, avoids tuple issues)
    try:
        state = graph.invoke(state)
    except Exception as e:
        print_status("Invoke", f"✗ Execution error: {e}", Fore.RED)
        logger.exception("Graph invocation error")
        return state

    # Print results
    print(format_results(state))

    return state


def interactive_mode():
    """Run interactive CLI mode."""
    print_banner()
    print(f"{Fore.CYAN}Type your analytics question (or 'quit' to exit):{Style.RESET_ALL}\n")

    while True:
        try:
            question = input(f"{Fore.YELLOW}Question > {Style.RESET_ALL}").strip()

            if question.lower() in ["quit", "exit", "q"]:
                print(f"{Fore.GREEN}Goodbye!{Style.RESET_ALL}")
                break

            if not question:
                print(f"{Fore.YELLOW}Please enter a question.{Style.RESET_ALL}\n")
                continue

            # Run analysis
            state = run_analysis(question)

            # Option to export
            export = input(
                f"\n{Fore.YELLOW}Export results? (y/n): {Style.RESET_ALL}"
            ).strip().lower()
            if export == "y" and state is not None:
                filename = f"analysis_{hash(question) % 10000}.json"
                with open(filename, "w") as f:
                    json.dump(state_to_dict(state), f, indent=2)
                print(f"{Fore.GREEN}✓ Exported to {filename}{Style.RESET_ALL}")

            print("")

        except KeyboardInterrupt:
            print(f"\n{Fore.GREEN}Interrupted. Goodbye!{Style.RESET_ALL}")
            break
        except Exception as e:
            print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
            if VERBOSE_LOGGING:
                logger.exception("Interactive mode error")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        # Interactive mode
        interactive_mode()
    else:
        # CLI mode: python main.py "Your question here"
        question = " ".join(sys.argv[1:])
        run_analysis(question)


if __name__ == "__main__":
    main()
