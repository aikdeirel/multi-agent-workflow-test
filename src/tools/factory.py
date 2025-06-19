import time
import functools
import logging
from typing import Callable, Any, Dict, Optional
from langchain.tools import tool
from langfuse import Langfuse

logger = logging.getLogger(__name__)

# Global variable to store current trace for tool access
_current_trace = None


def create_traced_tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
    langfuse_client: Optional[Langfuse] = None,
):
    """
    Decorator for creating LangChain tools with seamless Langfuse integration.

    This decorator automatically:
    - Creates Langfuse spans for tool execution within the parent trace
    - Extracts tool names and descriptions from docstrings
    - Handles errors and logs them appropriately
    - Records execution metadata (timing, input/output sizes)

    Args:
        name: Tool name (if not provided, uses function name)
        description: Tool description (if not provided, uses function docstring)
        langfuse_client: Langfuse client instance for tracing

    Returns:
        Decorated function that can be used as a LangChain tool
    """

    def decorator(func: Callable) -> Callable:
        # Extract name and description from function if not provided
        tool_name = name or func.__name__
        tool_description = description or (func.__doc__ or f"Tool: {tool_name}").strip()

        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Start timing
            start_time = time.time()

            # Prepare input data
            input_data = {"args": args, "kwargs": kwargs}

            try:
                # Get parent trace from global variable
                parent_trace = _current_trace
                logger.debug(
                    f"Tool {tool_name}: Found parent trace: {parent_trace is not None}"
                )

                # Create tool span within parent trace if available
                tool_span = None
                if parent_trace:
                    try:
                        tool_span = parent_trace.span(
                            name=f"tool_{tool_name}",
                            input=input_data,
                            metadata={
                                "tool_name": tool_name,
                                "tool_description": tool_description,
                                "function_name": func.__name__,
                                "tool_type": "operator",
                            },
                        )
                        logger.info(f"✅ Created tool span for {tool_name}")
                    except Exception as e:
                        logger.error(
                            f"❌ Failed to create tool span for {tool_name}: {e}"
                        )
                else:
                    logger.warning(f"⚠️ No parent trace available for tool {tool_name}")

                # Execute the function
                result = func(*args, **kwargs)

                # Calculate execution time
                execution_time = time.time() - start_time

                # Update tool span with results
                if tool_span:
                    try:
                        tool_span.update(
                            output=result,
                            metadata={
                                "tool_name": tool_name,
                                "tool_description": tool_description,
                                "function_name": func.__name__,
                                "execution_time_seconds": execution_time,
                                "input_size": len(str(input_data)),
                                "output_size": len(str(result)) if result else 0,
                                "success": True,
                                "tool_type": "operator",
                            },
                        )
                        logger.info(f"✅ Updated tool span for {tool_name}")
                    except Exception as e:
                        logger.error(
                            f"❌ Failed to update tool span for {tool_name}: {e}"
                        )

                logger.info(
                    f"Tool '{tool_name}' executed successfully in {execution_time:.3f}s"
                )
                return result

            except Exception as e:
                execution_time = time.time() - start_time
                error_msg = str(e)

                logger.error(
                    f"Tool '{tool_name}' failed after {execution_time:.3f}s: {error_msg}"
                )

                # Update tool span with error
                if tool_span:
                    try:
                        tool_span.update(
                            output={"error": error_msg},
                            metadata={
                                "tool_name": tool_name,
                                "tool_description": tool_description,
                                "function_name": func.__name__,
                                "execution_time_seconds": execution_time,
                                "success": False,
                                "error_type": type(e).__name__,
                                "tool_type": "operator",
                            },
                        )
                    except Exception as trace_error:
                        logger.error(
                            f"Failed to update tool span with error: {trace_error}"
                        )

                # Re-raise the original exception
                raise e

        # Create the LangChain tool using the @tool decorator
        # Use the decorator approach without problematic keyword arguments
        @tool
        def langchain_tool_func(*args, **kwargs):
            return wrapper(*args, **kwargs)

        # Set the name and description after creation
        langchain_tool_func.name = tool_name
        langchain_tool_func.description = tool_description

        langchain_tool = langchain_tool_func

        # Add metadata to the tool for inspection
        langchain_tool._original_function = func
        langchain_tool._tool_name = tool_name
        langchain_tool._tool_description = tool_description

        return langchain_tool

    return decorator


def get_tool_metadata(tool_instance) -> Dict[str, Any]:
    """
    Extract metadata from a traced tool instance.

    Args:
        tool_instance: Tool instance created with @create_traced_tool

    Returns:
        Dictionary containing tool metadata
    """
    return {
        "name": getattr(tool_instance, "_tool_name", tool_instance.name),
        "description": getattr(
            tool_instance, "_tool_description", tool_instance.description
        ),
        "function_name": getattr(tool_instance, "_original_function", {}).get(
            "__name__", "unknown"
        ),
        "has_tracing": hasattr(tool_instance, "_original_function"),
    }


def validate_tool(tool_instance) -> bool:
    """
    Validate that a tool instance is properly configured.

    Args:
        tool_instance: Tool instance to validate

    Returns:
        True if tool is valid, False otherwise
    """
    try:
        # Check basic attributes
        if not hasattr(tool_instance, "name") or not tool_instance.name:
            logger.error("Tool missing name attribute")
            return False

        if not hasattr(tool_instance, "description") or not tool_instance.description:
            logger.error(f"Tool '{tool_instance.name}' missing description")
            return False

        if not callable(tool_instance):
            logger.error(f"Tool '{tool_instance.name}' is not callable")
            return False

        logger.debug(f"Tool '{tool_instance.name}' validation passed")
        return True

    except Exception as e:
        logger.error(f"Tool validation failed: {str(e)}")
        return False
