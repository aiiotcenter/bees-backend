import requests
import time
import RPi.GPIO as GPIO
import subprocess

from DHT import get_temp_humidity
from sound import monitor_sound
from ir import read_ir_door_status
from gps_module import get_gps_location, send_location_to_api
from sensors.hx711py.weightsensor import get_weight
API_URL = "http://bees-backend.aiiot.center/api/records"
BUFFER_SEND_INTERVAL = 15

def setup_gpio():
    print("🔧 Setting up GPIO...")
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(7, GPIO.IN)
    GPIO.setup(9, GPIO.IN)

def cleanup_gpio():
    print("🧼 Cleaning up GPIO...")
    GPIO.cleanup()

def send_data_to_api(data):
    try:
        print(f"📤 Sending buffered data: {data}")
        response = requests.post(API_URL, json=data, timeout=10)
        print(f"✅ API Response: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"⚠️ Error sending data: {e}")

def safe_read(func, name="sensor", fallback=None):
    try:
        return func()
    except Exception as e:
        print(f"⚠️ {name} failed: {e}")
        return fallback

def check_gprs_and_connect():
    result = subprocess.run(['ifconfig'], capture_output=True, text=True)
    if 'ppp0' not in result.stdout:
        print("📡 GPRS not active. Attempting to connect...")
        try:
            subprocess.run(['sudo', '/home/pi/gprs_connect.sh'])
            time.sleep(10)
        except Exception as e:
            print(f"⚠️ Failed to launch GPRS: {e}")
    else:
        print("📶 GPRS is already active.")

def main():
    setup_gpio()
    buffered_data = []

    try:
        while True:
            temperature, humidity = safe_read(get_temp_humidity, name="Temp/Humidity", fallback=(-1, -1))
            sound = safe_read(monitor_sound, name="Sound", fallback=0)
            door_open = safe_read(read_ir_door_status, name="Door", fallback=0)
            weight = get_weight(timeout=2) or 0

            lat, lon = get_gps_location()
            if lat and lon:
                send_location_to_api(lat, lon)

            data = {
                "hiveId": "1",
                "temperature": str(temperature),
                "humidity": str(humidity),
                "weight": str(weight),
                "distance": 0,
                "soundStatus": 1 if sound else 0,
                "isDoorOpen": 1 if door_open else 0,
                "numOfIn": 0,
                "numOfOut": 0
            }

            buffered_data.append(data)
            print(f"📦 Buffered {len(buffered_data)} readings.")

            if len(buffered_data) >= BUFFER_SEND_INTERVAL:
                check_gprs_and_connect()
                for entry in buffered_data:
                    send_data_to_api(entry)
                    time.sleep(1)
                buffered_data.clear()
                print("✅ Sent all buffered data.")

            print("🔄 Waiting for next cycle...\\n")
            time.sleep(60)

    except KeyboardInterrupt:
        print("🛑 Program stopped by user.")
    finally:
        cleanup_gpio()

if __name__ == "__main__":
    main()