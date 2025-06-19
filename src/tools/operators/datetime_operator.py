import requests
import logging
from typing import Optional, Dict, Any, Union
from datetime import datetime

from langchain.tools import tool

logger = logging.getLogger(__name__)

# digidatesAPI base URL
DIGIDATES_API_URL = "https://digidates.de/api/v1"


def make_digidates_request(
    endpoint: str, params: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """
    Make a request to the digidatesAPI.

    Args:
        endpoint: API endpoint (e.g., "/unixtime", "/countdown/2024-12-31")
        params: Query parameters as dictionary

    Returns:
        JSON response data or None if error
    """
    try:
        url = f"{DIGIDATES_API_URL}{endpoint}"
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        # Handle different response types
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return response.json()
        else:
            # Sometimes API returns plain text/numbers
            try:
                return {"result": response.json()}
            except:
                return {"result": response.text}

    except requests.exceptions.RequestException as e:
        logger.error(f"Request error for {endpoint}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error processing response from {endpoint}: {str(e)}")
        return None


@tool
def get_unix_time(timestamp: Optional[str] = None) -> str:
    """
    Get Unix timestamp for current time or convert a given timestamp to Unix time.

    Args:
        timestamp: Optional timestamp to convert (e.g., "1970-01-01 00:00:01", "Sat, 01 Jan 2022 00:00:00")

    Returns:
        String containing Unix timestamp information

    Examples:
        - get_unix_time() -> Get current Unix time
        - get_unix_time("2022-01-01 00:00:00") -> Convert to Unix time
    """
    logger.info(f"Getting Unix time for timestamp: {timestamp}")

    try:
        # Handle case where LangChain passes JSON string or empty dict instead of raw value
        import json

        actual_timestamp = timestamp

        if isinstance(timestamp, str):
            # Check if it contains "Observation:" which means agent passed entire observation
            if "Observation:" in timestamp:
                logger.debug("Detected agent passed entire observation, ignoring")
                actual_timestamp = None
            elif timestamp.startswith("{"):
                try:
                    # Try to parse as JSON and extract the timestamp
                    data = json.loads(timestamp)
                    if isinstance(data, dict) and "timestamp" in data:
                        actual_timestamp = data["timestamp"]
                        logger.debug(
                            f"Extracted timestamp from JSON: {actual_timestamp}"
                        )
                    elif isinstance(data, dict) and not data:  # Empty dict
                        actual_timestamp = None
                except (json.JSONDecodeError, KeyError):
                    # If JSON parsing fails, use the original string
                    actual_timestamp = timestamp
            elif timestamp == "{}":  # Empty dict as string
                actual_timestamp = None
            elif timestamp.strip() == "":  # Empty or whitespace
                actual_timestamp = None

        params = {}
        if actual_timestamp:
            params["timestamp"] = actual_timestamp

        result = make_digidates_request("/unixtime", params)

        if result is None:
            return "Error: Unable to retrieve Unix time from the API"

        if isinstance(result, dict):
            if "time" in result:
                unix_time = result["time"]
            elif "result" in result:
                unix_time = result["result"]
            else:
                unix_time = result
        else:
            unix_time = result

        if actual_timestamp:
            # Also return the date format for easier processing
            try:
                from datetime import datetime

                dt = datetime.fromtimestamp(int(unix_time))
                date_str = dt.strftime("%Y-%m-%d")
                return f"Unix timestamp for '{actual_timestamp}': {unix_time} (Date: {date_str})"
            except:
                return f"Unix timestamp for '{actual_timestamp}': {unix_time}"
        else:
            # Return current time with both unix and readable format
            try:
                from datetime import datetime

                dt = datetime.fromtimestamp(int(unix_time))
                date_str = dt.strftime("%Y-%m-%d")
                return f"Current Unix timestamp: {unix_time} (Current date: {date_str})"
            except:
                return f"Current Unix timestamp: {unix_time}"

    except Exception as e:
        logger.error(f"Error getting Unix time: {str(e)}")
        return f"Error getting Unix time: {str(e)}"


@tool
def get_week_number(date: str) -> str:
    """
    Get the week number for a given date.

    Args:
        date: Date in format "YYYY-MM-DD" (e.g., "2022-01-01")

    Returns:
        String containing week number information

    Examples:
        - get_week_number("2022-01-01") -> Get week number for January 1st, 2022
    """
    logger.info(f"Getting week number for date: {date}")

    try:
        # Handle case where LangChain passes JSON string instead of raw value
        import json

        actual_date = date
        if isinstance(date, str) and date.startswith("{"):
            try:
                # Try to parse as JSON and extract the date
                data = json.loads(date)
                if isinstance(data, dict) and "date" in data:
                    actual_date = data["date"]
                    logger.debug(f"Extracted date from JSON: {actual_date}")
            except (json.JSONDecodeError, KeyError):
                # If JSON parsing fails, use the original string
                actual_date = date

        params = {"date": actual_date}
        result = make_digidates_request("/week", params)

        if result is None:
            return f"Error: Unable to retrieve week number for date {actual_date}"

        if isinstance(result, dict) and "result" in result:
            week_num = result["result"]
        else:
            week_num = result

        return f"Week number for {actual_date}: {week_num}"

    except Exception as e:
        logger.error(f"Error getting week number: {str(e)}")
        return f"Error getting week number for {date}: {str(e)}"


@tool
def check_leap_year(year: str) -> str:
    """
    Check if a given year is a leap year.

    Args:
        year: Year as string (e.g., "2020")

    Returns:
        String indicating whether the year is a leap year

    Examples:
        - check_leap_year("2020") -> Check if 2020 is a leap year
        - check_leap_year("2021") -> Check if 2021 is a leap year
    """
    logger.info(f"Checking if year {year} is a leap year")

    try:
        # Handle case where LangChain passes JSON string instead of raw value
        import json

        actual_year = year
        if isinstance(year, str) and year.startswith("{"):
            try:
                # Try to parse as JSON and extract the year
                data = json.loads(year)
                if isinstance(data, dict) and "year" in data:
                    actual_year = data["year"]
                    logger.debug(f"Extracted year from JSON: {actual_year}")
            except (json.JSONDecodeError, KeyError):
                # If JSON parsing fails, use the original string
                actual_year = year

        params = {"year": actual_year}
        result = make_digidates_request("/leapyear", params)

        if result is None:
            return f"Error: Unable to check leap year for {actual_year}"

        if isinstance(result, dict) and "result" in result:
            is_leap = result["result"]
        else:
            is_leap = result

        return (
            f"Year {actual_year} is {'a leap year' if is_leap else 'not a leap year'}"
        )

    except Exception as e:
        logger.error(f"Error checking leap year: {str(e)}")
        return f"Error checking leap year for {year}: {str(e)}"


@tool
def validate_date(date: str) -> str:
    """
    Check if a given date is valid.

    Args:
        date: Date in format "YYYY-MM-DD" (e.g., "2020-01-01")

    Returns:
        String indicating whether the date is valid

    Examples:
        - validate_date("2020-01-01") -> Check if date is valid
        - validate_date("2020-13-01") -> Check invalid date
    """
    logger.info(f"Validating date: {date}")

    try:
        # Handle case where LangChain passes JSON string instead of raw value
        import json

        actual_date = date
        if isinstance(date, str) and date.startswith("{"):
            try:
                # Try to parse as JSON and extract the date
                data = json.loads(date)
                if isinstance(data, dict) and "date" in data:
                    actual_date = data["date"]
                    logger.debug(f"Extracted date from JSON: {actual_date}")
            except (json.JSONDecodeError, KeyError):
                # If JSON parsing fails, use the original string
                actual_date = date

        params = {"date": actual_date}
        result = make_digidates_request("/checkdate", params)

        if result is None:
            return f"Error: Unable to validate date {actual_date}"

        if isinstance(result, dict) and "result" in result:
            is_valid = result["result"]
        else:
            is_valid = result

        return f"Date {actual_date} is {'valid' if is_valid else 'invalid'}"

    except Exception as e:
        logger.error(f"Error validating date: {str(e)}")
        return f"Error validating date {date}: {str(e)}"


@tool
def get_weekday(date: str) -> str:
    """
    Get the weekday for a given date.

    Args:
        date: Date in format "YYYY-MM-DD" (e.g., "2020-01-01")

    Returns:
        String containing weekday information (0=Sunday, 1=Monday, etc.)

    Examples:
        - get_weekday("2020-01-01") -> Get weekday for January 1st, 2020
    """
    logger.info(f"Getting weekday for date: {date}")

    try:
        # Handle case where LangChain passes JSON string instead of raw value
        import json

        actual_date = date
        if isinstance(date, str) and date.startswith("{"):
            try:
                # Try to parse as JSON and extract the date
                data = json.loads(date)
                if isinstance(data, dict) and "date" in data:
                    actual_date = data["date"]
                    logger.debug(f"Extracted date from JSON: {actual_date}")
            except (json.JSONDecodeError, KeyError):
                # If JSON parsing fails, use the original string
                actual_date = date

        params = {"date": actual_date}
        result = make_digidates_request("/weekday", params)

        if result is None:
            return f"Error: Unable to get weekday for date {actual_date}"

        if isinstance(result, dict) and "result" in result:
            weekday_num = result["result"]
        else:
            weekday_num = result

        # Convert number to weekday name
        weekdays = [
            "Sunday",
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
        ]
        if isinstance(weekday_num, int) and 0 <= weekday_num <= 6:
            weekday_name = weekdays[weekday_num]
            return f"Date {actual_date} falls on a {weekday_name} (weekday number: {weekday_num})"
        else:
            return f"Weekday number for {actual_date}: {weekday_num}"

    except Exception as e:
        logger.error(f"Error getting weekday: {str(e)}")
        return f"Error getting weekday for {date}: {str(e)}"


@tool
def calculate_progress(start_date: str, end_date: str) -> str:
    """
    Calculate progress between two dates.

    Args:
        start_date: Start date in format "YYYY-MM-DD" (e.g., "2022-01-01")
        end_date: End date in format "YYYY-MM-DD" (e.g., "2022-12-31")

    Returns:
        String containing progress information

    Examples:
        - calculate_progress("2022-01-01", "2022-12-31") -> Progress from start to end of 2022
    """
    logger.info(f"Calculating progress from {start_date} to {end_date}")

    try:
        # Handle case where LangChain passes JSON string instead of raw values
        import json

        actual_start_date = start_date
        actual_end_date = end_date

        if isinstance(start_date, str) and start_date.startswith("{"):
            try:
                # Try to parse as JSON and extract both start_date and end_date
                data = json.loads(start_date)
                if isinstance(data, dict):
                    actual_start_date = data.get("start_date", start_date)
                    actual_end_date = data.get("end_date", end_date)
                    logger.debug(
                        f"Extracted from JSON - start: {actual_start_date}, end: {actual_end_date}"
                    )
            except (json.JSONDecodeError, KeyError):
                # If JSON parsing fails, use the original values
                actual_start_date = start_date
                actual_end_date = end_date

        params = {"start": actual_start_date, "end": actual_end_date}
        result = make_digidates_request("/progress", params)

        if result is None:
            return (
                f"Error: Unable to calculate progress from {start_date} to {end_date}"
            )

        if isinstance(result, dict):
            if "result" in result:
                progress_data = result["result"]
            else:
                progress_data = result

            if isinstance(progress_data, dict):
                float_progress = progress_data.get("float", "N/A")
                percent_progress = progress_data.get("percent", "N/A")
                return f"Progress from {actual_start_date} to {actual_end_date}: {percent_progress}% ({float_progress} as decimal)"
            else:
                return f"Progress from {actual_start_date} to {actual_end_date}: {progress_data}"
        else:
            return f"Progress from {actual_start_date} to {actual_end_date}: {result}"

    except Exception as e:
        logger.error(f"Error calculating progress: {str(e)}")
        return f"Error calculating progress from {actual_start_date} to {actual_end_date}: {str(e)}"


@tool
def countdown_to_date(target_date: str) -> str:
    """
    Calculate countdown to a specific date.

    Args:
        target_date: Target date in format "YYYY-MM-DD" (e.g., "2024-12-31")

    Returns:
        String containing countdown information

    Examples:
        - countdown_to_date("2024-12-31") -> Countdown to New Year's Eve 2024
        - countdown_to_date("2024-12-25") -> Countdown to Christmas 2024
    """
    logger.info(f"Calculating countdown to date: {target_date}")

    try:
        # Handle case where LangChain passes JSON string instead of raw value
        import json

        actual_target_date = target_date
        if isinstance(target_date, str) and target_date.startswith("{"):
            try:
                # Try to parse as JSON and extract the target_date
                data = json.loads(target_date)
                if isinstance(data, dict) and "target_date" in data:
                    actual_target_date = data["target_date"]
                    logger.debug(
                        f"Extracted target_date from JSON: {actual_target_date}"
                    )
            except (json.JSONDecodeError, KeyError):
                # If JSON parsing fails, use the original string
                actual_target_date = target_date

        result = make_digidates_request(f"/countdown/{actual_target_date}")

        if result is None:
            return f"Error: Unable to calculate countdown to {actual_target_date}"

        if isinstance(result, dict):
            if "result" in result:
                countdown_data = result["result"]
            else:
                countdown_data = result

            if isinstance(countdown_data, dict):
                days_only = countdown_data.get("daysonly", "N/A")
                extended = countdown_data.get("countdownextended", {})

                response_parts = [f"Countdown to {actual_target_date}:"]
                response_parts.append(f"• Total days: {days_only}")

                if isinstance(extended, dict):
                    years = extended.get("years", 0)
                    months = extended.get("months", 0)
                    days = extended.get("days", 0)
                    if years or months or days:
                        response_parts.append(
                            f"• Extended: {years} years, {months} months, {days} days"
                        )

                return "\n".join(response_parts)
            else:
                return f"Countdown to {actual_target_date}: {countdown_data}"
        else:
            return f"Countdown to {actual_target_date}: {result}"

    except Exception as e:
        logger.error(f"Error calculating countdown: {str(e)}")
        return f"Error calculating countdown to {target_date}: {str(e)}"


@tool
def calculate_age(birth_date: str) -> str:
    """
    Calculate age from a birth date.

    Args:
        birth_date: Birth date in format "YYYY-MM-DD" (e.g., "1990-01-01")

    Returns:
        String containing age information

    Examples:
        - calculate_age("1990-01-01") -> Calculate age for someone born on January 1st, 1990
    """
    logger.info(f"Calculating age for birth date: {birth_date}")

    try:
        # Handle case where LangChain passes JSON string instead of raw value
        import json

        actual_birth_date = birth_date
        if isinstance(birth_date, str) and birth_date.startswith("{"):
            try:
                # Try to parse as JSON and extract the birth_date
                data = json.loads(birth_date)
                if isinstance(data, dict) and "birth_date" in data:
                    actual_birth_date = data["birth_date"]
                    logger.debug(f"Extracted birth_date from JSON: {actual_birth_date}")
            except (json.JSONDecodeError, KeyError):
                # If JSON parsing fails, use the original string
                actual_birth_date = birth_date

        result = make_digidates_request(f"/age/{actual_birth_date}")

        if result is None:
            return f"Error: Unable to calculate age for birth date {actual_birth_date}"

        if isinstance(result, dict):
            if "result" in result:
                age_data = result["result"]
            else:
                age_data = result

            if isinstance(age_data, dict):
                age = age_data.get("age", "N/A")
                extended = age_data.get("ageextended", {})

                response_parts = [f"Age for birth date {actual_birth_date}:"]
                response_parts.append(f"• Age: {age} years")

                if isinstance(extended, dict):
                    years = extended.get("years", 0)
                    months = extended.get("months", 0)
                    days = extended.get("days", 0)
                    if years or months or days:
                        response_parts.append(
                            f"• Detailed: {years} years, {months} months, {days} days"
                        )

                return "\n".join(response_parts)
            else:
                return f"Age for birth date {actual_birth_date}: {age_data}"
        else:
            return f"Age for birth date {actual_birth_date}: {result}"

    except Exception as e:
        logger.error(f"Error calculating age: {str(e)}")
        return f"Error calculating age for birth date {birth_date}: {str(e)}"


@tool
def get_co2_level(year: str) -> str:
    """
    Get CO2 level for a given year.

    Args:
        year: Year between 1959 and present (e.g., "2020")

    Returns:
        String containing CO2 level information

    Examples:
        - get_co2_level("2020") -> Get CO2 level for 2020
    """
    logger.info(f"Getting CO2 level for year: {year}")

    try:
        # Handle case where LangChain passes JSON string instead of raw value
        import json

        actual_year = year
        if isinstance(year, str) and year.startswith("{"):
            try:
                # Try to parse as JSON and extract the year
                data = json.loads(year)
                if isinstance(data, dict) and "year" in data:
                    actual_year = data["year"]
                    logger.debug(f"Extracted year from JSON: {actual_year}")
            except (json.JSONDecodeError, KeyError):
                # If JSON parsing fails, use the original string
                actual_year = year

        result = make_digidates_request(f"/co2/{actual_year}")

        if result is None:
            return f"Error: Unable to get CO2 level for year {actual_year}"

        if isinstance(result, dict):
            if "result" in result:
                co2_data = result["result"]
            else:
                co2_data = result

            if isinstance(co2_data, dict):
                co2_level = co2_data.get("co2", "N/A")
                return f"CO2 level for year {actual_year}: {co2_level} PPM"
            else:
                return f"CO2 level for year {actual_year}: {co2_data}"
        else:
            return f"CO2 level for year {actual_year}: {result}"

    except Exception as e:
        logger.error(f"Error getting CO2 level: {str(e)}")
        return f"Error getting CO2 level for year {year}: {str(e)}"


@tool
def get_german_holidays(
    year: Optional[str] = None, region: Optional[str] = None
) -> str:
    """
    Get German public holidays for a given year and region.

    Args:
        year: Year (e.g., "2022"). If not provided, current year is used.
        region: Region code (e.g., "de-bb"). If not provided, federal holidays are returned.

    Returns:
        String containing German public holidays

    Examples:
        - get_german_holidays("2022") -> Get federal holidays for 2022
        - get_german_holidays("2022", "de-bb") -> Get holidays for Brandenburg in 2022
    """
    logger.info(f"Getting German holidays for year: {year}, region: {region}")

    try:
        # Handle case where LangChain passes JSON string instead of raw values
        import json

        actual_year = year
        actual_region = region

        if isinstance(year, str) and year.startswith("{"):
            try:
                # Try to parse as JSON and extract both year and region
                data = json.loads(year)
                if isinstance(data, dict):
                    actual_year = data.get("year", year)
                    actual_region = data.get("region", region)
                    logger.debug(
                        f"Extracted from JSON - year: {actual_year}, region: {actual_region}"
                    )
            except (json.JSONDecodeError, KeyError):
                # If JSON parsing fails, use the original values
                actual_year = year
                actual_region = region

        params = {}
        if actual_year:
            params["year"] = actual_year
        if actual_region:
            params["region"] = actual_region

        result = make_digidates_request("/germanpublicholidays", params)

        if result is None:
            return f"Error: Unable to get German holidays"

        if isinstance(result, dict) and "result" in result:
            holidays_data = result["result"]
        else:
            holidays_data = result

        if isinstance(holidays_data, list):
            year_str = actual_year if actual_year else "current year"
            region_str = f" in region {actual_region}" if actual_region else ""

            response_parts = [f"German public holidays for {year_str}{region_str}:"]
            for i, holiday in enumerate(holidays_data, 1):
                response_parts.append(f"{i}. {holiday}")

            return "\n".join(response_parts)
        else:
            return f"German public holidays: {holidays_data}"

    except Exception as e:
        logger.error(f"Error getting German holidays: {str(e)}")
        return f"Error getting German holidays: {str(e)}"


@tool
def datetime_help() -> str:
    """
    Get help information about datetime operator capabilities.

    Returns:
        String containing help information about available datetime functions
    """
    help_text = """
DateTime Operator Help

Available datetime operations:
• get_unix_time(timestamp) - Convert timestamp to Unix time or get current Unix time
• get_week_number(date) - Get week number for a date (format: YYYY-MM-DD)
• check_leap_year(year) - Check if a year is a leap year
• validate_date(date) - Check if a date is valid (format: YYYY-MM-DD)
• get_weekday(date) - Get weekday for a date (format: YYYY-MM-DD)
• calculate_progress(start_date, end_date) - Calculate progress between two dates
• countdown_to_date(target_date) - Calculate countdown to a specific date
• calculate_age(birth_date) - Calculate age from birth date
• get_co2_level(year) - Get CO2 level for a given year (1959-present)
• get_german_holidays(year, region) - Get German public holidays

Date format: Use YYYY-MM-DD format for dates (e.g., "2022-01-01")
Time format: Various timestamp formats supported for Unix time conversion

Examples:
• "What week is January 1st, 2022?" -> get_week_number("2022-01-01")
• "Is 2020 a leap year?" -> check_leap_year("2020")
• "How many days until Christmas?" -> countdown_to_date("2024-12-25")
• "What's my age if I was born in 1990?" -> calculate_age("1990-01-01")
    """

    return help_text.strip()
