import requests
import math

GOOGLE_API_KEY = "AIzaSyAoMkVZUAMc91JvW_UclM4sSEzJBkW8dgY"

def get_weather_from_google(lat: float, lon: float):
    """
    Query Google Maps Platform Weather API for the given coordinates.
    Returns (temperature_c, humidity_percent) or (None, None) if failed.
    """
    try:
        url = (
            f"https://maps.googleapis.com/maps/api/weather/json?"
            f"location={lat},{lon}&key={GOOGLE_API_KEY}"
        )
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            print(f"⚠️ Google Weather API error: {response.status_code} {response.text}")
            return None, None

        data = response.json()
        current = data.get("currentConditions", {})
        temp_k = current.get("temperature")
        humidity = current.get("humidity")

        if temp_k is None:
            print("⚠️ No temperature data in Weather API response")
            return None, None

        temp_c = round(temp_k - 273.15, 1)

        # Estimate humidity if missing
        if humidity is None:
            humidity = estimate_humidity(temp_c)

        print(f"🌤️ Google Weather → T={temp_c}°C, H={humidity}%")
        return temp_c, humidity

    except Exception as e:
        print(f"⚠️ Weather API exception: {e}")
        return None, None


def estimate_humidity(temp_c):
    """
    Estimate humidity if Google does not return it.
    """
    base = max(20, 90 - abs(temp_c - 25) * 3)
    return round(min(95, max(20, base)), 1)
