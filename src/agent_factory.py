import os
import importlib
import importlib.util
import logging
from typing import List, Any, Optional
from langchain.agents import create_react_agent, AgentExecutor
from langchain.prompts import PromptTemplate
from langchain_mistralai import ChatMistralAI
from langfuse import Langfuse
from langchain.callbacks.base import BaseCallbackHandler

from config import load_json_setting
from prompt_manager import get_prompt_manager
from operators.weather_operator_agent import weather_operator
from operators.math_operator_agent import math_operator

logger = logging.getLogger(__name__)


class ProperLoggingCallback(BaseCallbackHandler):
    """Custom callback handler for agent actions with rich verbose output and proper formatting."""

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger("agent_executor")

    def on_chain_start(self, serialized, inputs, **kwargs):
        """Called when chain starts."""
        self.logger.info("")
        self.logger.info("🚀 \033[1;36m> Entering new AgentExecutor chain...\033[0m")

    def on_agent_action(self, action, **kwargs):
        """Called when agent takes an action."""
        self.logger.info(f"\033[1;32mAction:\033[0m {action.tool}")
        self.logger.info(f"\033[1;32mAction Input:\033[0m {action.tool_input}")

    def on_tool_start(self, serialized, input_str, **kwargs):
        """Called when tool starts."""
        tool_name = serialized.get("name", "Unknown Tool")
        self.logger.info(f"\033[1;33m⚡ Starting operator '{tool_name}'\033[0m")

    def on_tool_end(self, output, **kwargs):
        """Called when tool ends."""
        # Format tool output with proper line breaks and color
        formatted_output = str(output).strip()
        self.logger.info(f"\033[1;34mObservation:\033[0m {formatted_output}")

    def on_tool_error(self, error, **kwargs):
        """Called when tool encounters an error."""
        self.logger.error(f"\033[1;31m❌ Operator error:\033[0m {str(error)}")

    def on_agent_finish(self, finish, **kwargs):
        """Called when agent finishes."""
        final_output = finish.return_values.get("output", "No output")
        self.logger.info(f"\033[1;35mFinal Answer:\033[0m {final_output}")

    def on_chain_end(self, outputs, **kwargs):
        """Called when chain ends."""
        self.logger.info("")
        self.logger.info("✅ \033[1;36m> Finished chain.\033[0m")

    def on_text(self, text, **kwargs):
        """Called on arbitrary text - this captures the agent's thinking."""
        # Only log non-empty text that's not just whitespace
        if text and text.strip():
            text_stripped = text.strip()
            # Filter out some verbose internal text but keep the thinking
            if not any(skip in text_stripped for skip in ["Invoking:", "Got output"]):
                # Check if this is a "Thought:" line and color it appropriately
                if text_stripped.startswith("Thought:"):
                    self.logger.info(f"\033[1;37m{text_stripped}\033[0m")
                else:
                    self.logger.info(f"{text_stripped}")

    def on_llm_start(self, serialized, prompts, **kwargs):
        """Called when LLM starts."""
        self.logger.debug("\033[1;90m🧠 LLM thinking...\033[0m")

    def on_llm_end(self, response, **kwargs):
        """Called when LLM ends."""
        self.logger.debug("\033[1;90m💭 LLM response received\033[0m")


def get_operator_agents() -> List[Any]:
    """
    Get the available operator agent tools.

    Returns:
        List of operator agent tools
    """
    try:
        # Return the operator agent tools
        operators = [weather_operator, math_operator]

        logger.info(f"Loaded {len(operators)} operator agents:")
        for op in operators:
            logger.info(f"  - {op.name}: {op.description[:100]}...")

        return operators

    except Exception as e:
        logger.error(f"Error loading operator agents: {str(e)}")
        return []


def create_llm_from_config() -> ChatMistralAI:
    """
    Create and configure the LLM based on JSON configuration.

    Returns:
        Configured ChatMistralAI instance

    Raises:
        ValueError: If configuration is invalid
        RuntimeError: If LLM creation fails
    """
    try:
        # Load model configuration
        model_config = load_json_setting("model_config")

        # Validate required configuration
        required_keys = ["model_name", "temperature", "max_tokens", "timeout"]
        missing_keys = [key for key in required_keys if key not in model_config]
        if missing_keys:
            raise ValueError(
                f"Missing required model configuration keys: {missing_keys}"
            )

        # Create LLM instance with Mistral-compatible configuration
        # Note: We'll handle LLM tracing manually within our main trace rather than using callbacks
        llm = ChatMistralAI(
            model=model_config["model_name"],
            temperature=model_config["temperature"],
            max_tokens=model_config["max_tokens"],
            timeout=model_config["timeout"],
        )

        logger.info(
            f"Created LLM with model: {model_config['model_name']} (manual tracing)"
        )
        return llm

    except Exception as e:
        logger.error(f"Error creating LLM: {str(e)}")
        raise RuntimeError(f"Failed to create LLM: {str(e)}")


