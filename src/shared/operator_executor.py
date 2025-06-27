import logging
from typing import Dict, Any, Callable, Optional
from langchain.agents import AgentExecutor

logger = logging.getLogger(__name__)


def execute_operator_with_tracing(
    operator_name: str,
    query: str,
    agent_factory_func: Callable[[], AgentExecutor],
    emoji: str = "🤖"
) -> str:
    """
    Execute an operator with standardized Langfuse tracing and error handling.
    
    Args:
        operator_name: Name of the operator (e.g., "math", "weather", "datetime")
        query: The task query to execute
        agent_factory_func: Function that creates and returns the agent executor
        emoji: Emoji for logging
        
    Returns:
        String response from the operator
    """
    operator_logger = logging.getLogger(f"operators.{operator_name.lower()}_operator_agent")
    operator_logger.info(f"{emoji} {operator_name.upper()} OPERATOR STARTING TASK: {query}")
    operator_logger.info("🔧 Creating specialized agent...")

    try:
        # Try with Langfuse tracing first
        try:
            from langfuse import get_client

            langfuse_client = get_client()

            # Create child span in current context
            with langfuse_client.start_as_current_span(
                name=f"{operator_name.lower()}_operator_execution",
                input={"task": query},
                metadata={
                    "operator_type": operator_name.lower(),
                    "task_description": query,
                    "agent_type": f"{operator_name.lower()}_specialist",
                },
            ) as operator_span:
                logger.info(f"✅ Created {operator_name.lower()} operator span")

                # Create agent using the factory function
                agent = agent_factory_func()
                operator_logger.info(f"✅ {operator_name} agent created successfully")

                # Execute the task
                operator_logger.info(f"📋 SENDING TASK TO {operator_name.upper()} AGENT: {query}")
                operator_logger.info(f"🚀 Executing {operator_name.lower()} task...")

                result = agent.invoke({"input": query})

                # Extract the output
                output = result.get("output", f"No response from {operator_name.lower()} operator")

                # Log intermediate steps if any
                intermediate_steps = result.get("intermediate_steps", [])
                if intermediate_steps:
                    operator_logger.info(f"🔍 {operator_name} agent used {len(intermediate_steps)} tools:")
                    for i, (action, observation) in enumerate(intermediate_steps):
                        operator_logger.info(f"  Step {i+1}: {action.tool} -> {str(observation)[:100]}...")

                # Log the final response
                operator_logger.info(f"{emoji} {operator_name.upper()} OPERATOR RESPONSE: {output}")

                # Update operator span with results
                operator_span.update(
                    output=output,
                    metadata={
                        "operator_type": operator_name.lower(),
                        "task_description": query,
                        "agent_type": f"{operator_name.lower()}_specialist",
                        "tools_used": len(result.get("intermediate_steps", [])),
                        "success": True,
                    },
                )
                logger.info(f"✅ Updated {operator_name.lower()} operator span")

                logger.info(f"{emoji} {operator_name} operator completed task successfully")
                return output

        except Exception as trace_error:
            logger.warning(f"Langfuse tracing not available: {trace_error}")

            # Fallback execution without tracing
            agent = agent_factory_func()
            operator_logger.info(f"✅ {operator_name} agent created successfully (fallback mode)")

            # Execute the task
            operator_logger.info(f"📋 SENDING TASK TO {operator_name.upper()} AGENT (FALLBACK): {query}")
            operator_logger.info(f"🚀 Executing {operator_name.lower()} task (fallback mode)...")

            result = agent.invoke({"input": query})

            # Extract the output
            output = result.get("output", f"No response from {operator_name.lower()} operator")

            # Log intermediate steps if any
            intermediate_steps = result.get("intermediate_steps", [])
            if intermediate_steps:
                operator_logger.info(f"🔍 {operator_name} agent used {len(intermediate_steps)} tools:")
                for i, (action, observation) in enumerate(intermediate_steps):
                    operator_logger.info(f"  Step {i+1}: {action.tool} -> {str(observation)[:100]}...")

            # Log the final response
            operator_logger.info(f"{emoji} {operator_name.upper()} OPERATOR RESPONSE (FALLBACK): {output}")

            logger.info(f"{emoji} {operator_name} operator completed task successfully")
            return output

    except Exception as e:
        error_msg = f"Error in {operator_name.lower()} operator: {str(e)}"
        operator_logger.error(f"💥 {error_msg}")
        logger.error(error_msg)
        return error_msg