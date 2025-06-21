"""
Shared test fixtures and configuration for the multi-agent system test suite.
"""

import os
import pytest
import json
import tempfile
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any, Optional, Generator
import sys

# Add src directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from pydantic import BaseModel
from fastapi.testclient import TestClient
from langchain.agents import AgentExecutor
from langchain_mistralai import ChatMistralAI
from langfuse import Langfuse


@pytest.fixture
def mock_env_vars():
    """Mock environment variables for testing."""
    with patch.dict(os.environ, {
        'LANGFUSE_PUBLIC_KEY': 'pk-lf-test-key',
        'LANGFUSE_SECRET_KEY': 'sk-lf-test-secret', 
        'LANGFUSE_HOST': 'https://test.langfuse.com',
        'MISTRAL_API_KEY': 'test-mistral-key',
        'MISTRAL_MODEL': 'mistral-test',
        'LOG_LEVEL': 'INFO'
    }):
        yield


@pytest.fixture
def mock_settings():
    """Mock settings object for testing."""
    from config import Settings
    
    class MockSettings(Settings):
        langfuse_public_key: str = "pk-lf-test-key"
        langfuse_secret_key: str = "sk-lf-test-secret"
        langfuse_host: str = "https://test.langfuse.com"
        mistral_api_key: str = "test-mistral-key"
        mistral_model: str = "mistral-test"
        log_level: str = "INFO"
        
        class Config:
            env_file = None
    
    return MockSettings()


@pytest.fixture
def mock_json_configs():
    """Mock JSON configuration files."""
    configs = {
        'model_config': {
            'temperature': 0.7,
            'max_tokens': 1000,
            'timeout': 30
        },
        'langfuse_config': {
            'flush_at': 10,
            'flush_interval': 1.0,
            'public_key_env': 'LANGFUSE_PUBLIC_KEY',
            'secret_key_env': 'LANGFUSE_SECRET_KEY'
        }
    }
    
    def mock_load_json_setting(filename: str):
        base_name = filename.replace('.json', '')
        return configs.get(base_name, {})
    
    with patch('config.load_json_setting', side_effect=mock_load_json_setting), \
         patch('agent_factory.load_json_setting', side_effect=mock_load_json_setting):
        yield configs


@pytest.fixture
def mock_prompt_files():
    """Mock prompt files for testing."""
    prompts = {
        'main_orchestrator_system': """You are a helpful AI assistant that coordinates with specialist agents.

You have access to specialist agents for different tasks:
- Weather operations
- Mathematical calculations
- Date/time operations

Always delegate tasks to the appropriate specialist agent.""",
        
        'weather_operator_system': """You are a weather specialist agent.

You have access to weather tools:
- get_current_weather
- get_weather_forecast
- weather_help

Use these tools to provide accurate weather information.""",
        
        'math_operator_system': """You are a mathematical specialist agent.

You have access to mathematical tools:
- calculate
- math_help

Use these tools to perform accurate calculations.""",
        
        'datetime_operator_system': """You are a datetime specialist agent.

You have access to datetime tools:
- get_unix_time
- get_week_number
- check_leap_year
- validate_date

Use these tools to handle date and time operations."""
    }
    
    def mock_get_prompt(name: str) -> str:
        return prompts.get(name.replace('.md', ''), f"Mock prompt for {name}")
    
    with patch('prompt_manager.PromptManager.get_prompt', side_effect=mock_get_prompt):
        yield prompts


@pytest.fixture
def mock_langfuse_client():
    """Mock Langfuse client for testing."""
    mock_client = Mock()
    mock_client.flush.return_value = None
    
    # Configure trace method and context manager
    mock_trace = Mock()
    mock_trace.__enter__ = Mock(return_value=mock_trace)
    mock_trace.__exit__ = Mock(return_value=None)
    mock_trace.id = "test-trace-id"
    mock_client.trace.return_value = mock_trace
    
    # Configure start_as_current_span method
    mock_span = Mock()
    mock_span.__enter__ = Mock(return_value=mock_span)
    mock_span.__exit__ = Mock(return_value=None)
    mock_span.id = "test-span-id"
    mock_client.start_as_current_span.return_value = mock_span
    
    with patch('langfuse.Langfuse', return_value=mock_client), \
         patch('langfuse.get_client', return_value=mock_client):
        yield mock_client


@pytest.fixture
def mock_llm():
    """Mock ChatMistralAI LLM for testing."""
    mock_llm = Mock(spec=ChatMistralAI)
    mock_llm.invoke.return_value = Mock()
    mock_llm.astream.return_value = Mock()
    
    with patch('langchain_mistralai.ChatMistralAI', return_value=mock_llm):
        yield mock_llm


@pytest.fixture
def mock_weather_api():
    """Mock weather API responses."""
    def mock_get(url, params=None, timeout=None):
        response = Mock()
        response.raise_for_status.return_value = None
        
        if 'geocoding' in url:
            response.json.return_value = {
                'results': [{
                    'latitude': 52.52,
                    'longitude': 13.41,
                    'name': 'Berlin',
                    'country': 'Germany',
                    'admin1': 'Berlin'
                }]
            }
        else:  # forecast API
            response.json.return_value = {
                'current': {
                    'time': '2024-01-01T12:00:00Z',
                    'temperature_2m': 15.5,
                    'relative_humidity_2m': 65,
                    'wind_speed_10m': 10.2,
                    'wind_direction_10m': 180,
                    'precipitation': 0.0,
                    'weather_code': 1
                },
                'current_units': {
                    'temperature_2m': '°C',
                    'wind_speed_10m': 'km/h'
                },
                'daily': {
                    'time': ['2024-01-01', '2024-01-02', '2024-01-03'],
                    'temperature_2m_max': [18.0, 20.0, 17.0],
                    'temperature_2m_min': [10.0, 12.0, 11.0],
                    'weather_code': [1, 2, 3]
                }
            }
        
        return response
    
    with patch('requests.get', side_effect=mock_get):
        yield


