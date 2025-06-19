import logging
import asyncio
import uuid
import os
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from langfuse import Langfuse

from config import get_global_settings, load_json_setting
from agent_factory import create_orchestrator_agent, get_agent_info


class ColoredFormatter(logging.Formatter):
    """Custom formatter to add colors to log levels."""

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"  # Reset to default color

    def format(self, record):
        # Get the original formatted message
        log_message = super().format(record)

        # Add color to the log level
        level_name = record.levelname
        if level_name in self.COLORS:
            colored_level = f"{self.COLORS[level_name]}{level_name}{self.RESET}"
            # Replace the level name in the message with the colored version
            log_message = log_message.replace(level_name, colored_level, 1)

        return log_message


# Configure colorful logging
def setup_colored_logging():
    """Setup colorful logging configuration."""
    # Create colored formatter
    formatter = ColoredFormatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler with colored formatter
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)


# Setup colored logging
setup_colored_logging()
logger = logging.getLogger(__name__)

# Initialize Langfuse client early for @observe decorators
try:
    # Use environment variables directly for @observe decorators
    if os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"):
        # Langfuse Host should already be set in environment (cloud.langfuse.com)
        logger.info("Langfuse environment configured for @observe decorators")
    else:
        logger.warning("Langfuse keys not found in environment - tracing may not work")
except Exception as e:
    logger.warning(f"Error configuring Langfuse: {str(e)}")

# Global state for agent and components
app_state = {"agent_executor": None, "langfuse_client": None, "settings": None}


class InvokeRequest(BaseModel):
    """Request model for agent invocation."""

    input: str = Field(..., description="The user's input/query")
    session_id: Optional[str] = Field(
        None, description="Optional session ID for conversation tracking"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Optional metadata for the request"
    )


