"""
Unit tests for the agent_factory module.

Tests agent creation, LLM configuration, operator management, and callbacks.
"""

import pytest
from unittest.mock import patch, Mock, MagicMock
from langchain.agents import AgentExecutor

from agent_factory import (
    ProperLoggingCallback,
    get_operator_agents,
    create_llm_from_config,
    create_prompt_template,
    create_orchestrator_agent,
    get_agent_info
)


class TestProperLoggingCallback:
    """Test the ProperLoggingCallback class."""
    
    @pytest.mark.unit
    def test_callback_initialization(self):
        """Test callback initialization."""
        with patch('logging.getLogger'):
            callback = ProperLoggingCallback()
            
            assert callback is not None
            assert callback.step_counter == 0
    
    @pytest.mark.unit
    def test_on_chain_start(self):
        """Test on_chain_start callback method."""
        with patch('logging.getLogger') as mock_logger:
            callback = ProperLoggingCallback()
            mock_logger_instance = mock_logger.return_value
            
            inputs = {"input": "Test input"}
            callback.on_chain_start({}, inputs)
            
            # Should log chain start message
            mock_logger_instance.info.assert_called()
    
    @pytest.mark.unit
    def test_on_agent_action(self):
        """Test on_agent_action callback method."""
        with patch('logging.getLogger') as mock_logger:
            callback = ProperLoggingCallback()
            mock_logger_instance = mock_logger.return_value
            
            mock_action = Mock()
            mock_action.tool = "weather_operator"
            mock_action.tool_input = "Get weather for Berlin"
            
            callback.on_agent_action(mock_action)
            
            # Should increment step counter and log action
            assert callback.step_counter == 1
            mock_logger_instance.info.assert_called()
    
    @pytest.mark.unit
    def test_on_tool_start(self):
        """Test on_tool_start callback method."""
        with patch('logging.getLogger') as mock_logger:
            callback = ProperLoggingCallback()
            
            serialized = {"name": "weather_operator"}
            input_str = "Test tool input"
            
            callback.on_tool_start(serialized, input_str)
            
            # Should log tool start
            mock_logger.assert_called()
    
    @pytest.mark.unit
    def test_on_tool_end(self):
        """Test on_tool_end callback method."""
        with patch('logging.getLogger') as mock_logger:
            callback = ProperLoggingCallback()
            mock_logger_instance = mock_logger.return_value
            
            output = "Tool execution result"
            callback.on_tool_end(output)
            
            # Should log tool output
            mock_logger_instance.info.assert_called()
    
    @pytest.mark.unit
    def test_on_tool_error(self):
        """Test on_tool_error callback method."""
        with patch('logging.getLogger') as mock_logger:
            callback = ProperLoggingCallback()
            mock_logger_instance = mock_logger.return_value
            
            error = Exception("Tool error")
            callback.on_tool_error(error)
            
            # Should log error
            mock_logger_instance.error.assert_called()
    
    @pytest.mark.unit
    def test_on_agent_finish(self):
        """Test on_agent_finish callback method."""
        with patch('logging.getLogger') as mock_logger:
            callback = ProperLoggingCallback()
            mock_logger_instance = mock_logger.return_value
            
            mock_finish = Mock()
            mock_finish.return_values = {"output": "Final answer"}
            
            callback.on_agent_finish(mock_finish)
            
            # Should log final answer
            mock_logger_instance.info.assert_called()
    
    @pytest.mark.unit
    def test_on_chain_end(self):
        """Test on_chain_end callback method."""
        with patch('logging.getLogger') as mock_logger:
            callback = ProperLoggingCallback()
            callback.step_counter = 5  # Set some steps
            
            outputs = {"output": "Chain result"}
            callback.on_chain_end(outputs)
            
            # Should reset step counter
            assert callback.step_counter == 0
    
    @pytest.mark.unit
    def test_on_text_thought_processing(self):
        """Test on_text method with thought processing."""
        with patch('logging.getLogger') as mock_logger:
            callback = ProperLoggingCallback()
            mock_logger_instance = mock_logger.return_value
            
            thought_text = "Thought: I need to get weather information"
            callback.on_text(thought_text)
            
            # Should log the thought
            mock_logger_instance.info.assert_called()
    
    @pytest.mark.unit
    def test_on_llm_start(self):
        """Test on_llm_start callback method."""
        with patch('logging.getLogger') as mock_logger:
            callback = ProperLoggingCallback()
            
            prompts = ["Test prompt for LLM"]
            callback.on_llm_start({}, prompts)
            
            # Should log debug message
            mock_logger.assert_called()
    
    @pytest.mark.unit
    def test_on_llm_end(self):
        """Test on_llm_end callback method."""
        with patch('logging.getLogger') as mock_logger:
            callback = ProperLoggingCallback()
            
            mock_response = Mock()
            mock_generation = Mock()
            mock_generation.text = "LLM response text"
            mock_response.generations = [mock_generation]
            
            callback.on_llm_end(mock_response)
            
            # Should log LLM response
            mock_logger.assert_called()


