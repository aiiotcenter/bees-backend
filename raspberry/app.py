import requests
import time
import RPi.GPIO as GPIO
import subprocess
from sensors.DHT import get_temp_humidity
from sensors.sound import monitor_sound
from sensors.ir import read_ir_door_status
from sensors.hx711py.weightsensor import get_weight
from sensors.gps_module import get_gsm_location, send_location_to_api

API_URL = "http://bees-backend.aiiot.center/api/records"
BUFFER_SEND_INTERVAL = 3  # Set to 3 for test
GPRS_SCRIPT = "/home/pi/gprs_connect.sh"

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

def kill_ppp():
    subprocess.run(["sudo", "poff", "-a"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)

def wait_for_ttyS0_free(timeout=10):
    for i in range(timeout):
        result = subprocess.run(["lsof", "/dev/ttyS0"], capture_output=True, text=True)
        if not result.stdout.strip():
            print(f"✅ ttyS0 is now free after {i+1} seconds.")
            return True
        time.sleep(1)
    print("❌ ttyS0 still busy after 10 seconds.")
    return False

def start_gprs():
    print("📞 GPRS not active. Connecting...")
    try:
        subprocess.run(["sudo", GPRS_SCRIPT])
        time.sleep(10)
    except Exception as e:
        print(f"⚠️ GPRS connection error: {e}")

def set_gprs_as_default():
    try:
        subprocess.run(["sudo", "ip", "route", "del", "default"], stderr=subprocess.DEVNULL)
        subprocess.run(["sudo", "ip", "route", "add", "default", "dev", "ppp0"])
        print("🌐 GPRS set as default route.")
    except Exception as e:
        print(f"⚠️ Failed to set GPRS route: {e}")

def gprs_connected():
    result = subprocess.run(["ifconfig"], capture_output=True, text=True)
    return "ppp0" in result.stdout

def main():
    setup_gpio()
    buffered_data = []

    try:
        for _ in range(BUFFER_SEND_INTERVAL):
            print("🔄 Starting new reading...")
            temperature, humidity = safe_read(get_temp_humidity, name="Temp/Humidity", fallback=(-1, -1))
            sound = safe_read(monitor_sound, name="Sound", fallback=0)
            door_open = safe_read(read_ir_door_status, name="Door", fallback=0)
            weight = get_weight(timeout=2) or 0

            # ❗️Stop GPRS to free /dev/ttyS0
            kill_ppp()

            lat, lon = "0", "0"
            if wait_for_ttyS0_free():
                print("📡 Reading GPS...")
                lat, lon = get_gsm_location()
                if lat and lon:
                    send_location_to_api(lat, lon)
                else:
                    print("⚠️ GPS returned no coordinates.")
                    lat, lon = "0", "0"

            # ✅ Restart GPRS if not already connected
            if not gprs_connected():
                start_gprs()
            set_gprs_as_default()

            data = {
                "hiveId": "1",
                "temperature": str(temperature),
                "humidity": str(humidity),
                "weight": str(weight),
                "distance": 0,
                "soundStatus": 1 if sound else 0,
                "isDoorOpen": 1 if door_open else 0,
                "numOfIn": 0,
                "numOfOut": 0,
                "latitude": str(lat),
                "longitude": str(lon)
            }

            buffered_data.append(data)
            print(f"📦 Buffered {len(buffered_data)} readings.\n")
            time.sleep(10)  # Shorter delay for testing

        # ✅ After 3 readings
        print("🚀 Sending all buffered data...")
        for entry in buffered_data:
            send_data_to_api(entry)
            time.sleep(1)

        print("✅ All test data sent.")

    except KeyboardInterrupt:
        print("🛑 Program stopped by user.")
    finally:
        cleanup_gpio()

if __name__ == "__main__":
    main()
