import logging
from langchain.tools import tool

from shared.base_callback import WeatherOperatorCallback
from shared.agent_factory import create_operator_agent
from shared.operator_executor import execute_operator_with_tracing
from tools.operators.weather_operator import (
    get_current_weather,
    get_weather_forecast,
    weather_help,
)

logger = logging.getLogger(__name__)


def create_weather_operator_agent():
    """Create a specialized weather operator agent using shared utilities."""
    weather_tools = [get_current_weather, get_weather_forecast, weather_help]
    return create_operator_agent(
        operator_name="Weather",
        tools=weather_tools,
        callback_class=WeatherOperatorCallback,
        system_prompt_name="weather_operator_system"
    )


@tool
def weather_operator(query: str) -> str:
    """
    Delegate weather-related tasks to the specialized weather operator agent.

    This tool acts as a bridge between the orchestrator and the weather specialist.
    It takes natural language descriptions of weather tasks and handles them appropriately.

    Args:
        query: Natural language description of the weather task to perform

    Returns:
        String containing the weather operator's response

    Examples:
        - weather_operator("Get current weather for Berlin")
        - weather_operator("Compare weather between London and Paris")
        - weather_operator("Weather forecast for next 5 days in Tokyo")
    """
    logger.info(f"☁️ Weather operator received task: {query}")

    return execute_operator_with_tracing(
        operator_name="weather",
        query=query,
        agent_factory_func=create_weather_operator_agent,
        emoji="�️"
    )
