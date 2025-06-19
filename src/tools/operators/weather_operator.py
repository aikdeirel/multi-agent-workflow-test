import requests
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from langchain.tools import tool

logger = logging.getLogger(__name__)

# Open-Meteo API endpoints
FORECAST_API_URL = "https://api.open-meteo.com/v1/forecast"
GEOCODING_API_URL = "https://geocoding-api.open-meteo.com/v1/search"


def geocode_location(location: str) -> Optional[Dict[str, float]]:
    """
    Convert a location name to latitude and longitude coordinates.

    Args:
        location: City name, address, or location string

    Returns:
        Dictionary with 'latitude' and 'longitude' keys, or None if not found
    """
    try:
        params = {"name": location, "count": 1, "language": "en", "format": "json"}

        response = requests.get(GEOCODING_API_URL, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()

        if data.get("results") and len(data["results"]) > 0:
            result = data["results"][0]
            return {
                "latitude": result["latitude"],
                "longitude": result["longitude"],
                "name": result["name"],
                "country": result.get("country", ""),
                "admin1": result.get("admin1", ""),
            }

        return None

    except Exception as e:
        logger.error(f"Geocoding error for location '{location}': {str(e)}")
        return None


def format_weather_response(data: Dict[str, Any], location_info: Dict[str, Any]) -> str:
    """
    Format the weather data response into a readable string.

    Args:
        data: Weather data from Open-Meteo API
        location_info: Location information including coordinates and name

    Returns:
        Formatted weather information string
    """
    try:
        location_name = location_info.get("name", "Unknown Location")
        country = location_info.get("country", "")
        if country:
            location_name += f", {country}"

        response_parts = [f"Weather information for {location_name}:"]

        # Current weather
        if "current" in data:
            current = data["current"]
            current_time = current.get("time", "")
            response_parts.append(f"\nCurrent weather (as of {current_time}):")

            if "temperature_2m" in current:
                temp = current["temperature_2m"]
                response_parts.append(f"• Temperature: {temp}°C")

            if "relative_humidity_2m" in current:
                humidity = current["relative_humidity_2m"]
                response_parts.append(f"• Humidity: {humidity}%")

            if "wind_speed_10m" in current:
                wind_speed = current["wind_speed_10m"]
                response_parts.append(f"• Wind Speed: {wind_speed} km/h")

            if "wind_direction_10m" in current:
                wind_dir = current["wind_direction_10m"]
                response_parts.append(f"• Wind Direction: {wind_dir}°")

            if "precipitation" in current:
                precip = current["precipitation"]
                response_parts.append(f"• Precipitation: {precip} mm")

            if "weather_code" in current:
                weather_code = current["weather_code"]
                weather_desc = get_weather_description(weather_code)
                response_parts.append(f"• Conditions: {weather_desc}")

        # Daily forecast summary
        if "daily" in data:
            daily = data["daily"]
            response_parts.append(f"\nDaily forecast:")

            dates = daily.get("time", [])
            temp_max = daily.get("temperature_2m_max", [])
            temp_min = daily.get("temperature_2m_min", [])

            for i, date in enumerate(dates[:5]):  # Show next 5 days
                if i < len(temp_max) and i < len(temp_min):
                    response_parts.append(
                        f"• {date}: {temp_min[i]}°C to {temp_max[i]}°C"
                    )

        # Units information
        if "current_units" in data:
            units = data["current_units"]
            response_parts.append(
                f"\nUnits: Temperature in {units.get('temperature_2m', 'C')}, Wind in {units.get('wind_speed_10m', 'km/h')}"
            )

        return "\n".join(response_parts)

    except Exception as e:
        logger.error(f"Error formatting weather response: {str(e)}")
        return f"Error formatting weather data: {str(e)}"


def get_weather_description(weather_code: int) -> str:
    """
    Convert weather code to human-readable description.

    Args:
        weather_code: WMO weather code

    Returns:
        Human-readable weather description
    """
    weather_codes = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        56: "Light freezing drizzle",
        57: "Dense freezing drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        66: "Light freezing rain",
        67: "Heavy freezing rain",
        71: "Slight snow fall",
        73: "Moderate snow fall",
        75: "Heavy snow fall",
        77: "Snow grains",
        80: "Slight rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        85: "Slight snow showers",
        86: "Heavy snow showers",
        95: "Thunderstorm",
        96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail",
    }

    return weather_codes.get(
        weather_code, f"Unknown weather condition (code: {weather_code})"
    )