@pytest.fixture
def mock_agent_executor():
    """Mock AgentExecutor for testing."""
    mock_executor = Mock(spec=AgentExecutor)
    mock_executor.tools = []
    mock_executor.max_iterations = 10
    mock_executor.max_execution_time = 300
    mock_executor.verbose = False
    mock_executor.invoke.return_value = {
        'output': 'Test response',
        'intermediate_steps': []
    }
    
    return mock_executor


@pytest.fixture
def sample_weather_data():
    """Sample weather data for testing."""
    return {
        'current': {
            'time': '2024-01-01T12:00:00Z',
            'temperature_2m': 15.5,
            'relative_humidity_2m': 65,
            'wind_speed_10m': 10.2,
            'wind_direction_10m': 180,
            'precipitation': 0.0,
            'weather_code': 1
        },
        'current_units': {
            'temperature_2m': '°C',
            'wind_speed_10m': 'km/h'
        }
    }


@pytest.fixture
def sample_location_info():
    """Sample location information for testing."""
    return {
        'latitude': 52.52,
        'longitude': 13.41,
        'name': 'Berlin',
        'country': 'Germany',
        'admin1': 'Berlin'
    }


@pytest.fixture
def temp_prompts_dir():
    """Create temporary prompts directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        prompts_dir = os.path.join(temp_dir, 'prompts')
        os.makedirs(prompts_dir)
        
        # Create sample prompt files
        prompts = {
            'main_orchestrator_system.md': 'You are a helpful AI assistant.',
            'weather_operator_system.md': 'You are a weather specialist.',
            'math_operator_system.md': 'You are a math specialist.',
            'datetime_operator_system.md': 'You are a datetime specialist.'
        }
        
        for filename, content in prompts.items():
            with open(os.path.join(prompts_dir, filename), 'w') as f:
                f.write(content)
        
        yield prompts_dir


@pytest.fixture
def temp_settings_dir():
    """Create temporary settings directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        settings_dir = os.path.join(temp_dir, 'settings')
        os.makedirs(settings_dir)
        
        # Create sample settings files
        settings = {
            'model_config.json': {
                'temperature': 0.7,
                'max_tokens': 1000,
                'timeout': 30
            },
            'langfuse_config.json': {
                'flush_at': 10,
                'flush_interval': 1.0,
                'public_key_env': 'LANGFUSE_PUBLIC_KEY',
                'secret_key_env': 'LANGFUSE_SECRET_KEY'
            }
        }
        
        for filename, content in settings.items():
            with open(os.path.join(settings_dir, filename), 'w') as f:
                json.dump(content, f)
        
        yield settings_dir


@pytest.fixture
def mock_fastapi_app():
    """Mock FastAPI app for testing."""
    from main import app
    
    with patch('main.app_state', {
        'agent_executor': Mock(),
        'langfuse_client': Mock(),
        'settings': Mock()
    }):
        yield app


@pytest.fixture
def test_client(mock_fastapi_app):
    """Test client for FastAPI application."""
    return TestClient(mock_fastapi_app)


# Utility functions for tests
def create_mock_tool(name: str, description: str, func_return: Any = "Mock result"):
    """Create a mock tool for testing."""
    mock_tool = Mock()
    mock_tool.name = name
    mock_tool.description = description
    mock_tool.func.return_value = func_return
    return mock_tool


def create_mock_agent_action(tool: str, tool_input: Any):
    """Create a mock agent action for testing."""
    mock_action = Mock()
    mock_action.tool = tool
    mock_action.tool_input = tool_input
    return mock_action


# Parametrized test data
@pytest.fixture(params=[
    "Berlin",
    "London, UK", 
    "New York",
    "52.52,13.41"
])
def sample_locations(request):
    """Parametrized fixture for testing various location formats."""
    return request.param


@pytest.fixture(params=[
    {"temperature": 15.5, "humidity": 65, "wind_speed": 10.2},
    {"temperature": -5.0, "humidity": 90, "wind_speed": 25.0},
    {"temperature": 35.0, "humidity": 30, "wind_speed": 5.0},
])
def sample_weather_conditions(request):
    """Parametrized fixture for testing various weather conditions."""
    return request.param


@pytest.fixture(params=[
    "2 + 2",
    "10 * 3 + 5",
    "sqrt(16) + 2**3",
    "sin(0) + cos(0)"
])
def sample_math_expressions(request):
    """Parametrized fixture for testing various math expressions."""
    return request.param


@pytest.fixture(params=[
    "2024-01-01",
    "2024-12-31", 
    "2000-02-29",  # leap year
    "2023-02-28"   # non-leap year
])
def sample_dates(request):
    """Parametrized fixture for testing various date formats."""
    return request.param


# Async test utilities
@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()