def create_prompt_template(
    system_prompt_name: str = "main_orchestrator_system",
) -> PromptTemplate:
    """
    Create prompt template using the prompt manager for ReAct agent.

    Args:
        system_prompt_name: Name of the system prompt file

    Returns:
        Configured PromptTemplate

    Raises:
        RuntimeError: If prompt template creation fails
    """
    try:
        # Get prompt manager and load system prompt
        prompt_manager = get_prompt_manager()
        system_prompt = prompt_manager.get_prompt(system_prompt_name)

        # Create ReAct prompt template
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

CRITICAL SINGLE-ACTION RULES FOR ORCHESTRATOR:
- YOU CAN ONLY PERFORM ONE DELEGATION AT A TIME
- NEVER combine multiple Action/Action Input pairs in a single response
- After generating Action and Action Input, STOP and wait for the Observation
- Do NOT write multiple delegations like "Action: ... Action: ..." in the same response
- Do NOT include placeholder text like "(After receiving...)" or "(Then I'll...)"
- Each response must contain EITHER one Action OR one Final Answer, NEVER both
- If you need multiple operators, delegate to them one at a time across multiple responses

IMPORTANT RULES:
- You must EITHER generate an Action OR a Final Answer, NEVER both in the same response
- If you need to use a tool, generate Action and Action Input, then wait for Observation
- Only generate Final Answer when you have all the information needed to answer the question
- Do not include example text like "[After receiving the tool response]" in your actual response

Begin!

Question: {{input}}
Thought:{{agent_scratchpad}}"""

        prompt_template = PromptTemplate.from_template(react_template)

        logger.info(
            f"Created ReAct prompt template with system prompt: {system_prompt_name}"
        )
        return prompt_template

    except Exception as e:
        logger.error(f"Error creating prompt template: {str(e)}")
        raise RuntimeError(f"Failed to create prompt template: {str(e)}")


def create_orchestrator_agent(
    langfuse_client: Optional[Langfuse] = None,
) -> AgentExecutor:
    """
    Create the main orchestrator agent with all components configured.

    Args:
        langfuse_client: Langfuse client instance for tracing

    Returns:
        Configured AgentExecutor ready for use

    Raises:
        RuntimeError: If agent creation fails
    """
    try:
        logger.info("Starting orchestrator agent creation")

        # Initialize Langfuse client (the @observe decorator will handle tracing)
        if not langfuse_client:
            try:
                langfuse_config = load_json_setting("langfuse_config")
                langfuse_client = Langfuse(
                    host="http://langfuse:3000",  # Use service name from inside container
                    public_key=os.getenv(langfuse_config["public_key_env"]),
                    secret_key=os.getenv(langfuse_config["secret_key_env"]),
                    flush_at=langfuse_config.get("flush_at", 10),
                    flush_interval=langfuse_config.get("flush_interval", 1.0),
                )
                logger.info(
                    "Langfuse client initialized in agent_factory with service host"
                )
            except Exception as e:
                logger.warning(f"Could not initialize Langfuse client: {str(e)}")

        # Get operator agents instead of individual tools
        operators = get_operator_agents()

        if not operators:
            logger.warning(
                "No operator agents loaded - agent will have limited functionality"
            )

        # Create LLM (wrapped with @observe)
        llm = create_llm_from_config()

        # Create prompt template
        prompt = create_prompt_template()

        # Create ReAct agent (compatible with Mistral)
        agent = create_react_agent(llm=llm, tools=operators, prompt=prompt)

        # Create executor with basic configuration
        executor = AgentExecutor(
            agent=agent,
            tools=operators,
            verbose=False,  # Disable built-in verbose to use our custom callback
            max_iterations=10,
            max_execution_time=300,  # 5 minutes timeout
            return_intermediate_steps=True,
            handle_parsing_errors=True,
            callbacks=[ProperLoggingCallback()],  # Add our custom callback
        )

        logger.info("Orchestrator agent created successfully")
        logger.info(f"Agent configuration: {len(operators)} operator agents")

        return executor

    except Exception as e:
        logger.error(f"Error creating orchestrator agent: {str(e)}")
        raise RuntimeError(f"Failed to create orchestrator agent: {str(e)}")


def get_agent_info(executor: AgentExecutor) -> dict:
    """
    Get information about the agent executor.

    Args:
        executor: AgentExecutor instance

    Returns:
        Dictionary containing agent information
    """
    try:
        operators_info = []
        if executor.tools:
            for tool in executor.tools:
                operators_info.append(
                    {
                        "name": tool.name,
                        "description": (
                            tool.description[:100] + "..."
                            if tool.description and len(tool.description) > 100
                            else tool.description
                        ),
                    }
                )

        # Safely handle callbacks - they might be None
        callbacks_count = 0
        if hasattr(executor, "callbacks") and executor.callbacks is not None:
            callbacks_count = len(executor.callbacks)

        return {
            "operators_count": len(executor.tools) if executor.tools else 0,
            "operators": operators_info,
            "max_iterations": getattr(executor, "max_iterations", "unknown"),
            "max_execution_time": getattr(executor, "max_execution_time", "unknown"),
            "verbose": getattr(executor, "verbose", False),
            "has_callbacks": callbacks_count > 0,
            "callbacks_count": callbacks_count,
        }

    except Exception as e:
        logger.error(f"Error getting agent info: {str(e)}")
        return {"error": str(e)}
