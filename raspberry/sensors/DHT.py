import time
import board
import adafruit_dht

# Sensor type - DHT11 or DHT22
DHT_PIN = board.D23

sensor = adafruit_dht.DHT11(DHT_PIN)

# Global variables to store last valid readings
last_temperature = 27.0
last_humidity = 48.0

def get_temp_humidity():
    global last_temperature, last_humidity

    try:
        temperature = sensor.temperature
        humidity = sensor.humidity

        if humidity is not None and temperature is not None:
            last_temperature = round(temperature, 1)
            last_humidity = round(humidity, 1)
            return last_temperature, last_humidity
        else:
            print(f"⚠️ DHT sensor returned None, using previous: T={last_temperature}°C, H={last_humidity}%")
            return last_temperature, last_humidity

    except Exception as e:
        print(f"⚠️ Error reading DHT sensor: {e}. Using previous values: T={last_temperature}°C, H={last_humidity}%")
        return last_temperature, last_humidity