@tool
def get_current_weather(location: str, include_forecast: bool = False) -> str:
    """
    Get current weather information for a specified location.

    This tool fetches real-time weather data from Open-Meteo API including:
    - Current temperature, humidity, wind speed and direction
    - Weather conditions and precipitation
    - Optional daily forecast for the next few days

    The tool accepts either coordinates (latitude,longitude) or location names
    that will be automatically geocoded.

    Args:
        location: Location as city name (e.g., "London", "New York") or coordinates (e.g., "52.52,13.41")
        include_forecast: Whether to include daily forecast (default: False)

    Returns:
        String containing formatted current weather information

    Examples:
        - get_current_weather("London")
        - get_current_weather("40.7128,-74.0060")
        - get_current_weather("Tokyo", include_forecast=True)
    """
    logger.info(f"Getting current weather for location: {location}")

    try:
        # Parse location input
        if not location or not isinstance(location, str):
            return "Error: Please provide a valid location name or coordinates."

        # Handle case where LangChain passes JSON string instead of raw location
        import json

        actual_location = location
        if location.startswith('{"location":') or location.startswith("{'location'"):
            try:
                # Try to parse as JSON and extract the location
                data = json.loads(location.replace("'", '"'))
                if isinstance(data, dict) and "location" in data:
                    actual_location = data["location"]
                    logger.debug(f"Extracted location from JSON: {actual_location}")
            except (json.JSONDecodeError, KeyError):
                # If JSON parsing fails, use the original string
                actual_location = location

        actual_location = actual_location.strip()

        # Check if input is coordinates (lat,lon format)
        if "," in actual_location:
            try:
                lat_str, lon_str = actual_location.split(",", 1)
                latitude = float(lat_str.strip())
                longitude = float(lon_str.strip())
                location_info = {
                    "latitude": latitude,
                    "longitude": longitude,
                    "name": f"Coordinates ({latitude}, {longitude})",
                }
            except ValueError:
                return "Error: Invalid coordinate format. Use 'latitude,longitude' (e.g., '52.52,13.41')"
        else:
            # Geocode location name
            location_info = geocode_location(actual_location)
            if not location_info:
                return f"Error: Could not find coordinates for location '{actual_location}'. Please check the spelling or try a different location."

        # Prepare API parameters
        params = {
            "latitude": location_info["latitude"],
            "longitude": location_info["longitude"],
            "current": [
                "temperature_2m",
                "relative_humidity_2m",
                "precipitation",
                "weather_code",
                "wind_speed_10m",
                "wind_direction_10m",
            ],
            "timezone": "auto",
        }

        # Add daily forecast if requested
        if include_forecast:
            params["daily"] = [
                "temperature_2m_max",
                "temperature_2m_min",
                "weather_code",
                "precipitation_sum",
            ]
            params["forecast_days"] = 7

        # Make API request
        response = requests.get(FORECAST_API_URL, params=params, timeout=15)
        response.raise_for_status()

        weather_data = response.json()

        # Format and return response
        formatted_response = format_weather_response(weather_data, location_info)
        logger.info(
            f"Successfully retrieved weather for {location_info.get('name', actual_location)}"
        )

        return formatted_response

    except requests.exceptions.RequestException as e:
        error_msg = f"Error fetching weather data: Network error - {str(e)}"
        logger.error(f"Network error for location {location}: {str(e)}")
        return error_msg
    except Exception as e:
        error_msg = (
            f"Error: An unexpected error occurred while fetching weather data. {str(e)}"
        )
        logger.error(f"Unexpected error for location {location}: {str(e)}")
        return error_msg