class TestGetOperatorAgents:
    """Test the get_operator_agents function."""
    
    @pytest.mark.unit
    def test_get_operator_agents_success(self):
        """Test successful operator agents retrieval."""
        with patch('agent_factory.weather_operator') as mock_weather, \
             patch('agent_factory.math_operator') as mock_math, \
             patch('agent_factory.datetime_operator') as mock_datetime:
            
            # Mock operator properties
            mock_weather.name = "weather_operator"
            mock_weather.description = "Weather specialist agent"
            mock_math.name = "math_operator"
            mock_math.description = "Math specialist agent"
            mock_datetime.name = "datetime_operator"
            mock_datetime.description = "Datetime specialist agent"
            
            operators = get_operator_agents()
            
            assert len(operators) == 3
            assert mock_weather in operators
            assert mock_math in operators
            assert mock_datetime in operators
    
    @pytest.mark.unit
    def test_get_operator_agents_with_error(self):
        """Test operator agents retrieval with runtime error."""
        # Test the actual error handling in the function by causing an exception
        # in the list creation or logging
        with patch('agent_factory.logger') as mock_logger:
            # Mock logger.info to raise an exception to trigger the except block
            mock_logger.info.side_effect = Exception("Logging error")
            
            operators = get_operator_agents()
            
            # Should return empty list on error and log the error
            assert operators == []
            mock_logger.error.assert_called()


class TestCreateLlmFromConfig:
    """Test the create_llm_from_config function."""
    
    @pytest.mark.unit
    def test_create_llm_success(self, mock_env_vars, mock_json_configs, mock_settings):
        """Test successful LLM creation."""
        with patch('config.get_global_settings', return_value=mock_settings), \
             patch('agent_factory.ChatMistralAI') as mock_mistral:
            
            mock_llm = Mock()
            mock_mistral.return_value = mock_llm
            
            result = create_llm_from_config()
            
            assert result == mock_llm
            mock_mistral.assert_called_once()
            
            # Check that correct parameters were passed
            call_args = mock_mistral.call_args
            assert call_args[1]['model'] == mock_settings.mistral_model
            assert call_args[1]['temperature'] == 0.7
            assert call_args[1]['max_tokens'] == 1000
            assert call_args[1]['timeout'] == 30
    
    @pytest.mark.unit
    def test_create_llm_missing_config(self, mock_env_vars, mock_settings):
        """Test LLM creation with missing model config."""
        with patch('config.get_global_settings', return_value=mock_settings), \
             patch('agent_factory.load_json_setting', side_effect=FileNotFoundError("Config not found")):
            
            with pytest.raises(RuntimeError) as exc_info:
                create_llm_from_config()
            
            assert "Failed to create LLM" in str(exc_info.value)
    
    @pytest.mark.unit
    def test_create_llm_invalid_config(self, mock_env_vars, mock_settings):
        """Test LLM creation with invalid model config."""
        invalid_config = {"temperature": 0.7}  # Missing required keys
        
        with patch('config.get_global_settings', return_value=mock_settings), \
             patch('agent_factory.load_json_setting', return_value=invalid_config):
            
            with pytest.raises(ValueError) as exc_info:
                create_llm_from_config()
            
            assert "Missing required model configuration keys" in str(exc_info.value)
    
    @pytest.mark.unit
    def test_create_llm_mistral_error(self, mock_env_vars, mock_json_configs, mock_settings):
        """Test LLM creation with ChatMistralAI error."""
        with patch('config.get_global_settings', return_value=mock_settings), \
             patch('agent_factory.ChatMistralAI', side_effect=Exception("Mistral error")):
            
            with pytest.raises(RuntimeError) as exc_info:
                create_llm_from_config()
            
            assert "Failed to create LLM" in str(exc_info.value)


