import httpx


async def get_weather(city: str) -> dict:
    """Get current weather for a city using Open-Meteo API.

    Args:
        city: City name (e.g. "London", "New York")
    """
    async with httpx.AsyncClient() as client:
        # Geocode city name to coordinates
        geo_resp = await client.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1},
            timeout=10,
        )
        geo_resp.raise_for_status()
        geo_data = geo_resp.json()

        if not geo_data.get("results"):
            return {"error": f"City '{city}' not found"}

        location = geo_data["results"][0]
        latitude = location["latitude"]
        longitude = location["longitude"]

        # Fetch current weather
        weather_resp = await client.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m",
            },
            timeout=10,
        )
        weather_resp.raise_for_status()
        weather_data = weather_resp.json()

    current = weather_data["current"]
    return {
        "city": location["name"],
        "country": location.get("country", ""),
        "temperature_c": current["temperature_2m"],
        "feels_like_c": current["apparent_temperature"],
        "humidity": current["relative_humidity_2m"],
        "weather_code": current["weather_code"],
        "wind_speed_kmh": current["wind_speed_10m"],
    }
