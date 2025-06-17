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

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
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

    # Create Langfuse trace manually (v2 approach)
    trace = None
    if app_state["langfuse_client"]:
        try:
            trace = app_state["langfuse_client"].trace(
                name="agent_invoke",
                session_id=session_id,
                user_id=None,  # Could be added if you have user auth
                metadata={
                    "request_id": request_id,
                    "user_input": (
                        request.input[:100] + "..."
                        if len(request.input) > 100
                        else request.input
                    ),
                    "metadata": request.metadata,
                },
            )
            logger.debug(f"Created Langfuse trace: {trace.id}")
        except Exception as e:
            logger.warning(f"Failed to create Langfuse trace: {str(e)}")

    try:
        # Validate agent availability
        if not app_state["agent_executor"]:
            raise HTTPException(status_code=503, detail="Agent not initialized")

        # Prepare agent input
        agent_input = {"input": request.input}

        # Add metadata if provided
        if request.metadata:
            agent_input["metadata"] = request.metadata

        logger.debug(f"Agent input: {agent_input}")

        # Execute agent
        try:
            result = await asyncio.to_thread(
                app_state["agent_executor"].invoke, agent_input
            )

            # Update trace with success
            if trace:
                try:
                    trace.update(
                        output=result.get("output", "No response generated")[
                            :500
                        ],  # Truncate long outputs
                        metadata={
                            "status": "success",
                            "tools_used": len(result.get("intermediate_steps", [])),
                        },
                    )
                except Exception as e:
                    logger.warning(f"Failed to update Langfuse trace: {str(e)}")

        except Exception as e:
            # Update trace with error
            if trace:
                try:
                    trace.update(metadata={"status": "error", "error": str(e)})
                except Exception as trace_error:
                    logger.warning(
                        f"Failed to update Langfuse trace with error: {str(trace_error)}"
                    )

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