class TestCreatePromptTemplate:
    """Test the create_prompt_template function."""
    
    @pytest.mark.unit
    def test_create_prompt_template_success(self, mock_prompt_files):
        """Test successful prompt template creation."""
        with patch('agent_factory.get_prompt_manager') as mock_get_pm, \
             patch('agent_factory.PromptTemplate') as mock_template:
            
            mock_pm = Mock()
            mock_pm.get_prompt.return_value = "System prompt content"
            mock_get_pm.return_value = mock_pm
            
            mock_prompt_template = Mock()
            mock_template.from_template.return_value = mock_prompt_template
            
            result = create_prompt_template()
            
            assert result == mock_prompt_template
            mock_pm.get_prompt.assert_called_with("main_orchestrator_system")
            mock_template.from_template.assert_called_once()
    
    @pytest.mark.unit
    def test_create_prompt_template_custom_name(self, mock_prompt_files):
        """Test prompt template creation with custom prompt name."""
        with patch('agent_factory.get_prompt_manager') as mock_get_pm, \
             patch('agent_factory.PromptTemplate') as mock_template:
            
            mock_pm = Mock()
            mock_pm.get_prompt.return_value = "Custom prompt content"
            mock_get_pm.return_value = mock_pm
            
            mock_prompt_template = Mock()
            mock_template.from_template.return_value = mock_prompt_template
            
            result = create_prompt_template("custom_system")
            
            assert result == mock_prompt_template
            mock_pm.get_prompt.assert_called_with("custom_system")
    
    @pytest.mark.unit
    def test_create_prompt_template_error(self):
        """Test prompt template creation with error."""
        with patch('agent_factory.get_prompt_manager', side_effect=Exception("Prompt error")):
            
            with pytest.raises(RuntimeError) as exc_info:
                create_prompt_template()
            
            assert "Failed to create prompt template" in str(exc_info.value)
    
    @pytest.mark.unit
    def test_prompt_template_content(self, mock_prompt_files):
        """Test that prompt template contains required content."""
        with patch('agent_factory.get_prompt_manager') as mock_get_pm, \
             patch('agent_factory.PromptTemplate') as mock_template:
            
            mock_pm = Mock()
            mock_pm.get_prompt.return_value = "System prompt content"
            mock_get_pm.return_value = mock_pm
            
            create_prompt_template()
            
            # Check that template was created with proper ReAct format
            call_args = mock_template.from_template.call_args[0][0]
            assert "Question:" in call_args
            assert "Thought:" in call_args
            assert "Action:" in call_args
            assert "Action Input:" in call_args
            assert "Observation:" in call_args
            assert "Final Answer:" in call_args


