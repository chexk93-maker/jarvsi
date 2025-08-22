import os
import requests
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def detect_city_by_ip() -> str:
    try:
        logger.info("Trying to detect city using IP address")
        ip_info = requests.get("https://ipapi.co/json/").json()
        city = ip_info.get("city")
        if city:
            logger.info(f"City detected using IP: {city}")
            return city
        else:
            logger.warning("Failed to detect city, using default 'Delhi'")
            return "Delhi"
    except Exception as e:
        logger.error(f"Error occurred while detecting city by IP: {e}")
        return "Delhi"

async def get_weather(city: str = "") -> str:
    """Get current weather information for a city including rain probability."""
    api_key = os.getenv("OPENWEATHER_API_KEY")

    if not api_key:
        logger.error("OpenWeather API key is missing.")
        return "OpenWeather API key not found in environment variables."

    if not city:
        city = detect_city_by_ip()

    logger.info(f"Fetching weather for city: {city}")
    
    # Get current weather
    current_url = "https://api.openweathermap.org/data/2.5/weather"
    current_params = {
        "q": city,
        "appid": api_key,
        "units": "metric"
    }

    # Get forecast for rain probability
    forecast_url = "https://api.openweathermap.org/data/2.5/forecast"
    forecast_params = {
        "q": city,
        "appid": api_key,
        "units": "metric"
    }

    try:
        # Get current weather
        current_response = requests.get(current_url, params=current_params)
        if current_response.status_code != 200:
            logger.error(f"Error from OpenWeather API: {current_response.status_code} - {current_response.text}")
            return f"Error: Unable to fetch weather for {city}. Please check the city name."

        current_data = current_response.json()
        weather = current_data["weather"][0]["description"].title()
        temperature = current_data["main"]["temp"]
        humidity = current_data["main"]["humidity"]
        wind_speed = current_data["wind"]["speed"]

        # Get forecast for rain probability
        forecast_response = requests.get(forecast_url, params=forecast_params)
        rain_probability = "N/A"
        
        if forecast_response.status_code == 200:
            forecast_data = forecast_response.json()
            if forecast_data.get("list") and len(forecast_data["list"]) > 0:
                # Get the next few hours forecast for rain probability
                next_forecasts = forecast_data["list"][:4]  # Next 12 hours (3-hour intervals)
                max_pop = 0
                
                for forecast in next_forecasts:
                    pop = forecast.get("pop", 0)  # Probability of precipitation
                    max_pop = max(max_pop, pop)
                
                if max_pop > 0:
                    rain_probability = f"{max_pop * 100:.0f}%"
                else:
                    rain_probability = "0%"

        result = (f"Weather in {city}:\n" 
                  f"- Condition: {weather}\n" 
                  f"- Temperature: {temperature}°C\n" 
                  f"- Humidity: {humidity}%\n" 
                  f"- Wind Speed: {wind_speed} m/s\n"
                  f"- Rain Probability: {rain_probability}")

        logger.info(f"Weather result: \n{result}")
        return result

    except Exception as e:
        logger.exception(f"Exception occurred while fetching weather: {e}")
        return "An error occurred while fetching the weather."

def get_tools():
    """Return tool definitions for Ollama"""
    return [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get current weather information for a city including temperature, humidity, wind speed, and rain probability. If no city is provided, uses IP-based location detection.",
                "example": "what's the weather like in London?",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "The city name to get weather for (optional)"
                        }
                    },
                    "required": []
                }
            }
        }
    ]

def get_handlers():
    """Return tool handlers"""
    return {
        "get_weather": get_weather
    }
