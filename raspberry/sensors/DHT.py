import Adafruit_DHT
import time

SENSOR_TYPE = Adafruit_DHT.DHT11
DHT_PIN = 23

last_temperature = 27.0
last_humidity = 48.0

def get_temp_humidity():
    global last_temperature, last_humidity

    try:
        humidity, temperature = Adafruit_DHT.read_retry(SENSOR_TYPE, DHT_PIN)

        if humidity is not None and temperature is not None:
            last_temperature = round(temperature, 1)
            last_humidity = round(humidity, 1)
            return last_temperature, last_humidity
        else:
            print(f"⚠️ DHT sensor returned None, using previous: T={last_temperature}°C, H={last_humidity}%")
            return last_temperature, last_humidity

    except Exception as e:
        print(f"⚠️ Error reading DHT sensor: {e}. Using previous: T={last_temperature}°C, H={last_humidity}%")
        return last_temperature, last_humidity