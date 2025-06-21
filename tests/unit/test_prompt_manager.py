"""
Unit tests for the prompt_manager module.

Tests prompt loading, file management, and error handling.
"""

import pytest
import os
import tempfile
from unittest.mock import patch, mock_open

from prompt_manager import PromptManager, get_prompt_manager


class TestPromptManager:
    """Test the PromptManager class."""
    
    @pytest.mark.unit
    def test_init_with_default_directory(self):
        """Test PromptManager initialization with default directory."""
        pm = PromptManager()
        assert pm.prompts_dir == "prompts"
    
    @pytest.mark.unit
    def test_init_with_custom_directory(self):
        """Test PromptManager initialization with custom directory."""
        custom_dir = "custom_prompts"
        pm = PromptManager(custom_dir)
        assert pm.prompts_dir == custom_dir
    
    @pytest.mark.unit
    def test_init_with_nonexistent_directory(self):
        """Test PromptManager initialization with non-existent directory."""
        with patch('os.path.exists', return_value=False):
            with patch('logging.getLogger') as mock_logger:
                pm = PromptManager("nonexistent")
                assert pm.prompts_dir == "nonexistent"
                # Should log a warning
                mock_logger.return_value.warning.assert_called()
    
    @pytest.mark.unit
    def test_get_prompt_success(self, temp_prompts_dir):
        """Test successful prompt loading."""
        pm = PromptManager(temp_prompts_dir)
        
        content = pm.get_prompt("main_orchestrator_system")
        
        assert content == "You are a helpful AI assistant."
        assert isinstance(content, str)
    
    @pytest.mark.unit
    def test_get_prompt_with_md_extension(self, temp_prompts_dir):
        """Test prompt loading with .md extension."""
        pm = PromptManager(temp_prompts_dir)
        
        content = pm.get_prompt("main_orchestrator_system.md")
        
        assert content == "You are a helpful AI assistant."
    
    @pytest.mark.unit
    def test_get_prompt_without_md_extension(self, temp_prompts_dir):
        """Test prompt loading without .md extension."""
        pm = PromptManager(temp_prompts_dir)
        
        content = pm.get_prompt("weather_operator_system")
        
        assert content == "You are a weather specialist."
    
    @pytest.mark.unit
    def test_get_prompt_nonexistent_file(self, temp_prompts_dir):
        """Test getting a non-existent prompt file."""
        pm = PromptManager(temp_prompts_dir)
        
        with pytest.raises(FileNotFoundError) as exc_info:
            pm.get_prompt("nonexistent")
        
        assert "Prompt file not found" in str(exc_info.value)
    
    @pytest.mark.unit
    def test_get_prompt_file_read_error(self, temp_prompts_dir):
        """Test prompt loading with file read error."""
        pm = PromptManager(temp_prompts_dir)
        
        # Mock file read error
        with patch('builtins.open', side_effect=IOError("Permission denied")):
            with pytest.raises(IOError) as exc_info:
                pm.get_prompt("main_orchestrator_system")
            
            assert "Error reading prompt file" in str(exc_info.value)
    
    @pytest.mark.unit
    def test_get_prompt_empty_file(self):
        """Test loading an empty prompt file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create empty prompt file
            empty_file = os.path.join(temp_dir, "empty.md")
            with open(empty_file, 'w') as f:
                f.write("")
            
            pm = PromptManager(temp_dir)
            content = pm.get_prompt("empty")
            
            assert content == ""  # Should return empty string, not None
    
    @pytest.mark.unit
    def test_get_prompt_whitespace_only_file(self):
        """Test loading a prompt file with only whitespace."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create whitespace-only prompt file
            whitespace_file = os.path.join(temp_dir, "whitespace.md")
            with open(whitespace_file, 'w') as f:
                f.write("   \n\t\n   ")
            
            pm = PromptManager(temp_dir)
            content = pm.get_prompt("whitespace")
            
            assert content == ""  # Should be stripped to empty string
    
    @pytest.mark.unit
    def test_get_prompt_with_unicode_content(self):
        """Test loading prompt with unicode content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create prompt file with unicode
            unicode_file = os.path.join(temp_dir, "unicode.md")
            unicode_content = "You are a helpful AI assistant. 🤖\n\nSupport for 中文 and العربية"
            with open(unicode_file, 'w', encoding='utf-8') as f:
                f.write(unicode_content)
            
            pm = PromptManager(temp_dir)
            content = pm.get_prompt("unicode")
            
            assert "🤖" in content
            assert "中文" in content
            assert "العربية" in content
    
    @pytest.mark.unit
    def test_get_prompt_strips_whitespace(self):
        """Test that get_prompt strips leading/trailing whitespace."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create prompt file with extra whitespace
            prompt_file = os.path.join(temp_dir, "padded.md")
            with open(prompt_file, 'w') as f:
                f.write("\n\n  This is a prompt with padding.  \n\n")
            
            pm = PromptManager(temp_dir)
            content = pm.get_prompt("padded")
            
            assert content == "This is a prompt with padding."
            assert not content.startswith('\n')
            assert not content.endswith('\n')
    
    @pytest.mark.unit
    def test_list_available_prompts_success(self, temp_prompts_dir):
        """Test successful listing of available prompts."""
        pm = PromptManager(temp_prompts_dir)
        
        prompts = pm.list_available_prompts()
        
        expected_prompts = [
            "datetime_operator_system",
            "main_orchestrator_system", 
            "math_operator_system",
            "weather_operator_system"
        ]
        assert set(prompts) == set(expected_prompts)
        assert all(isinstance(p, str) for p in prompts)
    
    @pytest.mark.unit
    def test_list_available_prompts_empty_directory(self):
        """Test listing prompts in empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pm = PromptManager(temp_dir)
            
            prompts = pm.list_available_prompts()
            
            assert prompts == []
    
    @pytest.mark.unit
    def test_list_available_prompts_nonexistent_directory(self):
        """Test listing prompts in non-existent directory."""
        pm = PromptManager("nonexistent_dir")
        
        prompts = pm.list_available_prompts()
        
        assert prompts == []
    
    @pytest.mark.unit
    def test_list_available_prompts_mixed_files(self):
        """Test listing prompts with mixed file types."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create various files
            files = [
                "prompt1.md",
                "prompt2.md", 
                "not_a_prompt.txt",
                "README.md",
                "config.json"
            ]
            
            for filename in files:
                with open(os.path.join(temp_dir, filename), 'w') as f:
                    f.write("content")
            
            # Create subdirectory (should be ignored)
            os.makedirs(os.path.join(temp_dir, "subdir"))
            
            pm = PromptManager(temp_dir)
            prompts = pm.list_available_prompts()
            
            expected = ["README", "prompt1", "prompt2"]
            assert set(prompts) == set(expected)
    
    @pytest.mark.unit
    def test_list_available_prompts_permission_error(self):
        """Test listing prompts with permission error."""
        pm = PromptManager("test_dir")
        
        with patch('os.path.exists', return_value=True), \
             patch('os.listdir', side_effect=PermissionError("Access denied")):
            prompts = pm.list_available_prompts()
            
            assert prompts == []