@tool
def get_weather_forecast(location: str, days: int = 7) -> str:
    """
    Get detailed weather forecast for a specified location.

    This tool provides multi-day weather forecasts including:
    - Daily temperature highs and lows
    - Weather conditions for each day
    - Precipitation forecasts
    - Wind information

    Args:
        location: Location as city name or coordinates (lat,lon)
        days: Number of forecast days (1-16, default: 7)

    Returns:
        String containing formatted weather forecast

    Examples:
        - get_weather_forecast("Paris")
        - get_weather_forecast("Sydney", days=5)
        - get_weather_forecast("37.7749,-122.4194", days=10)
    """
    logger.info(f"Getting weather forecast for location: {location}, days: {days}")

    try:
        # Validate days parameter
        if not isinstance(days, int) or days < 1 or days > 16:
            return "Error: Number of days must be between 1 and 16.\n"

        # Parse location input
        if not location or not isinstance(location, str):
            return "Error: Please provide a valid location name or coordinates.\n"

        # Handle case where LangChain passes JSON string instead of raw location
        import json

        actual_location = location
        if location.startswith('{"location":') or location.startswith("{'location'"):
            try:
                # Try to parse as JSON and extract the location
                data = json.loads(location.replace("'", '"'))
                if isinstance(data, dict) and "location" in data:
                    actual_location = data["location"]
                    logger.debug(f"Extracted location from JSON: {actual_location}")
            except (json.JSONDecodeError, KeyError):
                # If JSON parsing fails, use the original string
                actual_location = location

        actual_location = actual_location.strip()

        # Check if input is coordinates (lat,lon format)
        if "," in actual_location:
            try:
                lat_str, lon_str = actual_location.split(",", 1)
                latitude = float(lat_str.strip())
                longitude = float(lon_str.strip())
                location_info = {
                    "latitude": latitude,
                    "longitude": longitude,
                    "name": f"Coordinates ({latitude}, {longitude})",
                }
            except ValueError:
                return "Error: Invalid coordinate format. Use 'latitude,longitude' (e.g., '52.52,13.41')\n"
        else:
            # Geocode location name
            location_info = geocode_location(actual_location)
            if not location_info:
                return f"Error: Could not find coordinates for location '{actual_location}'. Please check the spelling or try a different location.\n"

        # Prepare API parameters
        params = {
            "latitude": location_info["latitude"],
            "longitude": location_info["longitude"],
            "daily": [
                "temperature_2m_max",
                "temperature_2m_min",
                "weather_code",
                "precipitation_sum",
                "wind_speed_10m_max",
                "wind_direction_10m_dominant",
            ],
            "timezone": "auto",
            "forecast_days": days,
        }

        # Make API request
        response = requests.get(FORECAST_API_URL, params=params, timeout=15)
        response.raise_for_status()

        weather_data = response.json()

        # Format detailed forecast response
        location_name = location_info.get("name", "Unknown Location")
        country = location_info.get("country", "")
        if country:
            location_name += f", {country}"

        response_parts = [f"Weather forecast for {location_name} ({days} days):"]

        if "daily" in weather_data:
            daily = weather_data["daily"]
            dates = daily.get("time", [])
            temp_max = daily.get("temperature_2m_max", [])
            temp_min = daily.get("temperature_2m_min", [])
            weather_codes = daily.get("weather_code", [])
            precipitation = daily.get("precipitation_sum", [])
            wind_speed = daily.get("wind_speed_10m_max", [])

            for i, date in enumerate(dates):
                if i < len(temp_max) and i < len(temp_min):
                    # Parse date for better formatting
                    try:
                        date_obj = datetime.fromisoformat(date)
                        formatted_date = date_obj.strftime("%A, %B %d")
                    except:
                        formatted_date = date

                    day_info = [f"\n{formatted_date}:"]
                    day_info.append(
                        f"  • Temperature: {temp_min[i]}°C to {temp_max[i]}°C"
                    )

                    if i < len(weather_codes):
                        conditions = get_weather_description(weather_codes[i])
                        day_info.append(f"  • Conditions: {conditions}")

                    if i < len(precipitation):
                        day_info.append(f"  • Precipitation: {precipitation[i]} mm")

                    if i < len(wind_speed):
                        day_info.append(f"  • Max Wind Speed: {wind_speed[i]} km/h")

                    response_parts.extend(day_info)

        formatted_response = "\n".join(response_parts)
        logger.info(
            f"Successfully retrieved forecast for {location_info.get('name', actual_location)}"
        )

        return formatted_response + "\n"

    except requests.exceptions.RequestException as e:
        error_msg = f"Error fetching weather forecast: Network error - {str(e)}"
        logger.error(f"Network error for location {location}: {str(e)}")
        return error_msg + "\n"
    except Exception as e:
        error_msg = f"Error: An unexpected error occurred while fetching weather forecast. {str(e)}"
        logger.error(f"Unexpected error for location {location}: {str(e)}")
        return error_msg + "\n"


@tool
def weather_help() -> str:
    """
    Get help and information about weather tools and capabilities.

    This tool provides guidance on:
    - Available weather functions
    - Supported location formats
    - Weather data types
    - Usage examples

    Returns:
        String containing comprehensive help information about weather capabilities
    """
    help_text = """Weather Tools Help

AVAILABLE WEATHER FUNCTIONS:
• get_current_weather(location, include_forecast=False) - Current weather conditions
• get_weather_forecast(location, days=7) - Multi-day weather forecast
• weather_help() - This help information

LOCATION FORMATS SUPPORTED:
• City names: "London", "New York", "Tokyo"
• City with country: "Paris, France", "Sydney, Australia"  
• Coordinates: "52.52,13.41" (latitude,longitude)
• Addresses: "Times Square, New York"

CURRENT WEATHER DATA INCLUDES:
• Temperature (°C)
• Humidity (%)
• Wind speed and direction
• Precipitation (mm)
• Weather conditions
• Optional daily forecast

FORECAST DATA INCLUDES:
• Daily temperature highs and lows
• Weather conditions for each day
• Precipitation forecasts
• Maximum wind speeds
• Up to 16 days forecast

EXAMPLES:
• Current weather: get_current_weather("London")
• With forecast: get_current_weather("Tokyo", include_forecast=True)
• Multi-day forecast: get_weather_forecast("Paris", days=5)
• Using coordinates: get_current_weather("40.7128,-74.0060")

DATA SOURCE:
• Powered by Open-Meteo API (open-source weather service)
• No API key required
• High-resolution weather models (1-11 km)
• Updated hourly with latest conditions
• Global coverage with accurate forecasts

ERROR HANDLING:
• Automatic location geocoding
• Network timeout protection
• Invalid input validation
• Detailed error messages

Ask me for weather information for any location worldwide!"""

    return help_text + "\n"
