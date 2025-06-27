import logging
from langchain.tools import tool

from shared.base_callback import MathOperatorCallback
from shared.agent_factory import create_operator_agent
from shared.operator_executor import execute_operator_with_tracing
from tools.operators.math_operator import calculate, math_help

logger = logging.getLogger(__name__)


def create_math_operator_agent():
    """Create a specialized math operator agent using shared utilities."""
    math_tools = [calculate, math_help]
    return create_operator_agent(
        operator_name="Math",
        tools=math_tools,
        callback_class=MathOperatorCallback,
        system_prompt_name="math_operator_system"
    )


@tool
def math_operator(query: str) -> str:
    """
    Delegate mathematical tasks to the specialized math operator agent.

    This tool acts as a bridge between the orchestrator and the math specialist.
    It takes natural language descriptions of mathematical tasks and handles them appropriately.

    Args:
        query: Natural language description of the mathematical task to perform

    Returns:
        String containing the math operator's response

    Examples:
        - math_operator("Calculate 2 + 3 * 4")
        - math_operator("What is the square root of 144?")
        - math_operator("Solve the expression 50 * 2 + 25")
    """
    logger.info(f"🧮 Math operator received task: {query}")

    return execute_operator_with_tracing(
        operator_name="math",
        query=query,
        agent_factory_func=create_math_operator_agent,
        emoji="🧮"
    )