class TestGetPromptManager:
    """Test the get_prompt_manager function."""
    
    @pytest.mark.unit
    def test_get_prompt_manager_default(self):
        """Test getting prompt manager with default directory."""
        # Clear global instance
        import prompt_manager
        prompt_manager._prompt_manager = None
        
        pm = get_prompt_manager()
        
        assert isinstance(pm, PromptManager)
        assert pm.prompts_dir == "prompts"
    
    @pytest.mark.unit
    def test_get_prompt_manager_custom_directory(self):
        """Test getting prompt manager with custom directory."""
        # Clear global instance
        import prompt_manager
        prompt_manager._prompt_manager = None
        
        pm = get_prompt_manager("custom_prompts")
        
        assert isinstance(pm, PromptManager)
        assert pm.prompts_dir == "custom_prompts"
    
    @pytest.mark.unit
    def test_get_prompt_manager_singleton(self):
        """Test that get_prompt_manager returns singleton instance."""
        # Clear global instance
        import prompt_manager
        prompt_manager._prompt_manager = None
        
        pm1 = get_prompt_manager()
        pm2 = get_prompt_manager()
        
        assert pm1 is pm2  # Same instance


class TestPromptManagerIntegration:
    """Integration tests for PromptManager functionality."""
    
    @pytest.mark.integration
    def test_complete_prompt_workflow(self, temp_prompts_dir):
        """Test complete prompt loading workflow."""
        pm = PromptManager(temp_prompts_dir)
        
        # List available prompts
        available = pm.list_available_prompts()
        assert len(available) > 0
        
        # Load each available prompt
        for prompt_name in available:
            content = pm.get_prompt(prompt_name)
            assert isinstance(content, str)
            assert len(content) > 0
    
    @pytest.mark.integration
    def test_prompt_manager_with_real_files(self):
        """Test PromptManager with realistic prompt files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create realistic prompt files
            prompts = {
                "system_prompt.md": """You are a helpful AI assistant.