class TestCreateOrchestratorAgent:
    """Test the create_orchestrator_agent function."""
    
    @pytest.mark.unit
    def test_create_orchestrator_agent_success(self, mock_env_vars, mock_json_configs, mock_langfuse_client):
        """Test successful orchestrator agent creation."""
        with patch('agent_factory.get_operator_agents') as mock_get_ops, \
             patch('agent_factory.create_llm_from_config') as mock_create_llm, \
             patch('agent_factory.create_prompt_template') as mock_create_prompt, \
             patch('agent_factory.create_react_agent') as mock_create_agent, \
             patch('agent_factory.AgentExecutor') as mock_executor:
            
            # Mock operators
            mock_operators = [Mock(), Mock(), Mock()]
            mock_get_ops.return_value = mock_operators
            
            # Mock LLM
            mock_llm = Mock()
            mock_create_llm.return_value = mock_llm
            
            # Mock prompt template
            mock_prompt = Mock()
            mock_create_prompt.return_value = mock_prompt
            
            # Mock agent
            mock_agent = Mock()
            mock_create_agent.return_value = mock_agent
            
            # Mock executor
            mock_agent_executor = Mock()
            mock_executor.return_value = mock_agent_executor
            
            result = create_orchestrator_agent(mock_langfuse_client)
            
            assert result == mock_agent_executor
            
            # Verify all components were created correctly
            mock_get_ops.assert_called_once()
            mock_create_llm.assert_called_once()
            mock_create_prompt.assert_called_once()
            mock_create_agent.assert_called_once_with(
                llm=mock_llm,
                tools=mock_operators,
                prompt=mock_prompt
            )
            mock_executor.assert_called_once()
    
    @pytest.mark.unit
    def test_create_orchestrator_agent_no_operators(self, mock_env_vars, mock_json_configs, mock_langfuse_client):
        """Test orchestrator agent creation with no operators."""
        with patch('agent_factory.get_operator_agents', return_value=[]), \
             patch('agent_factory.create_llm_from_config') as mock_create_llm, \
             patch('agent_factory.create_prompt_template') as mock_create_prompt, \
             patch('agent_factory.create_react_agent') as mock_create_agent, \
             patch('agent_factory.AgentExecutor') as mock_executor:
            
            mock_llm = Mock()
            mock_create_llm.return_value = mock_llm
            
            mock_prompt = Mock()
            mock_create_prompt.return_value = mock_prompt
            
            mock_agent = Mock()
            mock_create_agent.return_value = mock_agent
            
            mock_agent_executor = Mock()
            mock_executor.return_value = mock_agent_executor
            
            result = create_orchestrator_agent(mock_langfuse_client)
            
            # Should still create agent even with no operators
            assert result == mock_agent_executor
    
    @pytest.mark.unit
    def test_create_orchestrator_agent_without_langfuse(self, mock_env_vars, mock_json_configs):
        """Test orchestrator agent creation without Langfuse client."""
        with patch('agent_factory.get_operator_agents') as mock_get_ops, \
             patch('agent_factory.create_llm_from_config') as mock_create_llm, \
             patch('agent_factory.create_prompt_template') as mock_create_prompt, \
             patch('agent_factory.create_react_agent') as mock_create_agent, \
             patch('agent_factory.AgentExecutor') as mock_executor, \
             patch('agent_factory.Langfuse') as mock_langfuse_class:
            
            mock_operators = [Mock()]
            mock_get_ops.return_value = mock_operators
            
            mock_llm = Mock()
            mock_create_llm.return_value = mock_llm
            
            mock_prompt = Mock()
            mock_create_prompt.return_value = mock_prompt
            
            mock_agent = Mock()
            mock_create_agent.return_value = mock_agent
            
            mock_agent_executor = Mock()
            mock_executor.return_value = mock_agent_executor
            
            # Mock Langfuse creation
            mock_langfuse_client = Mock()
            mock_langfuse_class.return_value = mock_langfuse_client
            
            result = create_orchestrator_agent(langfuse_client=None)
            
            assert result == mock_agent_executor
    
    @pytest.mark.unit
    def test_create_orchestrator_agent_error(self, mock_env_vars, mock_json_configs):
        """Test orchestrator agent creation with error."""
        with patch('agent_factory.get_operator_agents', side_effect=Exception("Operator error")):
            
            with pytest.raises(RuntimeError) as exc_info:
                create_orchestrator_agent()
            
            assert "Failed to create orchestrator agent" in str(exc_info.value)
    
    @pytest.mark.unit
    def test_agent_executor_configuration(self, mock_env_vars, mock_json_configs, mock_langfuse_client):
        """Test that AgentExecutor is configured correctly."""
        with patch('agent_factory.get_operator_agents') as mock_get_ops, \
             patch('agent_factory.create_llm_from_config') as mock_create_llm, \
             patch('agent_factory.create_prompt_template') as mock_create_prompt, \
             patch('agent_factory.create_react_agent') as mock_create_agent, \
             patch('agent_factory.AgentExecutor') as mock_executor:
            
            mock_operators = [Mock(), Mock()]
            mock_get_ops.return_value = mock_operators
            
            mock_llm = Mock()
            mock_create_llm.return_value = mock_llm
            
            mock_prompt = Mock()
            mock_create_prompt.return_value = mock_prompt
            
            mock_agent = Mock()
            mock_create_agent.return_value = mock_agent
            
            mock_agent_executor = Mock()
            mock_executor.return_value = mock_agent_executor
            
            create_orchestrator_agent(mock_langfuse_client)
            
            # Check AgentExecutor configuration
            call_kwargs = mock_executor.call_args[1]
            assert call_kwargs['agent'] == mock_agent
            assert call_kwargs['tools'] == mock_operators
            assert call_kwargs['verbose'] == False
            assert call_kwargs['max_iterations'] == 10
            assert call_kwargs['max_execution_time'] == 300
            assert call_kwargs['return_intermediate_steps'] == True
            assert call_kwargs['handle_parsing_errors'] == True
            assert len(call_kwargs['callbacks']) == 1


