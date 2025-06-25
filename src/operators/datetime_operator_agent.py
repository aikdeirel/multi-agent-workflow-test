import logging
from langchain.tools import tool

from shared.base_callback import DateTimeOperatorCallback
from shared.agent_factory import create_operator_agent
from shared.operator_executor import execute_operator_with_tracing
from tools.operators.datetime_operator import (
    get_unix_time,
    get_week_number,
    check_leap_year,
    validate_date,
    get_weekday,
    calculate_progress,
    countdown_to_date,
    calculate_age,
    get_co2_level,
    get_german_holidays,
    datetime_help,
)

logger = logging.getLogger(__name__)


def create_datetime_operator_agent():
    """Create a specialized datetime operator agent using shared utilities."""
    datetime_tools = [
        get_unix_time,
        get_week_number,
        check_leap_year,
        validate_date,
        get_weekday,
        calculate_progress,
        countdown_to_date,
        calculate_age,
        get_co2_level,
        get_german_holidays,
        datetime_help,
    ]
    return create_operator_agent(
        operator_name="DateTime",
        tools=datetime_tools,
        callback_class=DateTimeOperatorCallback,
        system_prompt_name="datetime_operator_system"
    )


@tool
def datetime_operator(query: str) -> str:
    """
    Delegate datetime-related tasks to the specialized datetime operator agent.

    This tool acts as a bridge between the orchestrator and the datetime specialist.
    It takes natural language descriptions of datetime tasks and handles them appropriately.

    Args:
        query: Natural language description of the datetime task to perform

    Returns:
        String containing the datetime operator's response

    Examples:
        - datetime_operator("What week is January 1st, 2022?")
        - datetime_operator("Is 2020 a leap year?")
        - datetime_operator("How many days until Christmas 2024?")
        - datetime_operator("Calculate my age if I was born on 1990-01-01")
    """
    logger.info(f"📅 DateTime operator received task: {query}")

    return execute_operator_with_tracing(
        operator_name="datetime",
        query=query,
        agent_factory_func=create_datetime_operator_agent,
        emoji="📅"
    )
