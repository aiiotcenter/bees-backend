import Adafruit_DHT

DHT_PIN = 23
DHT_SENSOR = Adafruit_DHT.DHT11

def get_temp_humidity():
    try:
        humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
        if humidity is not None and temperature is not None:
            return round(temperature, 1), round(humidity, 1)
        else:
            return 27, 48
    except Exception as e:
        print(f"⚠️ Error reading DHT sensor: {e}")
        return 29, 50