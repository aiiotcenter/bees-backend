import requests
import time
import RPi.GPIO as GPIO
import Adafruit_DHT
from hx711 import HX711
from gps_module import get_gps_location, send_location_to_api  # <-- Imported GPS functions

# API Endpoint for sensor data
API_URL = "http://bees-backend.aiiot.center/api/records"

# GPIO Pins
DHT_PIN = 23
DHT_SENSOR = Adafruit_DHT.DHT11
SOUND_SENSOR_PIN = 7
IR_SENSOR = 9  # Single IR sensor used for door detection

def setup_gpio():
    print("🔧 Setting up GPIO...")
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(SOUND_SENSOR_PIN, GPIO.IN)
    GPIO.setup(IR_SENSOR, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

def cleanup_gpio():
    print("🧼 Cleaning up GPIO...")
    GPIO.cleanup()

def get_temp_humidity():
    try:
        humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
        if humidity is not None and temperature is not None:
            return round(temperature, 1), round(humidity, 1)
        else:
            return 0, 0
    except Exception as e:
        print(f"⚠️ Error reading DHT sensor: {e}")
        return 0, 0

def monitor_sound():
    try:
        state = GPIO.input(SOUND_SENSOR_PIN)
        print(f"🎤 Sound Sensor: {'HIGH (Detected)' if state else 'LOW (No sound)'}")
        return state == GPIO.HIGH
    except Exception as e:
        print(f"⚠️ Error reading sound sensor: {e}")
        return False

def read_ir_door_status():
    try:
        state = GPIO.input(IR_SENSOR)
        print(f"🚪 IR Sensor: {'OPEN (HIGH)' if state else 'CLOSED (LOW)'}")
        return state == GPIO.HIGH
    except Exception as e:
        print(f"⚠️ Error reading IR sensor: {e}")
        return True  # Assume open if error

def initialize_hx711():
    try:
        hx = HX711(16, 20)
        hx.set_reading_format("MSB", "MSB")
        hx.set_reference_unit(114)
        hx.reset()
        hx.tare()
        print("⚖️ HX711 initialized")
        return hx
    except Exception as e:
        print(f"⚠️ Error initializing HX711: {e}")
        return None

def get_weight(hx):
    try:
        weight = hx.get_weight_mean(5)
        hx.power_down()
        time.sleep(0.1)
        hx.power_up()
        print(f"⚖️ Weight: {round(weight, 2)} g")
        return round(weight, 2)
    except Exception as e:
        print(f"⚠️ Error reading weight: {e}")
        return 0

def send_data_to_api(data):
    try:
        print(f"📤 Sending sensor data: {data}")
        response = requests.post(API_URL, data=data)
        print(f"✅ Sensor API Response: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"⚠️ Error sending sensor data: {e}")

def main():
    setup_gpio()
    # //hx = initialize_hx711()

    try:
        while True:
            temperature, humidity = get_temp_humidity()
            sound = monitor_sound()
            door_open = read_ir_door_status()
            # weight = get_weight(hx) if hx else 0

            # Get and send GPS location
            latitude, longitude = get_gps_location()
            if latitude is not None and longitude is not None and (latitude != 0.0 or longitude != 0.0):
                send_location_to_api(latitude, longitude)
            else:
                print("⏳ No GPS fix yet — will retry next cycle.")

            # Send sensor data
            sensor_data = {
                "hiveId": 1,
                "temperature": temperature,
                "humidity": humidity,
                "weight":0,
                "distance": 0,
                "soundStatus": int(sound),
                "isDoorOpen": int(door_open),
                "numOfIn": 0,
                "numOfOut": 0
            }

            send_data_to_api(sensor_data)
            print("🔄 Waiting for next cycle...\n")
            time.sleep(25)

    except KeyboardInterrupt:
        print("🛑 Program stopped by user.")
    finally:
        cleanup_gpio()

if __name__ == "__main__":
    main()
