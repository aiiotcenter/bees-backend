# import Adafruit_DHT
# import time

# # Sensor type - change this based on your sensor
# SENSOR_TYPE = Adafruit_DHT.DHT11  # or Adafruit_DHT.DHT22
# DHT_PIN = 23

# # Global variables to store last valid readings
# last_temperature = 27.0
# last_humidity = 48.0

# def get_temp_humidity():
#     global last_temperature, last_humidity
    
#     try:
#         humidity, temperature = Adafruit_DHT.read_retry(SENSOR_TYPE, DHT_PIN)
        
#         if humidity is not None and temperature is not None:
#             last_temperature = round(temperature, 1)
#             last_humidity = round(humidity, 1)
#             return last_temperature, last_humidity
#         else:
#             print(f"⚠️ DHT sensor returned None values, using previous: T={last_temperature}°C, H={last_humidity}%")
#             return last_temperature, last_humidity
            
#     except Exception as e:
#         print(f"⚠️ Error reading DHT sensor: {e}. Using previous values: T={last_temperature}°C, H={last_humidity}%")
#         return last_temperature, last_humidity

import Adafruit_DHT
import time
from sensors.google_weather import get_weather_from_google

# Sensor configuration
SENSOR_TYPE = Adafruit_DHT.DHT11  # or Adafruit_DHT.DHT22
DHT_PIN = 23

# Last known values (used as fallback)
last_temperature = 27.0
last_humidity = 48.0

def get_temp_humidity():
    """
    Get temperature and humidity.
    1️⃣ Try to read from DHT sensor.
    2️⃣ If DHT fails, try Google Weather API.
    3️⃣ If both fail, return last known values.
    """
    global last_temperature, last_humidity

    try:
        humidity, temperature = Adafruit_DHT.read_retry(SENSOR_TYPE, DHT_PIN)

        # ✅ Case 1: Sensor works
        if humidity is not None and temperature is not None:
            last_temperature = round(temperature, 1)
            last_humidity = round(humidity, 1)
            return last_temperature, last_humidity

        # ⚠️ Case 2: Sensor failed — use Google API fallback
        print("⚠️ DHT sensor failed. Trying Google Weather API fallback...")

        # !!!!!!!For now, hardcode coordinates
        # DYNAMIC Version
        # from smart_location import get_smart_location
        # lat, lon, _ = get_smart_location(verbose=False)
        lat, lon = 35.1856, 33.3823

        temp, hum = get_weather_from_google(lat, lon)

        if temp is not None:
            # Optional calibration for hive interior environment
            temp = round(temp + 2.5, 1)  # inside hive ~2.5°C warmer
            hum = min(100, (hum or last_humidity) + 10)  # ~10% more humid

            last_temperature = temp
            last_humidity = hum
            print(f"🌡️ Using Google Weather fallback → T={temp}°C, H={hum}%")
            return last_temperature, last_humidity

        # ❌ Case 3: Weather API also failed
        print(f"⚠️ Weather API unavailable. Using cached values: "
              f"T={last_temperature}°C, H={last_humidity}%")
        return last_temperature, last_humidity

    except Exception as e:
        print(f"⚠️ DHT sensor exception: {e}. Using previous cached values.")
        return last_temperature, last_humidity