class TestGetAgentInfo:
    """Test the get_agent_info function."""
    
    @pytest.mark.unit
    def test_get_agent_info_success(self):
        """Test successful agent info retrieval."""
        mock_tool1 = Mock()
        mock_tool1.name = "weather_operator"
        mock_tool1.description = "Weather specialist agent for weather operations"
        
        mock_tool2 = Mock()
        mock_tool2.name = "math_operator"
        mock_tool2.description = "Math specialist agent for calculations"
        
        mock_executor = Mock(spec=AgentExecutor)
        mock_executor.tools = [mock_tool1, mock_tool2]
        mock_executor.max_iterations = 10
        mock_executor.max_execution_time = 300
        mock_executor.verbose = False
        mock_executor.callbacks = [Mock()]
        
        result = get_agent_info(mock_executor)
        
        assert result["operators_count"] == 2
        assert len(result["operators"]) == 2
        assert result["operators"][0]["name"] == "weather_operator"
        assert "Weather specialist" in result["operators"][0]["description"]
        assert result["max_iterations"] == 10
        assert result["max_execution_time"] == 300
        assert result["verbose"] == False
        assert result["has_callbacks"] == True
        assert result["callbacks_count"] == 1
    
    @pytest.mark.unit
    def test_get_agent_info_no_tools(self):
        """Test agent info with no tools."""
        mock_executor = Mock(spec=AgentExecutor)
        mock_executor.tools = None
        mock_executor.max_iterations = 5
        mock_executor.max_execution_time = 120
        mock_executor.verbose = True
        mock_executor.callbacks = None
        
        result = get_agent_info(mock_executor)
        
        assert result["operators_count"] == 0
        assert result["operators"] == []
        assert result["max_iterations"] == 5
        assert result["max_execution_time"] == 120
        assert result["verbose"] == True
        assert result["has_callbacks"] == False
        assert result["callbacks_count"] == 0
    
    @pytest.mark.unit
    def test_get_agent_info_long_descriptions(self):
        """Test agent info with long tool descriptions."""
        mock_tool = Mock()
        mock_tool.name = "test_operator"
        mock_tool.description = "A" * 200  # Very long description
        
        mock_executor = Mock(spec=AgentExecutor)
        mock_executor.tools = [mock_tool]
        mock_executor.max_iterations = 10
        mock_executor.max_execution_time = 300
        mock_executor.verbose = False
        mock_executor.callbacks = []
        
        result = get_agent_info(mock_executor)
        
        # Description should be truncated
        operator_desc = result["operators"][0]["description"]
        assert len(operator_desc) <= 103  # 100 chars + "..."
        assert operator_desc.endswith("...")
    
    @pytest.mark.unit
    def test_get_agent_info_error(self):
        """Test agent info with error."""
        mock_executor = Mock()
        # Configure tools property to raise an exception when accessed
        type(mock_executor).tools = Mock(side_effect=Exception("Tools error"))
        
        result = get_agent_info(mock_executor)
        
        assert "error" in result
        assert "Tools error" in result["error"]
    
    @pytest.mark.unit
    def test_get_agent_info_missing_attributes(self):
        """Test agent info with missing attributes."""
        mock_executor = Mock()
        # Don't set some attributes
        del mock_executor.max_iterations
        del mock_executor.max_execution_time
        mock_executor.tools = []
        mock_executor.verbose = False
        mock_executor.callbacks = []
        
        result = get_agent_info(mock_executor)
        
        assert result["operators_count"] == 0
        assert result["max_iterations"] == "unknown"
        assert result["max_execution_time"] == "unknown"


