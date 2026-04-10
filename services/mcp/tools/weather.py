import os
import httpx

async def get_weather(location: str) -> str:
    """Get the current weather for a location.
    Args:
        location: City name or coordinates (e.g. 'Bengaluru', 'New York')
    Returns:
        Current weather conditions and temperature
    """
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return "Error: OPENWEATHER_API_KEY is not set."
        
    url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={api_key}&units=metric"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            if response.status_code == 404:
                return f"Weather for '{location}' not found."
            response.raise_for_status()
            
            data = response.json()
            
            desc = data['weather'][0]['description'].capitalize()
            temp = data['main']['temp']
            feels_like = data['main']['feels_like']
            humidity = data['main']['humidity']
            city = data['name']
            
            return f"Weather in {city}: {desc}, {temp}°C (feels like {feels_like}°C), Humidity: {humidity}%"
    except Exception as e:
         return f"Error fetching weather: {e}"
