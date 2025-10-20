import requests

GOOGLE_API_KEY = "AIzaSyAoMkVZUAMc91JvW_UclM4sSEzJBkW8dgY"

def get_weather_from_google(lat: float, lon: float):
    """
    Query Google Maps Platform Weather API for current weather data.
    Returns (temperature_c, humidity_percent) or (None, None) if fails.
    """
    try:
        url = (
            f"https://weather.googleapis.com/v1/currentConditions"
            f"?location={lat},{lon}&key={GOOGLE_API_KEY}"
        )
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            print(f"⚠️ Google Weather API error: {response.status_code} {response.text}")
            return None, None

        data = response.json()
        
        current = data.get("currentConditions", {})

        temp_c = current.get("temperature")
        humidity = current.get("humidity")

        if temp_c is None:
            print("⚠️ No temperature data in Weather API response")
            return None, None

        # Rounding
        temp_c = round(float(temp_c), 1)
        humidity = round(float(humidity), 1) if humidity is not None else estimate_humidity(temp_c)

        print(f"🌤️ Google Weather → T={temp_c}°C, H={humidity}%")
        return temp_c, humidity

    except Exception as e:
        print(f"⚠️ Weather API exception: {e}")
        return None, None


def estimate_humidity(temp_c):
    """Estimate humidity if Google doesn’t return it."""
    base = max(20, 90 - abs(temp_c - 25) * 3)
    return round(min(95, max(20, base)), 1)
