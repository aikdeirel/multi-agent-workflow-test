"""
Unit tests for the config module.

Tests settings validation, JSON configuration loading, and error handling.
"""

import pytest
import json
import os
import tempfile
from unittest.mock import patch, mock_open
from pydantic import ValidationError

from config import (
    Settings,
    load_json_setting,
    get_settings,
    validate_required_settings,
    get_global_settings
)


class TestSettings:
    """Test the Settings pydantic model."""
    
    @pytest.mark.unit
    def test_settings_with_valid_env_vars(self, mock_env_vars):
        """Test Settings creation with valid environment variables."""
        settings = Settings()
        
        assert settings.langfuse_public_key == "pk-lf-test-key"
        assert settings.langfuse_secret_key == "sk-lf-test-secret"
        assert settings.langfuse_host == "https://test.langfuse.com"
        assert settings.mistral_api_key == "test-mistral-key"
        assert settings.mistral_model == "mistral-test"
        assert settings.log_level == "INFO"
    
    @pytest.mark.unit
    def test_settings_default_values(self, mock_env_vars):
        """Test Settings default values."""
        with patch.dict(os.environ, {
            'LANGFUSE_PUBLIC_KEY': 'pk-test',
            'LANGFUSE_SECRET_KEY': 'sk-test',
            'MISTRAL_API_KEY': 'mistral-test'
        }, clear=True):
            settings = Settings()
            
            assert settings.langfuse_host == "https://cloud.langfuse.com"  # default
            assert settings.mistral_model == "mistral-medium-latest"  # default
            assert settings.log_level == "INFO"  # default
    
    @pytest.mark.unit
    def test_settings_missing_required_field(self):
        """Test Settings validation with missing required fields."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            
            # Should fail due to missing required fields
            assert "langfuse_public_key" in str(exc_info.value)
    
    @pytest.mark.unit
    def test_settings_case_insensitive(self):
        """Test that Settings is case insensitive."""
        with patch.dict(os.environ, {
            'langfuse_public_key': 'pk-test-lower',  # lowercase
            'LANGFUSE_SECRET_KEY': 'sk-test-upper',  # uppercase
            'MISTRAL_API_KEY': 'mistral-test'
        }, clear=True):
            settings = Settings()
            
            assert settings.langfuse_public_key == "pk-test-lower"
            assert settings.langfuse_secret_key == "sk-test-upper"


class TestLoadJsonSetting:
    """Test the load_json_setting function."""
    
    @pytest.mark.unit
    def test_load_valid_json_file(self, temp_settings_dir):
        """Test loading a valid JSON configuration file."""
        config = load_json_setting("model_config", temp_settings_dir)
        
        assert config["temperature"] == 0.7
        assert config["max_tokens"] == 1000
        assert config["timeout"] == 30
    
    @pytest.mark.unit
    def test_load_json_file_without_extension(self, temp_settings_dir):
        """Test loading JSON file without .json extension."""
        config = load_json_setting("model_config", temp_settings_dir)
        
        assert isinstance(config, dict)
        assert "temperature" in config
    
    @pytest.mark.unit
    def test_load_json_file_with_extension(self, temp_settings_dir):
        """Test loading JSON file with .json extension."""
        config = load_json_setting("model_config.json", temp_settings_dir)
        
        assert isinstance(config, dict)
        assert "temperature" in config
    
    @pytest.mark.unit
    def test_load_nonexistent_file(self, temp_settings_dir):
        """Test loading a non-existent JSON file."""
        with pytest.raises(FileNotFoundError) as exc_info:
            load_json_setting("nonexistent", temp_settings_dir)
        
        assert "Configuration file not found" in str(exc_info.value)
    
    @pytest.mark.unit
    def test_load_invalid_json(self):
        """Test loading an invalid JSON file."""
        invalid_json = '{"key": value,}'  # Invalid JSON
        
        with tempfile.TemporaryDirectory() as temp_dir:
            filepath = os.path.join(temp_dir, "invalid.json")
            with open(filepath, 'w') as f:
                f.write(invalid_json)
            
            with pytest.raises(json.JSONDecodeError):
                load_json_setting("invalid", temp_dir)
    
    @pytest.mark.unit
    def test_load_empty_json_file(self):
        """Test loading an empty JSON file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            filepath = os.path.join(temp_dir, "empty.json")
            with open(filepath, 'w') as f:
                f.write("")
            
            with pytest.raises(ValueError) as exc_info:
                load_json_setting("empty", temp_dir)
            
            assert "Configuration file is empty" in str(exc_info.value)
    
    @pytest.mark.unit
    def test_load_json_with_empty_dict(self):
        """Test loading JSON file with empty dictionary."""
        with tempfile.TemporaryDirectory() as temp_dir:
            filepath = os.path.join(temp_dir, "empty_dict.json")
            with open(filepath, 'w') as f:
                json.dump({}, f)
            
            with pytest.raises(ValueError) as exc_info:
                load_json_setting("empty_dict", temp_dir)
            
            assert "Configuration file is empty" in str(exc_info.value)
    
    @pytest.mark.unit
    def test_load_json_permission_error(self):
        """Test loading JSON file with permission errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            filepath = os.path.join(temp_dir, "test.json")
            
            # Create file then make it unreadable
            with open(filepath, 'w') as f:
                json.dump({"test": "value"}, f)
            
            # Mock permission error
            with patch('builtins.open', side_effect=PermissionError("Permission denied")):
                with pytest.raises(ValueError) as exc_info:
                    load_json_setting("test", temp_dir)
                
                assert "Error loading configuration" in str(exc_info.value)


class TestGetSettings:
    """Test the get_settings function."""
    
    @pytest.mark.unit
    def test_get_settings_success(self, mock_env_vars):
        """Test successful settings retrieval."""
        settings = get_settings()
        
        assert isinstance(settings, Settings)
        assert settings.langfuse_public_key == "pk-lf-test-key"
    
    @pytest.mark.unit
    def test_get_settings_validation_error(self):
        """Test get_settings with validation error."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                get_settings()
            
            assert "Configuration validation failed" in str(exc_info.value)


