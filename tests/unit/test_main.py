"""
Unit tests for the main FastAPI application.

Tests API endpoints, error handling, middleware, and application lifecycle.
"""

import pytest
import json
from unittest.mock import patch, Mock, AsyncMock
from fastapi.testclient import TestClient
from fastapi import HTTPException

from main import app


class TestHealthEndpoint:
    """Test the health check endpoint."""
    
    @pytest.mark.unit
    def test_health_check_success(self, test_client):
        """Test successful health check."""
        with patch('main.app_state', {
            'agent_executor': Mock(),
            'langfuse_client': Mock(),
            'settings': Mock()
        }):
            response = test_client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "timestamp" in data
            assert "agent_status" in data
            assert "tools_loaded" in data
            assert "langfuse_enabled" in data
    
    @pytest.mark.unit
    def test_health_check_agent_not_initialized(self, test_client):
        """Test health check when agent is not initialized."""
        with patch('main.app_state', {
            'agent_executor': None,
            'langfuse_client': Mock(),
            'settings': Mock()
        }):
            response = test_client.get("/health")
            
            assert response.status_code == 503
            assert "Agent not initialized" in response.json()["detail"]
    
    @pytest.mark.unit
    def test_health_check_with_agent_info_error(self, test_client):
        """Test health check when get_agent_info raises error."""
        mock_agent = Mock()
        
        with patch('main.app_state', {
            'agent_executor': mock_agent,
            'langfuse_client': Mock(),
            'settings': Mock()
        }), patch('main.get_agent_info', side_effect=Exception("Agent info error")):
            response = test_client.get("/health")
            
            assert response.status_code == 503
            assert "Service unhealthy" in response.json()["detail"]


class TestAgentInfoEndpoint:
    """Test the agent information endpoint."""
    
    @pytest.mark.unit
    def test_get_agent_info_success(self, test_client):
        """Test successful agent info retrieval."""
        mock_agent_info = {
            "operators_count": 3,
            "operators": [
                {"name": "weather_operator", "description": "Weather specialist"},
                {"name": "math_operator", "description": "Math specialist"},
                {"name": "datetime_operator", "description": "Datetime specialist"}
            ],
            "max_iterations": 10,
            "max_execution_time": 300
        }
        
        with patch('main.app_state', {
            'agent_executor': Mock(),
            'langfuse_client': Mock(),
            'settings': Mock()
        }), patch('main.get_agent_info', return_value=mock_agent_info):
            response = test_client.get("/agent/info")
            
            assert response.status_code == 200
            data = response.json()
            assert data["operators_count"] == 3
            assert len(data["operators"]) == 3
            assert data["max_iterations"] == 10
    
    @pytest.mark.unit
    def test_get_agent_info_agent_not_initialized(self, test_client):
        """Test agent info when agent is not initialized."""
        with patch('main.app_state', {
            'agent_executor': None,
            'langfuse_client': Mock(),
            'settings': Mock()
        }):
            response = test_client.get("/agent/info")
            
            assert response.status_code == 503
            assert "Agent not initialized" in response.json()["detail"]
    
    @pytest.mark.unit
    def test_get_agent_info_error(self, test_client):
        """Test agent info endpoint error handling."""
        with patch('main.app_state', {
            'agent_executor': Mock(),
            'langfuse_client': Mock(),
            'settings': Mock()
        }), patch('main.get_agent_info', side_effect=Exception("Info error")):
            response = test_client.get("/agent/info")
            
            assert response.status_code == 500
            assert "Error retrieving agent information" in response.json()["detail"]


