"""
Unit tests for config.py module.

This module contains tests for configuration loading functionality.
Focus: Simple, reliable tests for the load_json_setting function.
"""

import json
import os
import tempfile
import pytest
from unittest.mock import patch

# Import the function we're testing
from src.config import load_json_setting


class TestLoadJsonSetting:
    """Test suite for load_json_setting function."""

    def test_load_valid_json_file_success(self):
        """Test successful loading of a valid JSON configuration file."""
        # Create a temporary JSON file with test data
        test_config = {
            "temperature": 0.1,
            "max_tokens": 4000,
            "timeout": 30,
            "test_setting": "test_value"
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test file
            test_file = os.path.join(temp_dir, "test_config.json")
            with open(test_file, "w", encoding="utf-8") as f:
                json.dump(test_config, f)
            
            # Test the function
            result = load_json_setting("test_config.json", temp_dir)
            
            # Verify the result
            assert result == test_config
            assert result["temperature"] == 0.1
            assert result["max_tokens"] == 4000
            assert result["test_setting"] == "test_value"

    def test_load_json_file_not_found_raises_error(self):
        """Test that FileNotFoundError is raised when JSON file doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Try to load non-existent file
            with pytest.raises(FileNotFoundError) as exc_info:
                load_json_setting("nonexistent.json", temp_dir)
            
            # Verify error message contains expected information
            assert "Configuration file not found" in str(exc_info.value)
            assert "nonexistent.json" in str(exc_info.value)

    def test_load_invalid_json_raises_error(self):
        """Test that JSONDecodeError is raised for invalid JSON content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create file with invalid JSON
            test_file = os.path.join(temp_dir, "invalid.json")
            with open(test_file, "w", encoding="utf-8") as f:
                f.write("{ invalid json content")
            
            # Test that it raises JSONDecodeError
            with pytest.raises(json.JSONDecodeError):
                load_json_setting("invalid.json", temp_dir)

    def test_load_empty_json_file_raises_error(self):
        """Test that ValueError is raised for empty JSON file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create empty JSON file
            test_file = os.path.join(temp_dir, "empty.json")
            with open(test_file, "w", encoding="utf-8") as f:
                json.dump({}, f)  # Empty JSON object
            
            # Test that it raises ValueError for empty config
            with pytest.raises(ValueError) as exc_info:
                load_json_setting("empty.json", temp_dir)
            
            # Verify error message
            assert "Configuration file is empty" in str(exc_info.value)

    def test_filename_without_json_extension_works(self):
        """Test that function works correctly when .json extension is omitted."""
        test_config = {"test": "value"}
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test file
            test_file = os.path.join(temp_dir, "test_config.json")
            with open(test_file, "w", encoding="utf-8") as f:
                json.dump(test_config, f)
            
            # Test without .json extension
            result = load_json_setting("test_config", temp_dir)
            
            # Verify the result
            assert result == test_config