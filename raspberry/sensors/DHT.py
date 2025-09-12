# import Adafruit_DHT

# DHT_PIN = 23
# DHT_SENSOR = Adafruit_DHT.DHT11

# def get_temp_humidity():
#     try:
#         humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
#         if humidity is not None and temperature is not None:
#             return round(temperature, 1), round(humidity, 1)
#         else:
#             return 27, 48
#     except Exception as e:
#         print(f"⚠️ Error reading DHT sensor: {e}")
#         return 29, 50

# import adafruit_dht
# import board
# import time

# DHT_SENSOR = adafruit_dht.DHT11(board.D23)  # GPIO 23

# def get_temp_humidity():
#     try:
#         temperature = DHT_SENSOR.temperature
#         humidity = DHT_SENSOR.humidity
#         if humidity is not None and temperature is not None:
#             return round(temperature, 1), round(humidity, 1)
#         else:
#             return 27, 48
#     except Exception as e:
#         print(f"⚠️ Error reading DHT sensor: {e}")
#         return 29, 50

import adafruit_dht
import board
import time

DHT_SENSOR = adafruit_dht.DHT11(board.D23)  # GPIO 23

# Global variables to store last valid readings
last_temperature = 27.0  # Default fallback
last_humidity = 48.0     # Default fallback

def get_temp_humidity():
    global last_temperature, last_humidity
    
    try:
        temperature = DHT_SENSOR.temperature
        humidity = DHT_SENSOR.humidity
        
        if humidity is not None and temperature is not None:
            # Update last valid readings
            last_temperature = round(temperature, 1)
            last_humidity = round(humidity, 1)
            return last_temperature, last_humidity
        else:
            print(f"⚠️ DHT sensor returned None values, using previous: T={last_temperature}°C, H={last_humidity}%")
            return last_temperature, last_humidity
            
    except Exception as e:
        print(f"⚠️ Error reading DHT sensor: {e}. Using previous values: T={last_temperature}°C, H={last_humidity}%")
        return last_temperature, last_humidity
