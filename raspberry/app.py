import requests
import time
import RPi.GPIO as GPIO
from sensors.DHT import get_temp_humidity
from sensors.sound import monitor_sound
from sensors.ir import read_ir_door_status
from sensors.hx711py.weightsensor import get_weight  # use your new file

API_URL = "http://bees-backend.aiiot.center/api/records"

def setup_gpio():
    print("🔧 Setting up GPIO...")
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(7, GPIO.IN)  # Sound sensor
    GPIO.setup(9, GPIO.IN)  # IR sensor

def cleanup_gpio():
    print("🧼 Cleaning up GPIO...")
    GPIO.cleanup()

def send_data_to_api(data):
    try:
        print(f"📤 Sending sensor data: {data}")
        response = requests.post(API_URL, data=data, timeout=5)
        print(f"✅ Sensor API Response: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"⚠️ Error sending sensor data: {e}")

def safe_read(func, name="sensor", fallback=None):
    try:
        return func()
    except Exception as e:
        print(f"⚠️ {name} failed: {e}")
        return fallback

def main():
    setup_gpio()
    try:
        while True:
            temperature, humidity = safe_read(get_temp_humidity, name="Temp/Humidity", fallback=(-1, -1))
            sound = safe_read(monitor_sound, name="Sound", fallback=0)
            door_open = safe_read(read_ir_door_status, name="Door", fallback=False)
            weight = get_weight(timeout=2) or 0

            sensor_data = {
                "hiveId": 1,
                "temperature": temperature,
                "humidity": humidity,
                "weight": weight,
                "distance": 0,
                "soundStatus": sound,
                "isDoorOpen": int(door_open),
                "numOfIn": 0,
                "numOfOut": 0
            }

            send_data_to_api(sensor_data)
            print("🔄 Waiting for next cycle...\n")
            time.sleep(60)

    except KeyboardInterrupt:
        print("🛑 Program stopped by user.")
    finally:
        cleanup_gpio()

if __name__ == "__main__":
    main()
