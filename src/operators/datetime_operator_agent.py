import logging
from typing import Dict, Any, Optional, List
from langchain.agents import create_react_agent, AgentExecutor
from langchain.prompts import PromptTemplate
from langchain_mistralai import ChatMistralAI
from langchain.tools import tool
from langchain.callbacks.base import BaseCallbackHandler

from config import load_json_setting
from prompt_manager import get_prompt_manager
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
from tools import factory as tool_factory

logger = logging.getLogger(__name__)


class DateTimeOperatorCallback(BaseCallbackHandler):
    """Callback handler for datetime operator internal actions."""

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger("operators.datetime_internal")

    def on_agent_action(self, action, **kwargs):
        """Called when datetime agent takes an action."""
        self.logger.info(f"📅 DATETIME AGENT ACTION: {action.tool}")
        self.logger.info(f"📋 DATETIME AGENT PARAMETERS: {action.tool_input}")

    def on_tool_end(self, output, **kwargs):
        """Called when datetime tool ends."""
        self.logger.info(f"🔧 DATETIME TOOL RESPONSE: {str(output)[:200]}...")

    def on_text(self, text, **kwargs):
        """Called on datetime agent text - captures thinking."""
        if text and text.strip():
            text_stripped = text.strip()
            if text_stripped.startswith("Thought:"):
                thinking = text_stripped.replace("Thought:", "").strip()
                self.logger.info(f"💭 DATETIME AGENT THINKING: {thinking}")
            elif "I need" in text_stripped or "I should" in text_stripped:
                self.logger.info(f"🤔 DATETIME AGENT REASONING: {text_stripped}")

    def on_llm_start(self, serialized, prompts, **kwargs):
        """Called when datetime agent LLM starts."""
        if prompts and len(prompts) > 0:
            for i, prompt in enumerate(prompts):
                # Log a truncated version of the prompt sent to datetime operator
                if len(str(prompt)) > 300:
                    truncated = (
                        str(prompt)[:150] + "...[TRUNCATED]..." + str(prompt)[-100:]
                    )
                    self.logger.info(f"📝 DATETIME AGENT PROMPT #{i+1}: {truncated}")
                else:
                    self.logger.info(f"📝 DATETIME AGENT PROMPT #{i+1}: {prompt}")


