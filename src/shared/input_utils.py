import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def parse_json_input(input_value: Any, expected_key: str) -> str:
    """
    Parse JSON input that may be passed by LangChain and extract the expected value.
    
    Args:
        input_value: The input value that might be JSON or a plain string
        expected_key: The key to extract from JSON (e.g., "location", "expression", "date")
        
    Returns:
        The extracted string value
    """
    if not isinstance(input_value, str):
        return str(input_value) if input_value is not None else ""
    
    # Check if it looks like JSON
    if input_value.startswith('{"') or input_value.startswith("{'"):
        try:
            # Try to parse as JSON and extract the expected key
            data = json.loads(input_value.replace("'", '"'))
            if isinstance(data, dict) and expected_key in data:
                extracted_value = data[expected_key]
                logger.debug(f"Extracted {expected_key} from JSON: {extracted_value}")
                return str(extracted_value)
        except (json.JSONDecodeError, KeyError):
            # If JSON parsing fails, return the original string
            pass
    
    return input_value.strip() if input_value else ""


def parse_location_input(location: str) -> str:
    """Parse location input, handling JSON format."""
    return parse_json_input(location, "location")


def parse_expression_input(expression: str) -> str:
    """Parse mathematical expression input, handling JSON format."""
    return parse_json_input(expression, "expression")


def parse_date_input(date: str) -> str:
    """Parse date input, handling JSON format."""
    return parse_json_input(date, "date")


def parse_year_input(year: str) -> str:
    """Parse year input, handling JSON format."""
    return parse_json_input(year, "year")


def parse_target_date_input(target_date: str) -> str:
    """Parse target_date input, handling JSON format."""
    return parse_json_input(target_date, "target_date")


def parse_birth_date_input(birth_date: str) -> str:
    """Parse birth_date input, handling JSON format."""
    return parse_json_input(birth_date, "birth_date")


def parse_dual_date_input(input_str: str) -> Dict[str, str]:
    """
    Parse input that may contain two dates (start_date and end_date).
    
    Args:
        input_str: Input string that may be JSON with start_date and end_date
        
    Returns:
        Dictionary with parsed start_date and end_date
    """
    if not isinstance(input_str, str):
        return {"start_date": "", "end_date": ""}
    
    # Check if it looks like JSON
    if input_str.startswith('{"') or input_str.startswith("{'"):
        try:
            # Try to parse as JSON and extract both dates
            data = json.loads(input_str.replace("'", '"'))
            if isinstance(data, dict):
                start_date = data.get("start_date", "")
                end_date = data.get("end_date", "")
                logger.debug(f"Extracted from JSON - start: {start_date}, end: {end_date}")
                return {"start_date": str(start_date), "end_date": str(end_date)}
        except (json.JSONDecodeError, KeyError):
            # If JSON parsing fails, return empty
            pass
    
    return {"start_date": "", "end_date": ""}