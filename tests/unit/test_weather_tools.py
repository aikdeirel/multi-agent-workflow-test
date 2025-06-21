"""
Unit tests for the weather tools module.

Tests weather API interactions, data formatting, geocoding, and error handling.
"""

import pytest
import json
from unittest.mock import patch, Mock
import requests

from tools.operators.weather_operator import (
    geocode_location,
    format_weather_response,
    get_weather_description,
    get_current_weather,
    get_weather_forecast,
    weather_help
)


class TestGeocodeLocation:
    """Test the geocode_location function."""
    
    @pytest.mark.unit
    def test_geocode_success(self, mock_weather_api):
        """Test successful location geocoding."""
        result = geocode_location("Berlin")
        
        assert result is not None
        assert result["latitude"] == 52.52
        assert result["longitude"] == 13.41
        assert result["name"] == "Berlin"
        assert result["country"] == "Germany"
    
    @pytest.mark.unit
    def test_geocode_with_country(self, mock_weather_api):
        """Test geocoding with country specification."""
        result = geocode_location("London, UK")
        
        assert result is not None
        assert "name" in result
        assert "latitude" in result
        assert "longitude" in result
    
    @pytest.mark.unit
    def test_geocode_not_found(self):
        """Test geocoding with location not found."""
        def mock_get(url, params=None, timeout=None):
            response = Mock()
            response.raise_for_status.return_value = None
            response.json.return_value = {"results": []}
            return response
        
        with patch('requests.get', side_effect=mock_get):
            result = geocode_location("NonexistentCity12345")
            
            assert result is None
    
    @pytest.mark.unit
    def test_geocode_empty_results(self):
        """Test geocoding with empty results."""
        def mock_get(url, params=None, timeout=None):
            response = Mock()
            response.raise_for_status.return_value = None
            response.json.return_value = {}
            return response
        
        with patch('requests.get', side_effect=mock_get):
            result = geocode_location("EmptyResult")
            
            assert result is None
    
    @pytest.mark.unit
    def test_geocode_network_error(self):
        """Test geocoding with network error."""
        with patch('requests.get', side_effect=requests.exceptions.RequestException("Network error")):
            result = geocode_location("Berlin")
            
            assert result is None
    
    @pytest.mark.unit
    def test_geocode_timeout(self):
        """Test geocoding with timeout error."""
        with patch('requests.get', side_effect=requests.exceptions.Timeout("Timeout")):
            result = geocode_location("Berlin")
            
            assert result is None
    
    @pytest.mark.unit
    def test_geocode_invalid_json_response(self):
        """Test geocoding with invalid JSON response."""
        def mock_get(url, params=None, timeout=None):
            response = Mock()
            response.raise_for_status.return_value = None
            response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
            return response
        
        with patch('requests.get', side_effect=mock_get):
            result = geocode_location("Berlin")
            
            assert result is None
    
    @pytest.mark.unit
    def test_geocode_empty_location(self):
        """Test geocoding with empty location string."""
        result = geocode_location("")
        
        # Should handle gracefully and return None or raise appropriate error
        assert result is None
    
    @pytest.mark.unit
    def test_geocode_parameters(self, mock_weather_api):
        """Test that geocoding sends correct parameters."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {
                'results': [{
                    'latitude': 52.52,
                    'longitude': 13.41,
                    'name': 'Berlin',
                    'country': 'Germany'
                }]
            }
            mock_get.return_value = mock_response
            
            geocode_location("Berlin")
            
            # Check that correct parameters were sent
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert call_args[1]['params']['name'] == "Berlin"
            assert call_args[1]['params']['count'] == 1
            assert call_args[1]['timeout'] == 10


class TestFormatWeatherResponse:
    """Test the format_weather_response function."""
    
    @pytest.mark.unit
    def test_format_current_weather_complete(self, sample_weather_data, sample_location_info):
        """Test formatting complete current weather data."""
        result = format_weather_response(sample_weather_data, sample_location_info)
        
        assert "Weather information for Berlin, Germany:" in result
        assert "15.5°C" in result
        assert "65%" in result  # humidity
        assert "10.2 km/h" in result  # wind speed
        assert "180°" in result  # wind direction
    
    @pytest.mark.unit
    def test_format_weather_with_daily_forecast(self, sample_location_info):
        """Test formatting weather with daily forecast."""
        weather_data = {
            'current': {
                'time': '2024-01-01T12:00:00Z',
                'temperature_2m': 15.5,
                'weather_code': 1
            },
            'daily': {
                'time': ['2024-01-01', '2024-01-02', '2024-01-03'],
                'temperature_2m_max': [18.0, 20.0, 17.0],
                'temperature_2m_min': [10.0, 12.0, 11.0]
            }
        }
        
        result = format_weather_response(weather_data, sample_location_info)
        
        assert "Daily forecast:" in result
        assert "2024-01-01: 10.0°C to 18.0°C" in result
        assert "2024-01-02: 12.0°C to 20.0°C" in result
    
    @pytest.mark.unit
    def test_format_weather_minimal_data(self, sample_location_info):
        """Test formatting with minimal weather data."""
        minimal_data = {
            'current': {
                'temperature_2m': 20.0
            }
        }
        
        result = format_weather_response(minimal_data, sample_location_info)
        
        assert "Weather information for Berlin, Germany:" in result
        assert "20.0°C" in result
    
    @pytest.mark.unit
    def test_format_weather_no_country(self):
        """Test formatting with location info without country."""
        location_info = {
            'name': 'Unknown City',
            'latitude': 0.0,
            'longitude': 0.0
        }
        weather_data = {
            'current': {
                'temperature_2m': 25.0
            }
        }
        
        result = format_weather_response(weather_data, location_info)
        
        assert "Weather information for Unknown City:" in result
        assert "25.0°C" in result
    
    @pytest.mark.unit
    def test_format_weather_error_handling(self, sample_location_info):
        """Test formatting with malformed weather data."""
        malformed_data = {
            'current': {
                'temperature_2m': 'invalid_temp',  # Invalid temperature
                'weather_code': 'invalid_code'  # Invalid weather code
            }
        }
        
        result = format_weather_response(malformed_data, sample_location_info)
        
        # Should handle errors gracefully
        assert isinstance(result, str)
        assert len(result) > 0


class TestGetWeatherDescription:
    """Test the get_weather_description function."""
    
    @pytest.mark.unit
    @pytest.mark.parametrize("code,expected", [
        (0, "Clear sky"),
        (1, "Mainly clear"),
        (2, "Partly cloudy"),
        (3, "Overcast"),
        (45, "Fog"),
        (61, "Slight rain"),
        (71, "Slight snow fall"),
        (95, "Thunderstorm"),
        (99, "Thunderstorm with heavy hail")
    ])
    def test_valid_weather_codes(self, code, expected):
        """Test valid weather code descriptions."""
        result = get_weather_description(code)
        assert result == expected
    
    @pytest.mark.unit
    def test_invalid_weather_code(self):
        """Test invalid weather code handling."""
        result = get_weather_description(9999)
        
        assert "Unknown weather condition" in result
        assert "9999" in result
    
    @pytest.mark.unit
    def test_negative_weather_code(self):
        """Test negative weather code handling."""
        result = get_weather_description(-1)
        
        assert "Unknown weather condition" in result
        assert "-1" in result


class TestGetCurrentWeather:
    """Test the get_current_weather tool function."""
    
    @pytest.mark.unit
    def test_get_current_weather_city_name(self, mock_weather_api):
        """Test getting current weather by city name."""
        result = get_current_weather("Berlin")
        
        assert isinstance(result, str)
        assert "Berlin" in result
        assert "Temperature:" in result
        assert "°C" in result
    
    @pytest.mark.unit
    def test_get_current_weather_coordinates(self, mock_weather_api):
        """Test getting current weather by coordinates."""
        result = get_current_weather("52.52,13.41")
        
        assert isinstance(result, str)
        assert "Coordinates" in result
        assert "Temperature:" in result
    
    @pytest.mark.unit
    def test_get_current_weather_with_forecast(self, mock_weather_api):
        """Test getting current weather with forecast included."""
        result = get_current_weather("Berlin", include_forecast=True)
        
        assert isinstance(result, str)
        assert "Daily forecast:" in result or "forecast" in result.lower()
    
    @pytest.mark.unit
    def test_get_current_weather_invalid_coordinates(self, mock_weather_api):
        """Test getting weather with invalid coordinate format."""
        result = get_current_weather("invalid,coords")
        
        assert "Error:" in result
        assert "Invalid coordinate format" in result
    
    @pytest.mark.unit
    def test_get_current_weather_location_not_found(self):
        """Test getting weather for location that cannot be geocoded."""
        def mock_get(url, params=None, timeout=None):
            response = Mock()
            response.raise_for_status.return_value = None
            if 'geocoding' in url:
                response.json.return_value = {"results": []}
            return response
        
        with patch('requests.get', side_effect=mock_get):
            result = get_current_weather("NonexistentCity12345")
            
            assert "Error:" in result
            assert "Could not find coordinates" in result
    
    @pytest.mark.unit
    def test_get_current_weather_network_error(self):
        """Test getting weather with network error."""
        with patch('requests.get', side_effect=requests.exceptions.RequestException("Network error")):
            result = get_current_weather("Berlin")
            
            assert "Error" in result
            assert "Network error" in result
    
    @pytest.mark.unit
    def test_get_current_weather_empty_location(self):
        """Test getting weather with empty location."""
        result = get_current_weather("")
        
        assert "Error:" in result
        assert "valid location" in result
    
    @pytest.mark.unit
    def test_get_current_weather_json_input(self, mock_weather_api):
        """Test getting weather with JSON string input (LangChain format)."""
        json_input = '{"location": "Berlin"}'
        result = get_current_weather(json_input)
        
        assert isinstance(result, str)
        assert "Berlin" in result
    
    @pytest.mark.unit
    def test_get_current_weather_malformed_json_input(self, mock_weather_api):
        """Test getting weather with malformed JSON input."""
        malformed_json = '{"location": "Berlin"'  # Missing closing brace
        result = get_current_weather(malformed_json)
        
        # Should treat as regular string location
        assert isinstance(result, str)


class TestGetWeatherForecast:
    """Test the get_weather_forecast tool function."""
    
    @pytest.mark.unit
    def test_get_weather_forecast_default_days(self, mock_weather_api):
        """Test getting weather forecast with default days."""
        result = get_weather_forecast("Berlin")
        
        assert isinstance(result, str)
        assert "Weather forecast for Berlin" in result
        assert "7 days" in result
    
    @pytest.mark.unit
    def test_get_weather_forecast_custom_days(self, mock_weather_api):
        """Test getting weather forecast with custom number of days."""
        result = get_weather_forecast("Berlin", days=5)
        
        assert isinstance(result, str)
        assert "5 days" in result
    
    @pytest.mark.unit
    def test_get_weather_forecast_coordinates(self, mock_weather_api):
        """Test getting forecast by coordinates."""
        result = get_weather_forecast("52.52,13.41", days=3)
        
        assert isinstance(result, str)
        assert "Coordinates" in result
        assert "3 days" in result
    
    @pytest.mark.unit
    def test_get_weather_forecast_invalid_days(self, mock_weather_api):
        """Test getting forecast with invalid number of days."""
        result = get_weather_forecast("Berlin", days=20)  # Too many days
        
        assert "Error:" in result
        assert "between 1 and 16" in result
    
    @pytest.mark.unit
    def test_get_weather_forecast_zero_days(self, mock_weather_api):
        """Test getting forecast with zero days."""
        result = get_weather_forecast("Berlin", days=0)
        
        assert "Error:" in result
        assert "between 1 and 16" in result
    
    @pytest.mark.unit
    def test_get_weather_forecast_negative_days(self, mock_weather_api):
        """Test getting forecast with negative days."""
        result = get_weather_forecast("Berlin", days=-1)
        
        assert "Error:" in result
        assert "between 1 and 16" in result
    
    @pytest.mark.unit
    def test_get_weather_forecast_non_integer_days(self, mock_weather_api):
        """Test getting forecast with non-integer days."""
        result = get_weather_forecast("Berlin", days="five")
        
        assert "Error:" in result
        assert "between 1 and 16" in result


class TestWeatherHelp:
    """Test the weather_help function."""
    
    @pytest.mark.unit
    def test_weather_help_content(self):
        """Test weather help returns comprehensive information."""
        result = weather_help()
        
        assert isinstance(result, str)
        assert len(result) > 100  # Should be substantial help text
        
        # Check for key sections
        assert "AVAILABLE WEATHER FUNCTIONS" in result
        assert "LOCATION FORMATS SUPPORTED" in result
        assert "CURRENT WEATHER DATA INCLUDES" in result
        assert "FORECAST DATA INCLUDES" in result
        assert "EXAMPLES" in result
        assert "DATA SOURCE" in result
    
    @pytest.mark.unit
    def test_weather_help_function_descriptions(self):
        """Test that help includes function descriptions."""
        result = weather_help()
        
        assert "get_current_weather" in result
        assert "get_weather_forecast" in result
        assert "weather_help" in result
    
    @pytest.mark.unit
    def test_weather_help_location_formats(self):
        """Test that help includes location format examples."""
        result = weather_help()
        
        assert "City names:" in result
        assert "Coordinates:" in result
        assert "latitude,longitude" in result
    
    @pytest.mark.unit
    def test_weather_help_examples(self):
        """Test that help includes usage examples."""
        result = weather_help()
        
        assert "get_current_weather(" in result
        assert "get_weather_forecast(" in result


class TestWeatherToolsIntegration:
    """Integration tests for weather tools."""
    
    @pytest.mark.integration
    def test_complete_weather_workflow(self, mock_weather_api):
        """Test complete weather workflow from geocoding to formatting."""
        # Test the full workflow
        location = "Berlin"
        
        # Get current weather
        current_result = get_current_weather(location)
        assert "Berlin" in current_result
        assert "Temperature:" in current_result
        
        # Get forecast
        forecast_result = get_weather_forecast(location, days=3)
        assert "Berlin" in forecast_result
        assert "3 days" in forecast_result
        
        # Get help
        help_result = weather_help()
        assert "AVAILABLE WEATHER FUNCTIONS" in help_result
    
    @pytest.mark.integration
    def test_weather_tools_error_handling(self):
        """Test error handling across weather tools."""
        # Test network error handling
        with patch('requests.get', side_effect=requests.exceptions.RequestException("Network error")):
            current_result = get_current_weather("Berlin")
            forecast_result = get_weather_forecast("Berlin")
            
            assert "Error" in current_result
            assert "Error" in forecast_result
            assert "Network error" in current_result
            assert "Network error" in forecast_result


class TestWeatherToolsParametrized:
    """Parametrized tests for weather tools."""
    
    @pytest.mark.unit
    @pytest.mark.parametrize("location", [
        "Berlin",
        "London, UK",
        "New York, USA",
        "Tokyo, Japan"
    ])
    def test_get_current_weather_various_locations(self, location, mock_weather_api):
        """Test current weather with various location formats."""
        result = get_current_weather(location)
        
        assert isinstance(result, str)
        assert "Temperature:" in result
        assert "°C" in result
    
    @pytest.mark.unit
    @pytest.mark.parametrize("coordinates", [
        "52.52,13.41",  # Berlin
        "51.5074,-0.1278",  # London
        "40.7128,-74.0060",  # New York
        "35.6762,139.6503"  # Tokyo
    ])
    def test_get_current_weather_coordinates(self, coordinates, mock_weather_api):
        """Test current weather with various coordinate formats."""
        result = get_current_weather(coordinates)
        
        assert isinstance(result, str)
        assert "Coordinates" in result
        assert "Temperature:" in result
    
    @pytest.mark.unit
    @pytest.mark.parametrize("days", [1, 3, 5, 7, 10, 16])
    def test_get_weather_forecast_valid_days(self, days, mock_weather_api):
        """Test weather forecast with various valid day counts."""
        result = get_weather_forecast("Berlin", days=days)
        
        assert isinstance(result, str)
        assert f"{days} days" in result
    
    @pytest.mark.unit
    @pytest.mark.parametrize("invalid_days", [-5, 0, 17, 100, "five", None])
    def test_get_weather_forecast_invalid_days(self, invalid_days, mock_weather_api):
        """Test weather forecast with various invalid day counts."""
        result = get_weather_forecast("Berlin", days=invalid_days)
        
        assert "Error:" in result
        assert "between 1 and 16" in result


class TestWeatherToolsEdgeCases:
    """Test edge cases and boundary conditions."""
    
    @pytest.mark.unit
    def test_weather_tools_with_very_long_location_name(self, mock_weather_api):
        """Test weather tools with very long location names."""
        long_location = "A" * 1000  # Very long location name
        
        # Should handle gracefully without crashing
        result = get_current_weather(long_location)
        assert isinstance(result, str)
    
    @pytest.mark.unit
    def test_weather_tools_with_special_characters(self, mock_weather_api):
        """Test weather tools with special characters in location."""
        special_location = "München"  # Contains special character
        
        result = get_current_weather(special_location)
        assert isinstance(result, str)
    
    @pytest.mark.unit
    def test_weather_forecast_boundary_days(self, mock_weather_api):
        """Test weather forecast with boundary day values."""
        # Test minimum valid days
        result_min = get_weather_forecast("Berlin", days=1)
        assert "1 days" in result_min
        
        # Test maximum valid days
        result_max = get_weather_forecast("Berlin", days=16)
        assert "16 days" in result_max