def create_datetime_operator_agent(llm: ChatMistralAI) -> AgentExecutor:
    """
    Create a specialized datetime operator agent.

    Args:
        llm: Configured ChatMistralAI instance

    Returns:
        Configured AgentExecutor for datetime operations
    """
    try:
        # Get datetime tools
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

        # Load datetime operator prompt
        prompt_manager = get_prompt_manager()
        system_prompt = prompt_manager.get_prompt("datetime_operator_system")

        # Create ReAct prompt template for datetime operator
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
- If you need multiple datetime operations, use them one at a time across multiple responses

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
        agent = create_react_agent(
            llm=llm, tools=datetime_tools, prompt=prompt_template
        )

        # Create executor with callback
        executor = AgentExecutor(
            agent=agent,
            tools=datetime_tools,
            verbose=False,
            max_iterations=5,
            max_execution_time=120,
            return_intermediate_steps=True,
            handle_parsing_errors=True,
            callbacks=[DateTimeOperatorCallback()],  # Add datetime-specific callback
        )

        logger.info("DateTime operator agent created successfully")
        return executor

    except Exception as e:
        logger.error(f"Error creating datetime operator agent: {str(e)}")
        raise RuntimeError(f"Failed to create datetime operator agent: {str(e)}")


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

    # Enhanced logging for datetime operator
    datetime_logger = logging.getLogger("operators.datetime_operator_agent")
    datetime_logger.info(f"📅 DATETIME OPERATOR STARTING TASK: {query}")
    datetime_logger.info("🔧 Creating specialized datetime agent...")

    try:
        # Use Langfuse 3.x context approach
        try:
            from langfuse import get_client

            langfuse_client = get_client()

            # Create child span in current context
            with langfuse_client.start_as_current_span(
                name="datetime_operator_execution",
                input={"task": query},
                metadata={
                    "operator_type": "datetime",
                    "task_description": query,
                    "agent_type": "datetime_specialist",
                },
            ) as operator_span:
                logger.info("✅ Created datetime operator span")

                # Create LLM for the datetime operator
                from config import get_global_settings

                settings = get_global_settings()
                model_config = load_json_setting("model_config")
                llm = ChatMistralAI(
                    model=settings.mistral_model,
                    temperature=model_config["temperature"],
                    max_tokens=model_config["max_tokens"],
                    timeout=model_config["timeout"],
                )

                # Create datetime operator agent
                datetime_agent = create_datetime_operator_agent(llm)
                datetime_logger.info("✅ DateTime agent created successfully")

                # Execute datetime task
                datetime_logger.info(f"📋 SENDING TASK TO DATETIME AGENT: {query}")
                datetime_logger.info("🚀 Executing datetime task...")

                result = datetime_agent.invoke({"input": query})

                # Extract response
                agent_response = result.get("output", "No response from datetime agent")
                datetime_logger.info(f"📅 DATETIME OPERATOR RESPONSE: {agent_response}")

                # Log tool usage summary
                if "intermediate_steps" in result:
                    steps = result["intermediate_steps"]
                    if steps:
                        datetime_logger.info(
                            f"🔍 DateTime agent used {len(steps)} tools:"
                        )
                        for i, (action, observation) in enumerate(steps, 1):
                            tool_name = action.tool
                            datetime_logger.info(
                                f"  Step {i}: {tool_name} -> {str(observation)[:100]}..."
                            )

                # Update operator span
                operator_span.update(
                    output=agent_response,
                    metadata={
                        "operator_type": "datetime",
                        "task_description": query,
                        "agent_type": "datetime_specialist",
                        "tools_used": len(result.get("intermediate_steps", [])),
                        "success": True,
                    },
                )
                datetime_logger.info("✅ Updated datetime operator span")
                datetime_logger.info("📅 DateTime operator completed task successfully")

                return agent_response

        except Exception as trace_error:
            # If tracing fails, continue without it
            datetime_logger.warning(
                f"⚠️ Tracing failed, continuing without: {trace_error}"
            )

            # Create LLM for the datetime operator
            from config import get_global_settings

            settings = get_global_settings()
            model_config = load_json_setting("model_config")
            llm = ChatMistralAI(
                model=settings.mistral_model,
                temperature=model_config["temperature"],
                max_tokens=model_config["max_tokens"],
                timeout=model_config["timeout"],
            )

            # Create datetime operator agent
            datetime_agent = create_datetime_operator_agent(llm)
            datetime_logger.info("✅ DateTime agent created successfully (no tracing)")

            # Execute datetime task
            datetime_logger.info(f"📋 SENDING TASK TO DATETIME AGENT: {query}")
            datetime_logger.info("🚀 Executing datetime task...")

            result = datetime_agent.invoke({"input": query})

            # Extract response
            agent_response = result.get("output", "No response from datetime agent")
            datetime_logger.info(f"📅 DATETIME OPERATOR RESPONSE: {agent_response}")

            # Log tool usage summary
            if "intermediate_steps" in result:
                steps = result["intermediate_steps"]
                if steps:
                    datetime_logger.info(f"🔍 DateTime agent used {len(steps)} tools:")
                    for i, (action, observation) in enumerate(steps, 1):
                        tool_name = action.tool
                        datetime_logger.info(
                            f"  Step {i}: {tool_name} -> {str(observation)[:100]}..."
                        )

            datetime_logger.info("📅 DateTime operator completed task successfully")

            return agent_response

    except Exception as e:
        error_msg = f"DateTime operator failed: {str(e)}"
        datetime_logger.error(f"💥 {error_msg}")
        logger.error(error_msg)
        return f"Error: {error_msg}"