class TestValidateRequiredSettings:
    """Test the validate_required_settings function."""
    
    @pytest.mark.unit
    def test_validate_all_required_fields_present(self, mock_settings):
        """Test validation with all required fields present."""
        # Should not raise any exception
        validate_required_settings(mock_settings)
    
    @pytest.mark.unit
    def test_validate_missing_langfuse_public_key(self, mock_settings):
        """Test validation with missing langfuse_public_key."""
        mock_settings.langfuse_public_key = ""
        
        with pytest.raises(ValueError) as exc_info:
            validate_required_settings(mock_settings)
        
        assert "langfuse_public_key" in str(exc_info.value)
    
    @pytest.mark.unit
    def test_validate_missing_langfuse_secret_key(self, mock_settings):
        """Test validation with missing langfuse_secret_key."""
        mock_settings.langfuse_secret_key = None
        
        with pytest.raises(ValueError) as exc_info:
            validate_required_settings(mock_settings)
        
        assert "langfuse_secret_key" in str(exc_info.value)
    
    @pytest.mark.unit
    def test_validate_missing_mistral_api_key(self, mock_settings):
        """Test validation with missing mistral_api_key."""
        mock_settings.mistral_api_key = "   "  # whitespace only
        
        with pytest.raises(ValueError) as exc_info:
            validate_required_settings(mock_settings)
        
        assert "mistral_api_key" in str(exc_info.value)
    
    @pytest.mark.unit
    def test_validate_multiple_missing_fields(self, mock_settings):
        """Test validation with multiple missing fields."""
        mock_settings.langfuse_public_key = ""
        mock_settings.mistral_api_key = ""
        
        with pytest.raises(ValueError) as exc_info:
            validate_required_settings(mock_settings)
        
        error_msg = str(exc_info.value)
        assert "langfuse_public_key" in error_msg
        assert "mistral_api_key" in error_msg


