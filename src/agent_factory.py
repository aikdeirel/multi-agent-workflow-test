import os
import importlib
import importlib.util
import logging
from typing import List, Any, Optional
from langchain.agents import create_react_agent, AgentExecutor
from langchain.prompts import PromptTemplate
from langchain_mistralai import ChatMistralAI
from langfuse import Langfuse

from config import load_json_setting
from prompt_manager import get_prompt_manager
from tools.factory import validate_tool

logger = logging.getLogger(__name__)


def discover_and_load_tools(
    operators_dir: str = "tools/operators", langfuse_client: Optional[Langfuse] = None
) -> List[Any]:
    """
    Dynamically discover and load tools from the operators directory.

    Args:
        operators_dir: Directory containing operator modules
        langfuse_client: Langfuse client for tool tracing

    Returns:
        List of loaded and validated tools
    """
    tools = []

    if not os.path.exists(operators_dir):
        logger.warning(f"Operators directory '{operators_dir}' does not exist")
        return tools

    # Find all Python files in operators directory
    for filename in os.listdir(operators_dir):
        if filename.endswith(".py") and filename != "__init__.py":
            module_name = filename[:-3]  # Remove .py extension
            module_path = os.path.join(operators_dir, filename)

            try:
                # Load module dynamically
                spec = importlib.util.spec_from_file_location(module_name, module_path)
                if spec is None or spec.loader is None:
                    logger.error(f"Could not load spec for module {module_name}")
                    continue

                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Look for tool functions in the module
                # Convention: functions decorated with @create_traced_tool become tools
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)

                    # Check if it's a tool (has LangChain tool attributes)
                    if (
                        hasattr(attr, "name")
                        and hasattr(attr, "description")
                        and callable(attr)
                    ):

                        # Validate the tool
                        if validate_tool(attr):
                            tools.append(attr)
                            logger.info(f"Loaded tool: {attr.name} from {module_name}")
                        else:
                            logger.error(
                                f"Tool validation failed for {attr_name} in {module_name}"
                            )

            except Exception as e:
                logger.error(f"Error loading operator module {module_name}: {str(e)}")
                continue

    logger.info(f"Successfully loaded {len(tools)} tools")
    return tools


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

        # Discover and load tools
        tools = discover_and_load_tools(langfuse_client=langfuse_client)

        if not tools:
            logger.warning("No tools loaded - agent will have limited functionality")

        # Create LLM (wrapped with @observe)
        llm = create_llm_from_config()

        # Create prompt template
        prompt = create_prompt_template()

        # Create ReAct agent (compatible with Mistral)
        agent = create_react_agent(llm=llm, tools=tools, prompt=prompt)

        # Create executor with basic configuration
        executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            max_iterations=10,
            max_execution_time=300,  # 5 minutes timeout
            return_intermediate_steps=True,
            handle_parsing_errors=True,
            # Add early stopping to prevent infinite loops
            early_stopping_method="generate",
        )

        logger.info("Orchestrator agent created successfully")
        logger.info(f"Agent configuration: {len(tools)} tools")

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
        tools_info = []
        if executor.tools:
            for tool in executor.tools:
                tools_info.append(
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
            "tools_count": len(executor.tools) if executor.tools else 0,
            "tools": tools_info,
            "max_iterations": getattr(executor, "max_iterations", "unknown"),
            "max_execution_time": getattr(executor, "max_execution_time", "unknown"),
            "verbose": getattr(executor, "verbose", False),
            "has_callbacks": callbacks_count > 0,
            "callbacks_count": callbacks_count,
        }

    except Exception as e:
        logger.error(f"Error getting agent info: {str(e)}")
        return {"error": str(e)}
