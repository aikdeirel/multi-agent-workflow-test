import json
import os
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable loading and validation."""

    # Langfuse Cloud settings
    langfuse_public_key: str = Field(env="LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: str = Field(env="LANGFUSE_SECRET_KEY")
    langfuse_host: str = Field(
        default="https://cloud.langfuse.com", env="LANGFUSE_HOST"
    )

    # LLM settings
    mistral_api_key: str = Field(env="MISTRAL_API_KEY")

    # Application settings
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    class Config:
        case_sensitive = False


def load_json_setting(filename: str, settings_dir: str = "settings") -> Dict[str, Any]:
    """
    Load JSON configuration from file. Always reads from disk for hot-reload.

    Args:
        filename: Name of the JSON file (with or without .json extension)
        settings_dir: Directory containing settings files

    Returns:
        Dictionary containing the configuration

    Raises:
        FileNotFoundError: If the configuration file doesn't exist
        json.JSONDecodeError: If the JSON is invalid
        ValueError: If the configuration is empty or invalid
    """
    if not filename.endswith(".json"):
        filename += ".json"

    filepath = os.path.join(settings_dir, filename)

    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Configuration file not found: {filepath}")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            config = json.load(f)

        if not config:
            raise ValueError(f"Configuration file is empty: {filepath}")

        return config

    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Invalid JSON in {filepath}: {e.msg}", e.doc, e.pos)
    except Exception as e:
        raise ValueError(f"Error loading configuration from {filepath}: {str(e)}")


def get_settings() -> Settings:
    """Get validated application settings."""
    try:
        return Settings()
    except Exception as e:
        raise ValueError(f"Configuration validation failed: {str(e)}")


def validate_required_settings(settings: Settings) -> None:
    """Validate that all required settings are present and valid."""
    required_fields = ["langfuse_public_key", "langfuse_secret_key", "mistral_api_key"]

    missing_fields = []
    for field in required_fields:
        value = getattr(settings, field, None)
        if not value or value.strip() == "":
            missing_fields.append(field)

    if missing_fields:
        raise ValueError(
            f"Missing required configuration fields: {', '.join(missing_fields)}"
        )


# Global settings instance
_settings: Optional[Settings] = None


def get_global_settings() -> Settings:
    """Get global settings instance, creating it if needed."""
    global _settings
    if _settings is None:
        _settings = get_settings()
        validate_required_settings(_settings)
    return _settings