class TestAgentFactoryIntegration:
    """Integration tests for agent factory functionality."""
    
    @pytest.mark.integration
    def test_complete_agent_creation_workflow(self, mock_env_vars, mock_json_configs, mock_prompt_files, mock_langfuse_client):
        """Test complete agent creation workflow."""
        with patch('agent_factory.weather_operator') as mock_weather, \
             patch('agent_factory.math_operator') as mock_math, \
             patch('agent_factory.datetime_operator') as mock_datetime, \
             patch('agent_factory.ChatMistralAI') as mock_mistral, \
             patch('agent_factory.create_react_agent') as mock_create_agent, \
             patch('agent_factory.AgentExecutor') as mock_executor:
            
            # Mock operators
            mock_weather.name = "weather_operator"
            mock_weather.description = "Weather specialist"
            mock_math.name = "math_operator"
            mock_math.description = "Math specialist"
            mock_datetime.name = "datetime_operator"
            mock_datetime.description = "Datetime specialist"
            
            # Mock LLM
            mock_llm = Mock()
            mock_mistral.return_value = mock_llm
            
            # Mock agent
            mock_agent = Mock()
            mock_create_agent.return_value = mock_agent
            
            # Mock executor
            mock_agent_executor = Mock()
            mock_executor.return_value = mock_agent_executor
            
            # Create agent
            result = create_orchestrator_agent(mock_langfuse_client)
            
            # Verify workflow
            assert result == mock_agent_executor
            
            # Check that all components were integrated
            mock_mistral.assert_called_once()
            mock_create_agent.assert_called_once()
            mock_executor.assert_called_once()
    
    @pytest.mark.integration
    def test_error_handling_throughout_workflow(self, mock_env_vars):
        """Test error handling throughout the agent creation workflow."""
        # Test each potential failure point
        
        # 1. Operator loading failure
        with patch('agent_factory.get_operator_agents', side_effect=Exception("Operator error")):
            with pytest.raises(RuntimeError):
                create_orchestrator_agent()
        
        # 2. LLM creation failure
        with patch('agent_factory.get_operator_agents', return_value=[]), \
             patch('agent_factory.create_llm_from_config', side_effect=Exception("LLM error")):
            with pytest.raises(RuntimeError):
                create_orchestrator_agent()
        
        # 3. Prompt template failure
        with patch('agent_factory.get_operator_agents', return_value=[]), \
             patch('agent_factory.create_llm_from_config', return_value=Mock()), \
             patch('agent_factory.create_prompt_template', side_effect=Exception("Prompt error")):
            with pytest.raises(RuntimeError):
                create_orchestrator_agent()


class TestAgentFactoryEdgeCases:
    """Test edge cases and boundary conditions."""
    
    @pytest.mark.unit
    def test_callback_with_empty_text(self):
        """Test callback handling of empty text."""
        with patch('logging.getLogger'):
            callback = ProperLoggingCallback()
            
            # Should handle empty text gracefully
            callback.on_text("")
            callback.on_text(None)
            callback.on_text("   ")  # Whitespace only
    
    @pytest.mark.unit
    def test_callback_with_special_characters(self):
        """Test callback handling of text with special characters."""
        with patch('logging.getLogger') as mock_logger:
            callback = ProperLoggingCallback()
            mock_logger_instance = mock_logger.return_value
            
            special_text = "Thought: Processing 🌍 data with special chars: ñ, é, 中文"
            callback.on_text(special_text)
            
            # Should handle special characters without errors
            mock_logger_instance.info.assert_called()
    
    @pytest.mark.unit
    def test_agent_info_with_none_tools(self):
        """Test get_agent_info when tools is None."""
        mock_executor = Mock()
        mock_executor.tools = None
        mock_executor.max_iterations = 10
        mock_executor.max_execution_time = 300
        mock_executor.verbose = False
        mock_executor.callbacks = None
        
        result = get_agent_info(mock_executor)
        
        assert result["operators_count"] == 0
        assert result["operators"] == []
    
    @pytest.mark.unit
    def test_large_number_of_operators(self, mock_env_vars, mock_json_configs, mock_langfuse_client):
        """Test agent creation with large number of operators."""
        with patch('agent_factory.get_operator_agents') as mock_get_ops, \
             patch('agent_factory.create_llm_from_config') as mock_create_llm, \
             patch('agent_factory.create_prompt_template') as mock_create_prompt, \
             patch('agent_factory.create_react_agent') as mock_create_agent, \
             patch('agent_factory.AgentExecutor') as mock_executor:
            
            # Create many mock operators
            mock_operators = [Mock() for _ in range(100)]
            mock_get_ops.return_value = mock_operators
            
            mock_llm = Mock()
            mock_create_llm.return_value = mock_llm
            
            mock_prompt = Mock()
            mock_create_prompt.return_value = mock_prompt
            
            mock_agent = Mock()
            mock_create_agent.return_value = mock_agent
            
            mock_agent_executor = Mock()
            mock_executor.return_value = mock_agent_executor
            
            result = create_orchestrator_agent(mock_langfuse_client)
            
            # Should handle many operators
            assert result == mock_agent_executor
            assert mock_create_agent.call_args[1]['tools'] == mock_operators