You should:
- Be helpful and accurate
- Provide clear explanations
- Ask for clarification when needed

Always be polite and professional.""",
                
                "agent_prompt.md": """You are a specialized agent for handling specific tasks.

Your capabilities include:
1. Task analysis
2. Action planning
3. Result verification

Use your tools effectively to complete tasks."""
            }
            
            for filename, content in prompts.items():
                filepath = os.path.join(temp_dir, filename)
                with open(filepath, 'w') as f:
                    f.write(content)
            
            pm = PromptManager(temp_dir)
            
            # Test loading prompts
            system_prompt = pm.get_prompt("system_prompt")
            agent_prompt = pm.get_prompt("agent_prompt")
            
            assert "helpful AI assistant" in system_prompt
            assert "specialized agent" in agent_prompt
            assert "capabilities include" in agent_prompt
            
            # Test listing
            available = pm.list_available_prompts()
            assert "system_prompt" in available
            assert "agent_prompt" in available


class TestPromptManagerEdgeCases:
    """Test edge cases and error conditions."""
    
    @pytest.mark.unit
    def test_get_prompt_very_long_filename(self, temp_prompts_dir):
        """Test getting prompt with very long filename."""
        long_name = "a" * 200  # Very long filename
        
        pm = PromptManager(temp_prompts_dir)
        
        with pytest.raises(FileNotFoundError):
            pm.get_prompt(long_name)
    
    @pytest.mark.unit
    def test_get_prompt_with_path_traversal(self, temp_prompts_dir):
        """Test prompt loading with path traversal attempt."""
        pm = PromptManager(temp_prompts_dir)
        
        # Try path traversal
        with pytest.raises(FileNotFoundError):
            pm.get_prompt("../../../etc/passwd")
    
    @pytest.mark.unit
    def test_get_prompt_with_special_characters(self):
        """Test prompt loading with special characters in filename."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create file with special characters (allowed in filename)
            special_name = "prompt-with_special.chars"
            filepath = os.path.join(temp_dir, f"{special_name}.md")
            with open(filepath, 'w') as f:
                f.write("Special prompt content")
            
            pm = PromptManager(temp_dir)
            content = pm.get_prompt(special_name)
            
            assert content == "Special prompt content"
    
    @pytest.mark.unit
    def test_prompt_manager_large_file(self):
        """Test loading a very large prompt file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create large prompt file
            large_content = "This is a line of text.\n" * 10000
            filepath = os.path.join(temp_dir, "large.md")
            with open(filepath, 'w') as f:
                f.write(large_content)
            
            pm = PromptManager(temp_dir)
            content = pm.get_prompt("large")
            
            assert len(content) > 100000
            assert "This is a line of text." in content
    
    @pytest.mark.unit
    def test_prompt_manager_concurrent_access(self, temp_prompts_dir):
        """Test PromptManager with concurrent access patterns."""
        import threading
        import time
        
        pm = PromptManager(temp_prompts_dir)
        results = []
        errors = []
        
        def load_prompt():
            try:
                content = pm.get_prompt("main_orchestrator_system")
                results.append(content)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=load_prompt)
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 10
        assert all(r == "You are a helpful AI assistant." for r in results)


class TestPromptManagerLogging:
    """Test logging behavior of PromptManager."""
    
    @pytest.mark.unit
    def test_logging_on_successful_load(self, temp_prompts_dir):
        """Test that successful prompt loading is logged."""
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = mock_get_logger.return_value
            
            pm = PromptManager(temp_prompts_dir)
            pm.get_prompt("main_orchestrator_system")
            
            # Should log debug message
            mock_logger.debug.assert_called_with("Loaded prompt: main_orchestrator_system.md")
    
    @pytest.mark.unit
    def test_logging_on_error(self, temp_prompts_dir):
        """Test that errors are logged properly."""
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = mock_get_logger.return_value
            
            pm = PromptManager(temp_prompts_dir)
            
            # Mock file read error
            with patch('builtins.open', side_effect=IOError("File error")):
                try:
                    pm.get_prompt("main_orchestrator_system")
                except IOError:
                    pass
                
                # Should log error
                mock_logger.error.assert_called()
                error_call_args = mock_logger.error.call_args[0][0]
                assert "Error loading prompt" in error_call_args