class InvokeResponse(BaseModel):
    """Response model for agent invocation."""

    output: str = Field(..., description="The agent's response")
    session_id: str = Field(..., description="Session ID for conversation tracking")
    request_id: str = Field(..., description="Unique identifier for this request")
    intermediate_steps: Optional[list] = Field(
        None, description="Intermediate steps taken by the agent"
    )
    metadata: Optional[Dict[str, Any]] = Field(None, description="Response metadata")


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(..., description="Error message")
    error_type: str = Field(..., description="Type of error")
    request_id: str = Field(..., description="Request ID for tracking")
    details: Optional[str] = Field(None, description="Additional error details")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown."""
    # Startup
    logger.info("Starting multi-agent system...")

    try:
        # Load settings
        settings = get_global_settings()
        app_state["settings"] = settings
        logger.info("Settings loaded successfully")

        # Configure logging level
        logging.getLogger().setLevel(getattr(logging, settings.log_level.upper()))

        # Initialize Langfuse cloud client
        try:
            langfuse_config = load_json_setting("langfuse_config")
            langfuse_client = Langfuse(
                public_key=settings.langfuse_public_key,
                secret_key=settings.langfuse_secret_key,
                host=settings.langfuse_host,  # Use cloud service
                flush_at=langfuse_config.get("flush_at", 10),
                flush_interval=langfuse_config.get("flush_interval", 1.0),
            )
            app_state["langfuse_client"] = langfuse_client
            logger.info(
                f"Langfuse client initialized with cloud host: {settings.langfuse_host}"
            )
        except Exception as e:
            logger.warning(f"Could not initialize Langfuse client: {str(e)}")
            logger.warning("Continuing without Langfuse integration")

        # Create agent executor
        agent_executor = create_orchestrator_agent(app_state["langfuse_client"])
        app_state["agent_executor"] = agent_executor

        # Log agent info
        agent_info = get_agent_info(agent_executor)
        logger.info(f"Agent created successfully: {agent_info}")

        logger.info("Multi-agent system startup complete")

    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        raise RuntimeError(f"Application startup failed: {str(e)}")

    yield

    # Shutdown
    logger.info("Shutting down multi-agent system...")

    # Cleanup Langfuse client
    if app_state["langfuse_client"]:
        try:
            app_state["langfuse_client"].flush()
            logger.info("Langfuse client flushed")
        except Exception as e:
            logger.error(f"Error flushing Langfuse client: {str(e)}")

    logger.info("Multi-agent system shutdown complete")


# Create FastAPI app with lifespan management
app = FastAPI(
    title="Multi-Agent System API",
    description="A self-hosted LangChain multi-agent system with Langfuse monitoring",
    version="1.0.0",
    lifespan=lifespan,
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    request_id = str(uuid.uuid4())
    logger.error(
        f"Unhandled exception in request {request_id}: {str(exc)}", exc_info=True
    )

    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            error_type=type(exc).__name__,
            request_id=request_id,
            details=(
                str(exc)
                if app_state["settings"]
                and app_state["settings"].log_level.upper() == "DEBUG"
                else None
            ),
        ).dict(),
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check if agent is available
        if not app_state["agent_executor"]:
            raise HTTPException(status_code=503, detail="Agent not initialized")

        # Get agent info for health details
        agent_info = get_agent_info(app_state["agent_executor"])

        return {
            "status": "healthy",
            "timestamp": "2024-01-01T00:00:00Z",  # This would normally be current time
            "agent_status": "ready",
            "tools_loaded": agent_info.get("tools_count", 0),
            "langfuse_enabled": app_state["langfuse_client"] is not None,
        }

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")


@app.get("/agent/info")
async def get_agent_information():
    """Get information about the current agent configuration."""
    try:
        if not app_state["agent_executor"]:
            raise HTTPException(status_code=503, detail="Agent not initialized")

        agent_info = get_agent_info(app_state["agent_executor"])
        return agent_info

    except Exception as e:
        logger.error(f"Error getting agent info: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error retrieving agent information: {str(e)}"
        )


@app.post("/invoke", response_model=InvokeResponse)
async def invoke_agent(request: InvokeRequest):
    """
    Invoke the agent with a user query.

    This endpoint accepts user input and processes it through the orchestrator agent,
    which may delegate to specialized tools as needed.
    """
    request_id = str(uuid.uuid4())
    session_id = request.session_id or str(uuid.uuid4())

    logger.info(f"Processing request {request_id} for session {session_id}")

    # Create Langfuse trace with proper hierarchy
    trace = None
    if app_state["langfuse_client"]:
        try:
            trace = app_state["langfuse_client"].trace(
                name="multi_agent_workflow",
                session_id=session_id,
                user_id=None,  # Could be added if you have user auth
                input=request.input,
                metadata={
                    "request_id": request_id,
                    "user_input": request.input,
                    "metadata": request.metadata,
                    "agent_type": "orchestrator",
                },
                tags=["agent", "orchestrator", "multi-agent-system"],
            )
            logger.debug(f"Created Langfuse trace: {trace.id}")
        except Exception as e:
            logger.warning(f"Failed to create Langfuse trace: {str(e)}")

    try:
        # Validate agent availability
        if not app_state["agent_executor"]:
            if trace:
                trace.update(
                    output={"error": "Agent not initialized"},
                    metadata={"status": "error", "error_type": "agent_not_available"},
                )
            raise HTTPException(status_code=503, detail="Agent not initialized")

        # Create agent execution span
        agent_span = None
        if trace:
            agent_span = trace.span(
                name="agent_execution",
                input={"query": request.input},
                metadata={"agent_type": "react_orchestrator"},
            )

        # Prepare agent input
        agent_input = {"input": request.input}

        # Add metadata if provided
        if request.metadata:
            agent_input["metadata"] = request.metadata

        logger.debug(f"Agent input: {agent_input}")

        # Execute agent with tracing context
        try:
            # Store trace in a way tools can access it
            if trace:
                # Use a simple global variable approach for tool access
                from tools import factory as tool_factory

                tool_factory._current_trace = trace
                logger.info(f"✅ Set global trace for tools: {trace.id}")

            # Create a simple callback to capture LLM interactions
            from langchain.callbacks.base import BaseCallbackHandler

            class LangfuseLLMCallback(BaseCallbackHandler):
                def __init__(self, parent_trace):
                    super().__init__()
                    self.parent_trace = parent_trace
                    self.llm_spans = []

                def on_llm_start(self, serialized, prompts, **kwargs):
                    if self.parent_trace:
                        try:
                            llm_span = self.parent_trace.span(
                                name="llm_call",
                                input={
                                    "prompts": prompts[:1000] if prompts else ""
                                },  # Truncate for readability
                                metadata={
                                    "model": "mistral-medium-latest",
                                    "type": "llm_generation",
                                    "serialized": str(serialized)[:200],
                                },
                            )
                            self.llm_spans.append(llm_span)
                            logger.info("✅ Created LLM span")
                        except Exception as e:
                            logger.error(f"❌ Failed to create LLM span: {e}")

                def on_llm_end(self, response, **kwargs):
                    if self.llm_spans:
                        try:
                            llm_span = self.llm_spans.pop()
                            # Extract basic response info
                            output_text = ""
                            if (
                                hasattr(response, "generations")
                                and response.generations
                            ):
                                output_text = str(response.generations[0])[
                                    :500
                                ]  # Truncate

                            llm_span.update(
                                output=output_text,
                                metadata={
                                    "model": "mistral-medium-latest",
                                    "type": "llm_generation",
                                    "status": "completed",
                                },
                            )
                            logger.info("✅ Updated LLM span")
                        except Exception as e:
                            logger.error(f"❌ Failed to update LLM span: {e}")

                def on_llm_error(self, error, **kwargs):
                    if self.llm_spans:
                        try:
                            llm_span = self.llm_spans.pop()
                            llm_span.update(
                                output={"error": str(error)},
                                metadata={
                                    "model": "mistral-medium-latest",
                                    "type": "llm_generation",
                                    "status": "error",
                                },
                            )
                            logger.info("✅ Updated LLM span with error")
                        except Exception as e:
                            logger.error(
                                f"❌ Failed to update LLM span with error: {e}"
                            )

            # Set up LLM callback if we have tracing
            callbacks = []
            if trace:
                callbacks = [LangfuseLLMCallback(trace)]

            result = await asyncio.to_thread(
                lambda: app_state["agent_executor"].invoke(
                    agent_input, config={"callbacks": callbacks} if callbacks else None
                )
            )

            # Clean up global trace reference
            if trace:
                tool_factory._current_trace = None
                logger.info("🧹 Cleaned up global trace reference")

            # Update agent span with results
            if agent_span:
                agent_span.update(
                    output=result.get("output", "No response generated"),
                    metadata={
                        "tools_used": len(result.get("intermediate_steps", [])),
                        "status": "success",
                    },
                )

            # Update main trace with success
            if trace:
                trace.update(
                    output=result.get("output", "No response generated"),
                    metadata={
                        "status": "success",
                        "tools_used": len(result.get("intermediate_steps", [])),
                        "intermediate_steps_count": len(
                            result.get("intermediate_steps", [])
                        ),
                    },
                )

        except Exception as e:
            # Update spans and trace with error
            if agent_span:
                agent_span.update(metadata={"status": "error", "error": str(e)})
            if trace:
                trace.update(metadata={"status": "error", "error": str(e)})

            logger.error(f"Agent execution failed for request {request_id}: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Agent execution failed: {str(e)}"
            )

        # Extract response data
        output = result.get("output", "No response generated")
        intermediate_steps = result.get("intermediate_steps", [])

        # Create response
        response = InvokeResponse(
            output=output,
            session_id=session_id,
            request_id=request_id,
            intermediate_steps=intermediate_steps if intermediate_steps else None,
            metadata={
                "processing_time": "N/A",  # Would normally calculate this
                "tools_used": len(intermediate_steps) if intermediate_steps else 0,
                "langfuse_enabled": app_state["langfuse_client"] is not None,
                "trace_id": trace.id if trace else None,
            },
        )

        logger.info(f"Request {request_id} completed successfully")
        return response

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Update trace with unexpected error
        if trace:
            try:
                trace.update(
                    metadata={
                        "status": "unexpected_error",
                        "error": str(e),
                        "error_type": type(e).__name__,
                    }
                )
            except Exception as trace_error:
                logger.warning(
                    f"Failed to update Langfuse trace with unexpected error: {str(trace_error)}"
                )

        logger.error(
            f"Unexpected error processing request {request_id}: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


if __name__ == "__main__":
    # Run the application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disabled since we use watchmedo for hot-reload
        log_level="info",
    )