class TestGetGlobalSettings:
    """Test the get_global_settings function."""
    
    @pytest.mark.unit
    def test_get_global_settings_first_call(self, mock_env_vars):
        """Test first call to get_global_settings creates instance."""
        # Clear any existing global settings
        import config
        config._settings = None
        
        settings = get_global_settings()
        
        assert isinstance(settings, Settings)
        assert settings.langfuse_public_key == "pk-lf-test-key"
    
    @pytest.mark.unit
    def test_get_global_settings_subsequent_calls(self, mock_env_vars):
        """Test subsequent calls return same instance."""
        import config
        config._settings = None
        
        settings1 = get_global_settings()
        settings2 = get_global_settings()
        
        assert settings1 is settings2  # Same instance
    
    @pytest.mark.unit
    def test_get_global_settings_validation_error(self):
        """Test get_global_settings with validation error."""
        import config
        config._settings = None
        
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                get_global_settings()
            
            assert "Missing required configuration fields" in str(exc_info.value)


class TestSettingsIntegration:
    """Integration tests for settings functionality."""
    
    @pytest.mark.integration
    def test_complete_settings_workflow(self, mock_env_vars, temp_settings_dir):
        """Test complete settings loading workflow."""
        # Load JSON config
        model_config = load_json_setting("model_config", temp_settings_dir)
        
        # Create settings
        settings = get_settings()
        
        # Validate settings
        validate_required_settings(settings)
        
        # Assert everything works together
        assert isinstance(model_config, dict)
        assert model_config["temperature"] == 0.7
        assert isinstance(settings, Settings)
        assert settings.langfuse_public_key == "pk-lf-test-key"
    
    @pytest.mark.integration
    def test_settings_environment_override(self):
        """Test that environment variables properly override defaults."""
        custom_values = {
            'LANGFUSE_PUBLIC_KEY': 'pk-custom',
            'LANGFUSE_SECRET_KEY': 'sk-custom',
            'LANGFUSE_HOST': 'https://custom.langfuse.com',
            'MISTRAL_API_KEY': 'custom-mistral-key',
            'MISTRAL_MODEL': 'custom-model',
            'LOG_LEVEL': 'DEBUG'
        }
        
        with patch.dict(os.environ, custom_values, clear=True):
            settings = Settings()
            
            assert settings.langfuse_public_key == "pk-custom"
            assert settings.langfuse_secret_key == "sk-custom"
            assert settings.langfuse_host == "https://custom.langfuse.com"
            assert settings.mistral_api_key == "custom-mistral-key"
            assert settings.mistral_model == "custom-model"
            assert settings.log_level == "DEBUG"


class TestConfigEdgeCases:
    """Test edge cases and error conditions."""
    
    @pytest.mark.unit
    def test_load_json_with_unicode_content(self):
        """Test loading JSON with unicode content."""
        unicode_content = {"message": "Hello 世界", "emoji": "🌍"}
        
        with tempfile.TemporaryDirectory() as temp_dir:
            filepath = os.path.join(temp_dir, "unicode.json")
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(unicode_content, f, ensure_ascii=False)
            
            config = load_json_setting("unicode", temp_dir)
            
            assert config["message"] == "Hello 世界"
            assert config["emoji"] == "🌍"
    
    @pytest.mark.unit
    def test_load_json_large_file(self):
        """Test loading a large JSON configuration file."""
        large_config = {f"key_{i}": f"value_{i}" for i in range(1000)}
        
        with tempfile.TemporaryDirectory() as temp_dir:
            filepath = os.path.join(temp_dir, "large.json")
            with open(filepath, 'w') as f:
                json.dump(large_config, f)
            
            config = load_json_setting("large", temp_dir)
            
            assert len(config) == 1000
            assert config["key_0"] == "value_0"
            assert config["key_999"] == "value_999"
    
    @pytest.mark.unit
    def test_settings_with_special_characters(self):
        """Test Settings with special characters in values."""
        special_values = {
            'LANGFUSE_PUBLIC_KEY': 'pk-test!@#$%^&*()',
            'LANGFUSE_SECRET_KEY': 'sk-test_with-dashes.and.dots',
            'MISTRAL_API_KEY': 'key+with+plus+signs',
            'LANGFUSE_HOST': 'https://test.example.com:8080/path?query=value'
        }
        
        with patch.dict(os.environ, special_values, clear=True):
            settings = Settings()
            
            assert settings.langfuse_public_key == "pk-test!@#$%^&*()"
            assert settings.langfuse_secret_key == "sk-test_with-dashes.and.dots"
            assert settings.mistral_api_key == "key+with+plus+signs"
            assert settings.langfuse_host == "https://test.example.com:8080/path?query=value"