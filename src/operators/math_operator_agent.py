import logging
from typing import Dict, Any, Optional, List
from langchain.agents import create_react_agent, AgentExecutor
from langchain.prompts import PromptTemplate
from langchain_mistralai import ChatMistralAI
from langchain.tools import tool
from langchain.callbacks.base import BaseCallbackHandler

from config import load_json_setting
from prompt_manager import get_prompt_manager
from tools.operators.math_operator import calculate, math_help
from tools import factory as tool_factory

logger = logging.getLogger(__name__)


class MathOperatorCallback(BaseCallbackHandler):
    """Callback handler for math operator internal actions."""

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger("operators.math_internal")

    def on_agent_action(self, action, **kwargs):
        """Called when math agent takes an action."""
        self.logger.info(f"🧮 MATH AGENT ACTION: {action.tool}")
        self.logger.info(f"📋 MATH AGENT PARAMETERS: {action.tool_input}")

    def on_tool_end(self, output, **kwargs):
        """Called when math tool ends."""
        self.logger.info(f"🔧 MATH TOOL RESPONSE: {str(output)[:200]}...")

    def on_text(self, text, **kwargs):
        """Called on math agent text - captures thinking."""
        if text and text.strip():
            text_stripped = text.strip()
            if text_stripped.startswith("Thought:"):
                thinking = text_stripped.replace("Thought:", "").strip()
                self.logger.info(f"💭 MATH AGENT THINKING: {thinking}")
            elif "I need" in text_stripped or "I should" in text_stripped:
                self.logger.info(f"🤔 MATH AGENT REASONING: {text_stripped}")

    def on_llm_start(self, serialized, prompts, **kwargs):
        """Called when math agent LLM starts."""
        if prompts and len(prompts) > 0:
            for i, prompt in enumerate(prompts):
                # Log a truncated version of the prompt sent to math operator
                if len(str(prompt)) > 300:
                    truncated = (
                        str(prompt)[:150] + "...[TRUNCATED]..." + str(prompt)[-100:]
                    )
                    self.logger.info(f"📝 MATH AGENT PROMPT #{i+1}: {truncated}")
                else:
                    self.logger.info(f"📝 MATH AGENT PROMPT #{i+1}: {prompt}")


def create_math_operator_agent(llm: ChatMistralAI) -> AgentExecutor:
    """
    Create a specialized math operator agent.

    Args:
        llm: Configured ChatMistralAI instance

    Returns:
        Configured AgentExecutor for mathematical operations
    """
    try:
        # Get math tools
        math_tools = [calculate, math_help]

        # Load math operator prompt
        prompt_manager = get_prompt_manager()
        system_prompt = prompt_manager.get_prompt("math_operator_system")

        # Create ReAct prompt template for math operator
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
- If you need multiple calculations, perform them one at a time across multiple responses

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
        agent = create_react_agent(llm=llm, tools=math_tools, prompt=prompt_template)

        # Create executor with callback
        executor = AgentExecutor(
            agent=agent,
            tools=math_tools,
            verbose=False,
            max_iterations=5,
            max_execution_time=120,
            return_intermediate_steps=True,
            handle_parsing_errors=True,
            callbacks=[MathOperatorCallback()],  # Add math-specific callback
        )

        logger.info("Math operator agent created successfully")
        return executor

    except Exception as e:
        logger.error(f"Error creating math operator agent: {str(e)}")
        raise RuntimeError(f"Failed to create math operator agent: {str(e)}")


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

    # Enhanced logging for math operator
    math_logger = logging.getLogger("operators.math_operator_agent")
    math_logger.info(f"📊 MATH OPERATOR STARTING TASK: {query}")
    math_logger.info("🔧 Creating specialized math agent...")

    try:
        # Use Langfuse 3.x context approach
        try:
            from langfuse import get_client

            langfuse_client = get_client()

            # Create child span in current context
            with langfuse_client.start_as_current_span(
                name="math_operator_execution",
                input={"task": query},
                metadata={
                    "operator_type": "math",
                    "task_description": query,
                    "agent_type": "math_specialist",
                },
            ) as operator_span:
                logger.info("✅ Created math operator span")

                # Create LLM for the math operator
                from config import get_global_settings

                settings = get_global_settings()
                model_config = load_json_setting("model_config")
                llm = ChatMistralAI(
                    model=settings.mistral_model,
                    temperature=model_config["temperature"],
                    max_tokens=model_config["max_tokens"],
                    timeout=model_config["timeout"],
                )

                # Create math operator agent
                math_agent = create_math_operator_agent(llm)
                math_logger.info("✅ Math agent created successfully")

                # Log the prompt that will be sent to the math operator
                math_logger.info(f"📋 SENDING TASK TO MATH AGENT: {query}")

                # Execute the task
                math_logger.info("🚀 Executing math task...")
                result = math_agent.invoke({"input": query})

                # Extract the output
                output = result.get("output", "No response from math operator")

                # Log intermediate steps if any
                intermediate_steps = result.get("intermediate_steps", [])
                if intermediate_steps:
                    math_logger.info(
                        f"🔍 Math agent used {len(intermediate_steps)} tools:"
                    )
                    for i, (action, observation) in enumerate(intermediate_steps):
                        math_logger.info(
                            f"  Step {i+1}: {action.tool} -> {str(observation)[:100]}..."
                        )

                # Log the final math operator response
                math_logger.info(f"🧮 MATH OPERATOR RESPONSE: {output}")

                # Update operator span with results
                operator_span.update(
                    output=output,
                    metadata={
                        "operator_type": "math",
                        "task_description": query,
                        "agent_type": "math_specialist",
                        "tools_used": len(result.get("intermediate_steps", [])),
                        "success": True,
                    },
                )
                logger.info("✅ Updated math operator span")

                logger.info("🧮 Math operator completed task successfully")
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

            # Create math operator agent
            math_agent = create_math_operator_agent(llm)
            math_logger.info("✅ Math agent created successfully (fallback mode)")

            # Log the prompt that will be sent to the math operator
            math_logger.info(f"📋 SENDING TASK TO MATH AGENT (FALLBACK): {query}")

            # Execute the task
            math_logger.info("🚀 Executing math task (fallback mode)...")
            result = math_agent.invoke({"input": query})

            # Extract the output
            output = result.get("output", "No response from math operator")

            # Log intermediate steps if any
            intermediate_steps = result.get("intermediate_steps", [])
            if intermediate_steps:
                math_logger.info(f"🔍 Math agent used {len(intermediate_steps)} tools:")
                for i, (action, observation) in enumerate(intermediate_steps):
                    math_logger.info(
                        f"  Step {i+1}: {action.tool} -> {str(observation)[:100]}..."
                    )

            # Log the final math operator response
            math_logger.info(f"🧮 MATH OPERATOR RESPONSE (FALLBACK): {output}")

            logger.info("🧮 Math operator completed task successfully")
            return output

    except Exception as e:
        error_msg = f"Error in math operator: {str(e)}"
        logger.error(error_msg)
        return error_msg