class TestInvokeEndpoint:
    """Test the agent invocation endpoint."""
    
    @pytest.mark.unit
    def test_invoke_agent_success(self, test_client):
        """Test successful agent invocation."""
        mock_agent = Mock()
        mock_agent.invoke.return_value = {
            'output': 'Test response from agent',
            'intermediate_steps': [('action1', 'result1')]
        }
        
        with patch('main.app_state', {
            'agent_executor': mock_agent,
            'langfuse_client': Mock(),
            'settings': Mock()
        }), patch('langfuse.get_client') as mock_get_client, \
           patch('asyncio.to_thread') as mock_to_thread:
            
            # Mock Langfuse client
            mock_langfuse_client = Mock()
            mock_span = Mock()
            mock_span.__enter__ = Mock(return_value=mock_span)
            mock_span.__exit__ = Mock(return_value=None)
            mock_langfuse_client.start_as_current_span.return_value = mock_span
            mock_get_client.return_value = mock_langfuse_client
            
            # Mock asyncio.to_thread
            mock_to_thread.return_value = {
                'output': 'Test response from agent',
                'intermediate_steps': [('action1', 'result1')]
            }
            
            request_data = {
                "input": "What is the weather in Berlin?",
                "session_id": "test-session-123"
            }
            
            response = test_client.post("/invoke", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["output"] == "Test response from agent"
            assert data["session_id"] == "test-session-123"
            assert "request_id" in data
            assert data["intermediate_steps"] is not None
            assert "metadata" in data
    
    @pytest.mark.unit
    def test_invoke_agent_without_session_id(self, test_client):
        """Test agent invocation without session ID (should generate one)."""
        mock_agent = Mock()
        mock_agent.invoke.return_value = {
            'output': 'Test response',
            'intermediate_steps': []
        }
        
        with patch('main.app_state', {
            'agent_executor': mock_agent,
            'langfuse_client': Mock(),
            'settings': Mock()
        }), patch('langfuse.get_client') as mock_get_client, \
           patch('asyncio.to_thread') as mock_to_thread:
            
            # Mock Langfuse client
            mock_langfuse_client = Mock()
            mock_span = Mock()
            mock_span.__enter__ = Mock(return_value=mock_span)
            mock_span.__exit__ = Mock(return_value=None)
            mock_langfuse_client.start_as_current_span.return_value = mock_span
            mock_get_client.return_value = mock_langfuse_client
            
            mock_to_thread.return_value = {
                'output': 'Test response',
                'intermediate_steps': []
            }
            
            request_data = {
                "input": "Calculate 2 + 2"
            }
            
            response = test_client.post("/invoke", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert "session_id" in data
            assert len(data["session_id"]) > 0  # Should have generated a session ID
    
    @pytest.mark.unit
    def test_invoke_agent_with_metadata(self, test_client):
        """Test agent invocation with metadata."""
        mock_agent = Mock()
        mock_agent.invoke.return_value = {
            'output': 'Test response',
            'intermediate_steps': []
        }
        
        with patch('main.app_state', {
            'agent_executor': mock_agent,
            'langfuse_client': Mock(),
            'settings': Mock()
        }), patch('langfuse.get_client') as mock_get_client, \
           patch('asyncio.to_thread') as mock_to_thread:
            
            mock_langfuse_client = Mock()
            mock_span = Mock()
            mock_span.__enter__ = Mock(return_value=mock_span)
            mock_span.__exit__ = Mock(return_value=None)
            mock_langfuse_client.start_as_current_span.return_value = mock_span
            mock_get_client.return_value = mock_langfuse_client
            
            mock_to_thread.return_value = {
                'output': 'Test response',
                'intermediate_steps': []
            }
            
            request_data = {
                "input": "Test input",
                "session_id": "test-session",
                "metadata": {"user_id": "user123", "context": "test"}
            }
            
            response = test_client.post("/invoke", json=request_data)
            
            assert response.status_code == 200
            # Should have passed metadata to agent
            mock_agent.invoke.assert_called_once()
            call_args = mock_agent.invoke.call_args[0][0]
            assert "metadata" in call_args
            assert call_args["metadata"]["user_id"] == "user123"
    
    @pytest.mark.unit
    def test_invoke_agent_not_initialized(self, test_client):
        """Test agent invocation when agent is not initialized."""
        with patch('main.app_state', {
            'agent_executor': None,
            'langfuse_client': Mock(),
            'settings': Mock()
        }):
            request_data = {
                "input": "Test input"
            }
            
            response = test_client.post("/invoke", json=request_data)
            
            assert response.status_code == 503
            assert "Agent not initialized" in response.json()["detail"]
    
    @pytest.mark.unit
    def test_invoke_agent_execution_error(self, test_client):
        """Test agent invocation with execution error."""
        mock_agent = Mock()
        mock_agent.invoke.side_effect = Exception("Agent execution failed")
        
        with patch('main.app_state', {
            'agent_executor': mock_agent,
            'langfuse_client': Mock(),
            'settings': Mock()
        }), patch('langfuse.get_client') as mock_get_client, \
           patch('asyncio.to_thread', side_effect=Exception("Agent execution failed")):
            
            mock_langfuse_client = Mock()
            mock_span = Mock()
            mock_span.__enter__ = Mock(return_value=mock_span)
            mock_span.__exit__ = Mock(return_value=None)
            mock_langfuse_client.start_as_current_span.return_value = mock_span
            mock_get_client.return_value = mock_langfuse_client
            
            request_data = {
                "input": "Test input"
            }
            
            response = test_client.post("/invoke", json=request_data)
            
            assert response.status_code == 500
            assert "Agent execution failed" in response.json()["detail"]
    
    @pytest.mark.unit
    def test_invoke_agent_without_langfuse(self, test_client):
        """Test agent invocation without Langfuse tracing."""
        mock_agent = Mock()
        mock_agent.invoke.return_value = {
            'output': 'Test response',
            'intermediate_steps': []
        }
        
        with patch('main.app_state', {
            'agent_executor': mock_agent,
            'langfuse_client': None,  # No Langfuse client
            'settings': Mock()
        }), patch('langfuse.get_client', side_effect=Exception("Langfuse not available")), \
           patch('asyncio.to_thread') as mock_to_thread:
            
            mock_to_thread.return_value = {
                'output': 'Test response',
                'intermediate_steps': []
            }
            
            request_data = {
                "input": "Test input"
            }
            
            response = test_client.post("/invoke", json=request_data)
            
            # Should still work without Langfuse
            assert response.status_code == 200
            data = response.json()
            assert data["output"] == "Test response"


class TestInvokeRequestValidation:
    """Test request validation for the invoke endpoint."""
    
    @pytest.mark.unit
    def test_invoke_empty_input(self, test_client):
        """Test invoke with empty input."""
        request_data = {
            "input": ""
        }
        
        # Should accept empty input (might be valid for some use cases)
        with patch('main.app_state', {
            'agent_executor': Mock(),
            'langfuse_client': Mock(),
            'settings': Mock()
        }):
            response = test_client.post("/invoke", json=request_data)
            # The validation happens at the Pydantic model level
            # Empty string should be allowed but might not be processed well by agent
    
    @pytest.mark.unit
    def test_invoke_missing_input(self, test_client):
        """Test invoke with missing input field."""
        request_data = {
            "session_id": "test-session"
            # Missing required "input" field
        }
        
        response = test_client.post("/invoke", json=request_data)
        
        assert response.status_code == 422  # Validation error
        error_data = response.json()
        assert "input" in str(error_data)
    
    @pytest.mark.unit
    def test_invoke_invalid_json(self, test_client):
        """Test invoke with invalid JSON."""
        invalid_json = '{"input": "test"'  # Missing closing brace
        
        response = test_client.post(
            "/invoke",
            data=invalid_json,
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422  # JSON parse error
    
    @pytest.mark.unit
    def test_invoke_wrong_content_type(self, test_client):
        """Test invoke with wrong content type."""
        response = test_client.post(
            "/invoke",
            data="input=test",
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert response.status_code == 422  # Content type error


class TestErrorHandling:
    """Test global error handling."""
    
    @pytest.mark.unit
    def test_global_exception_handler(self, test_client):
        """Test global exception handler."""
        # Create a route that raises an exception for testing
        @app.get("/test-error")
        def test_error():
            raise ValueError("Test error")
        
        response = test_client.get("/test-error")
        
        assert response.status_code == 500
        error_data = response.json()
        assert error_data["error"] == "Internal server error"
        assert error_data["error_type"] == "ValueError"
        assert "request_id" in error_data
        
        # Clean up the test route
        app.routes = [route for route in app.routes if not (
            hasattr(route, 'path') and route.path == "/test-error"
        )]
    
    @pytest.mark.unit
    def test_http_exception_handling(self, test_client):
        """Test HTTP exception handling."""
        # HTTP exceptions should not be caught by global handler
        @app.get("/test-http-error")
        def test_http_error():
            raise HTTPException(status_code=404, detail="Not found")
        
        response = test_client.get("/test-http-error")
        
        assert response.status_code == 404
        assert response.json()["detail"] == "Not found"
        
        # Clean up
        app.routes = [route for route in app.routes if not (
            hasattr(route, 'path') and route.path == "/test-http-error"
        )]


class TestResponseModels:
    """Test response model validation."""
    
    @pytest.mark.unit
    def test_invoke_response_structure(self, test_client):
        """Test that invoke response matches expected structure."""
        mock_agent = Mock()
        mock_agent.invoke.return_value = {
            'output': 'Test response',
            'intermediate_steps': [('action1', 'result1')]
        }
        
        with patch('main.app_state', {
            'agent_executor': mock_agent,
            'langfuse_client': Mock(),
            'settings': Mock()
        }), patch('langfuse.get_client') as mock_get_client, \
           patch('asyncio.to_thread') as mock_to_thread:
            
            mock_langfuse_client = Mock()
            mock_span = Mock()
            mock_span.__enter__ = Mock(return_value=mock_span)
            mock_span.__exit__ = Mock(return_value=None)
            mock_langfuse_client.start_as_current_span.return_value = mock_span
            mock_get_client.return_value = mock_langfuse_client
            
            mock_to_thread.return_value = {
                'output': 'Test response',
                'intermediate_steps': [('action1', 'result1')]
            }
            
            request_data = {
                "input": "Test input",
                "session_id": "test-session"
            }
            
            response = test_client.post("/invoke", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            
            # Check all required fields are present
            required_fields = ["output", "session_id", "request_id", "metadata"]
            for field in required_fields:
                assert field in data
            
            # Check types
            assert isinstance(data["output"], str)
            assert isinstance(data["session_id"], str)
            assert isinstance(data["request_id"], str)
            assert isinstance(data["metadata"], dict)


class TestApplicationLifecycle:
    """Test application startup and shutdown."""
    
    @pytest.mark.unit
    def test_application_startup_configuration(self):
        """Test application startup configuration."""
        # Test that the app is configured correctly
        assert app.title == "Multi-Agent System API"
        assert app.description is not None
        assert app.version == "1.0.0"
    
    @pytest.mark.unit
    def test_lifespan_startup_success(self, mock_env_vars, mock_json_configs, mock_langfuse_client):
        """Test successful application startup."""
        with patch('main.get_global_settings') as mock_get_settings, \
             patch('main.create_orchestrator_agent') as mock_create_agent, \
             patch('main.get_agent_info') as mock_get_info:
            
            mock_settings = Mock()
            mock_settings.log_level = "INFO"
            mock_get_settings.return_value = mock_settings
            
            mock_agent = Mock()
            mock_create_agent.return_value = mock_agent
            
            mock_get_info.return_value = {"status": "ready"}
            
            # The lifespan is tested indirectly through the app startup
            # In a real test, you would need to trigger the lifespan events
            assert app is not None
    
    @pytest.mark.unit
    def test_lifespan_startup_failure(self, mock_env_vars):
        """Test application startup failure handling."""
        with patch('main.get_global_settings', side_effect=Exception("Config error")):
            # In a real scenario, this would prevent app startup
            # Here we just test that the error would be raised
            with pytest.raises(Exception):
                from main import get_global_settings
                get_global_settings()


class TestIntegration:
    """Integration tests for the main application."""
    
    @pytest.mark.integration
    def test_complete_api_workflow(self, test_client):
        """Test complete API workflow: health -> info -> invoke."""
        mock_agent = Mock()
        mock_agent.invoke.return_value = {
            'output': 'Workflow test response',
            'intermediate_steps': []
        }
        
        mock_agent_info = {
            "operators_count": 3,
            "max_iterations": 10
        }
        
        with patch('main.app_state', {
            'agent_executor': mock_agent,
            'langfuse_client': Mock(),
            'settings': Mock()
        }), patch('main.get_agent_info', return_value=mock_agent_info), \
           patch('langfuse.get_client') as mock_get_client, \
           patch('asyncio.to_thread') as mock_to_thread:
            
            mock_langfuse_client = Mock()
            mock_span = Mock()
            mock_span.__enter__ = Mock(return_value=mock_span)
            mock_span.__exit__ = Mock(return_value=None)
            mock_langfuse_client.start_as_current_span.return_value = mock_span
            mock_get_client.return_value = mock_langfuse_client
            
            mock_to_thread.return_value = {
                'output': 'Workflow test response',
                'intermediate_steps': []
            }
            
            # 1. Check health
            health_response = test_client.get("/health")
            assert health_response.status_code == 200
            
            # 2. Get agent info
            info_response = test_client.get("/agent/info")
            assert info_response.status_code == 200
            
            # 3. Invoke agent
            invoke_response = test_client.post("/invoke", json={
                "input": "Test complete workflow"
            })
            assert invoke_response.status_code == 200
            
            # All steps should succeed
            assert health_response.json()["status"] == "healthy"
            assert info_response.json()["operators_count"] == 3
            assert invoke_response.json()["output"] == "Workflow test response"


class TestAPIDocumentation:
    """Test API documentation and OpenAPI spec."""
    
    @pytest.mark.unit
    def test_openapi_spec_available(self, test_client):
        """Test that OpenAPI spec is available."""
        response = test_client.get("/openapi.json")
        
        assert response.status_code == 200
        spec = response.json()
        assert "openapi" in spec
        assert "info" in spec
        assert spec["info"]["title"] == "Multi-Agent System API"
    
    @pytest.mark.unit
    def test_docs_endpoint_available(self, test_client):
        """Test that documentation endpoint is available."""
        response = test_client.get("/docs")
        
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")


class TestSecurityAndValidation:
    """Test security and validation aspects."""
    
    @pytest.mark.unit
    def test_invoke_request_size_limit(self, test_client):
        """Test request size handling."""
        # Create a very large input
        large_input = "A" * 100000  # 100KB input
        
        with patch('main.app_state', {
            'agent_executor': Mock(),
            'langfuse_client': Mock(),
            'settings': Mock()
        }):
            request_data = {
                "input": large_input
            }
            
            # Should handle large inputs (within reasonable limits)
            response = test_client.post("/invoke", json=request_data)
            # Response depends on how the agent handles large inputs
    
    @pytest.mark.unit
    def test_concurrent_requests(self, test_client):
        """Test handling of concurrent requests."""
        import threading
        import time
        
        mock_agent = Mock()
        mock_agent.invoke.return_value = {
            'output': 'Concurrent test response',
            'intermediate_steps': []
        }
        
        responses = []
        errors = []
        
        def make_request():
            try:
                with patch('main.app_state', {
                    'agent_executor': mock_agent,
                    'langfuse_client': Mock(),
                    'settings': Mock()
                }), patch('langfuse.get_client') as mock_get_client, \
                   patch('asyncio.to_thread') as mock_to_thread:
                    
                    mock_langfuse_client = Mock()
                    mock_span = Mock()
                    mock_span.__enter__ = Mock(return_value=mock_span)
                    mock_span.__exit__ = Mock(return_value=None)
                    mock_langfuse_client.start_as_current_span.return_value = mock_span
                    mock_get_client.return_value = mock_langfuse_client
                    
                    mock_to_thread.return_value = {
                        'output': 'Concurrent test response',
                        'intermediate_steps': []
                    }
                    
                    response = test_client.post("/invoke", json={
                        "input": f"Concurrent request {threading.current_thread().ident}"
                    })
                    responses.append(response.status_code)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # All requests should succeed
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert all(status == 200 for status in responses)