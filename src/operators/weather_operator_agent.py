import logging
from typing import Dict, Any, Optional, List
from langchain.agents import create_react_agent, AgentExecutor
from langchain.prompts import PromptTemplate
from langchain_mistralai import ChatMistralAI
from langchain.tools import tool

from config import load_json_setting
from prompt_manager import get_prompt_manager
from tools.operators.weather_operator import (
    get_current_weather,
    get_weather_forecast,
    weather_help,
)
from tools import factory as tool_factory

logger = logging.getLogger(__name__)


def create_weather_operator_agent(llm: ChatMistralAI) -> AgentExecutor:
    """
    Create a specialized weather operator agent.

    Args:
        llm: Configured ChatMistralAI instance

    Returns:
        Configured AgentExecutor for weather operations
    """
    try:
        # Get weather tools
        weather_tools = [get_current_weather, get_weather_forecast, weather_help]

        # Load weather operator prompt
        prompt_manager = get_prompt_manager()
        system_prompt = prompt_manager.get_prompt("weather_operator_system")

        # Create ReAct prompt template for weather operator
        react_template = f"""{system_prompt}

TOOLS:
------

You have access to the following tools:

{{tools}}

To use a tool, you MUST use this EXACT format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{{tool_names}}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

CRITICAL SINGLE-ACTION RULES:
- YOU CAN ONLY PERFORM ONE ACTION PER RESPONSE
- NEVER combine multiple Action/Action Input pairs in a single response
- After generating Action and Action Input, STOP and wait for the Observation
- Do NOT write multiple actions like "Action: ... Action: ..." in the same response
- Do NOT include placeholder text like "(After receiving...)" or "(Then I'll...)"
- Each response must contain EITHER one Action OR one Final Answer, NEVER both
- If you need multiple tools, use them one at a time across multiple responses

IMPORTANT RULES:
- You must EITHER generate an Action OR a Final Answer, NEVER both in the same response
- If you need to use a tool, generate Action and Action Input, then wait for Observation
- Only generate Final Answer when you have all the information needed to answer the question
- Do not include example text like "[After receiving the tool response]" in your actual response

Begin!

Question: {{input}}
Thought:{{agent_scratchpad}}"""

        prompt_template = PromptTemplate.from_template(react_template)

        # Create ReAct agent
        agent = create_react_agent(llm=llm, tools=weather_tools, prompt=prompt_template)

        # Create executor
        executor = AgentExecutor(
            agent=agent,
            tools=weather_tools,
            verbose=False,
            max_iterations=5,
            max_execution_time=120,
            return_intermediate_steps=True,
            handle_parsing_errors=True,
        )

        logger.info("Weather operator agent created successfully")
        return executor

    except Exception as e:
        logger.error(f"Error creating weather operator agent: {str(e)}")
        raise RuntimeError(f"Failed to create weather operator agent: {str(e)}")


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
    logger.info(f"Weather operator received task: {query}")

    try:
        # Use Langfuse 3.x context approach
        try:
            from langfuse import get_client

            langfuse_client = get_client()

            # Create child span in current context
            with langfuse_client.start_as_current_span(
                name="weather_operator_execution",
                input={"task": query},
                metadata={
                    "operator_type": "weather",
                    "task_description": query,
                    "agent_type": "weather_specialist",
                },
            ) as operator_span:
                logger.info("✅ Created weather operator span")

                # Create LLM for the weather operator
                from config import get_global_settings

                settings = get_global_settings()
                model_config = load_json_setting("model_config")
                llm = ChatMistralAI(
                    model=settings.mistral_model,
                    temperature=model_config["temperature"],
                    max_tokens=model_config["max_tokens"],
                    timeout=model_config["timeout"],
                )

                # Create weather operator agent
                weather_agent = create_weather_operator_agent(llm)

                # Execute the task
                result = weather_agent.invoke({"input": query})

                # Extract the output
                output = result.get("output", "No response from weather operator")

                # Update operator span with results
                operator_span.update(
                    output=output,
                    metadata={
                        "operator_type": "weather",
                        "task_description": query,
                        "agent_type": "weather_specialist",
                        "tools_used": len(result.get("intermediate_steps", [])),
                        "success": True,
                    },
                )
                logger.info("✅ Updated weather operator span")

                logger.info("Weather operator completed task successfully")
                return output

        except Exception as e:
            logger.warning(f"Langfuse tracing not available: {e}")

            # Fallback execution without tracing
            from config import get_global_settings

            settings = get_global_settings()
            model_config = load_json_setting("model_config")
            llm = ChatMistralAI(
                model=settings.mistral_model,
                temperature=model_config["temperature"],
                max_tokens=model_config["max_tokens"],
                timeout=model_config["timeout"],
            )

            # Create weather operator agent
            weather_agent = create_weather_operator_agent(llm)

            # Execute the task
            result = weather_agent.invoke({"input": query})

            # Extract the output
            output = result.get("output", "No response from weather operator")

            logger.info("Weather operator completed task successfully")
            return output

    except Exception as e:
        error_msg = f"Error in weather operator: {str(e)}"
        logger.error(error_msg)
        return error_msg
