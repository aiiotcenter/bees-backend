import requests
import time
import RPi.GPIO as GPIO
import Adafruit_DHT
from hx711 import HX711
# from gps_module import get_gps_location, send_location_to_api

# API Endpoint
API_URL = "http://bees-backend.aiiot.center/api/records" 

# GPIO Pin Configuration
TRIG = 8
ECHO = 7
DHT_PIN = 23
DHT_SENSOR = Adafruit_DHT.DHT11
SOUND_SENSOR_PIN = 2

# === HX711 Calibration ===
# Set to 1 for calibration mode (then adjust after)
REFERENCE_UNIT = 1  # Change this after calibration (e.g., 158)

# Setup GPIO
def setup_gpio():
    print("🔧 Setting up GPIO pins...")
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(TRIG, GPIO.OUT)
    GPIO.setup(ECHO, GPIO.IN)
    GPIO.setup(SOUND_SENSOR_PIN, GPIO.IN)

def cleanup_gpio():
    print("🧹 Cleaning up GPIO pins...")
    GPIO.cleanup()

# Distance Sensor
def get_distance():
    try:
        GPIO.output(TRIG, True)
        time.sleep(0.00001)
        GPIO.output(TRIG, False)

        start_time = time.time()
        while GPIO.input(ECHO) == 0:
            start_time = time.time()
        while GPIO.input(ECHO) == 1:
            end_time = time.time()

        elapsed_time = end_time - start_time
        distance = (elapsed_time * 34300) / 2
        print(f"📏 Distance: {distance:.2f} cm")
        return distance
    except Exception as e:
        print(f"❌ Error reading distance: {e}")
        return 0

# DHT Sensor
def get_temp_humidity():
    try:
        print("🌡️ Reading temperature and humidity...")
        humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
        print(f"📊 Raw DHT: Humidity={humidity}, Temp={temperature}")
        if humidity is not None and temperature is not None:
            return round(temperature, 1), round(humidity, 1)
        return 0, 0
    except Exception as e:
        print(f"❌ Error reading DHT: {e}")
        return 0, 0

# Sound Sensor
def monitor_sound():
    try:
        sound_detected = GPIO.input(SOUND_SENSOR_PIN) == GPIO.HIGH
        print(f"🎵 Sound detected: {'Yes' if sound_detected else 'No'}")
        return sound_detected
    except Exception as e:
        print(f"❌ Error reading sound sensor: {e}")
        return False

# HX711 Setup
def initialize_hx711():
    print("⚖️ Initializing HX711...")
    try:
        hx = HX711(5, 6)
        hx.set_reading_format("MSB", "MSB")
        hx.set_reference_unit(REFERENCE_UNIT)
        hx.reset()
        hx.tare()
        print("✅ HX711 Ready.")
        return hx
    except Exception as e:
        print(f"❌ HX711 init error: {e}")
        return None

def get_weight(hx):
    try:
        weight = round(hx.get_weight(5), 2)  # 5 samples, rounded to 2 decimals
        print(f"⚖️ Weight: {weight} grams")
        hx.power_down()
        time.sleep(0.1)
        hx.power_up()
        return weight
    except Exception as e:
        print(f"❌ Error reading HX711: {e}")
        return 0

# Send Data to API
def send_data_to_api(data):
    try:
        print(f"📤 Sending to API: {data}")
        response = requests.post(API_URL, data=data)
        print(f"✅ API Response: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ API Error: {e}")

# Main Program
def main():
    setup_gpio()
    hx = initialize_hx711()

    if not hx:
        print("❌ HX711 failed. Exiting.")
        return

    try:
        while True:
            print("\n📡 Collecting data...")

            temperature, humidity = get_temp_humidity()
            weight = get_weight(hx)
            distance = get_distance()
            sound_detected = monitor_sound()

            data = {
                "hiveId": 1,
                "temperature": temperature,
                "humidity": humidity,
                "weight": weight,
                "distance": distance,
                "soundStatus": int(sound_detected),
                "isDoorOpen": 0,
                "numOfIn": 0,
                "numOfOut": 0,
            }

            print(f"📦 Data payload: {data}")
            send_data_to_api(data)

            # If using GPS:
            # latitude, longitude = get_gps_location()
            # send_location_to_api(latitude, longitude)

            time.sleep(5)

    except KeyboardInterrupt:
        print("🛑 Stopped by user.")
    except Exception as e:
        print(f"❌ Runtime error: {e}")
    finally:
        cleanup_gpio()

if __name__ == "__main__":
    main()
