import requests

def get_weather_from_google(lat: float, lon: float):
    """
    Getting temperature & humidity fallback using Open-Meteo API.

    """
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,relative_humidity_2m"
        )
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            print(f"⚠️ Weather API error: {response.status_code} {response.text}")
            return None, None

        data = response.json()
        current = data.get("current", {})
        temp_c = current.get("temperature_2m")
        humidity = current.get("relative_humidity_2m")

        if temp_c is None:
            print("⚠️ No temperature data in Weather API response")
            return None, None

        temp_c = round(float(temp_c), 1)
        humidity = round(float(humidity), 1) if humidity is not None else estimate_humidity(temp_c)

        print(f"🌤️ Fallback Weather → T={temp_c}°C, H={humidity}%")
        return temp_c, humidity

    except Exception as e:
        print(f"⚠️ Weather API exception: {e}")
        return None, None


def estimate_humidity(temp_c):
    """Estimate humidity if none provided."""
    base = max(20, 90 - abs(temp_c - 25) * 3)
    return round(min(95, max(20, base)), 1)
