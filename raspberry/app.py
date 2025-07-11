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
GPRS_SCRIPT = "/home/pi/gprs_connect.sh"
GPS_RETRIES = 3
READINGS_BEFORE_GPS = 3

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

def start_gprs():
    print("📞 GPRS not active. Connecting...")
    try:
        subprocess.run(["sudo", GPRS_SCRIPT])
        time.sleep(10)
    except Exception as e:
        print(f"⚠️ GPRS connection error: {e}")

def set_gprs_as_default():
    try:
        print("🌐 Switching default route to GPRS...")
        subprocess.run(["sudo", "ip", "route", "del", "default"], stderr=subprocess.DEVNULL)
        subprocess.run(["sudo", "ip", "route", "add", "default", "dev", "ppp0"], check=True)
        print("🌐 GPRS is now default route.")
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Failed to set GPRS route: {e}")

def gprs_connected():
    result = subprocess.run(["ifconfig"], capture_output=True, text=True)
    return "ppp0" in result.stdout

def wait_for_tty_free(timeout=10):
    for i in range(timeout):
        result = subprocess.run(["lsof", "/dev/ttyS0"], capture_output=True, text=True)
        if not result.stdout.strip():
            print(f"✅ ttyS0 is now free after {i+1} seconds.")
            return
        time.sleep(1)
    print("⚠️ ttyS0 still busy after timeout.")

def main():
    setup_gpio()
    buffered_data = []
    gps_lat = "0"
    gps_lon = "0"

    try:
        for reading_count in range(READINGS_BEFORE_GPS):
            print("🔄 Starting new reading...")

            temperature, humidity = safe_read(get_temp_humidity, name="Temp/Humidity", fallback=(-1, -1))
            sound = safe_read(monitor_sound, name="Sound", fallback=0)
            door_open = safe_read(read_ir_door_status, name="Door", fallback=0)
            weight = get_weight(timeout=2) or 0

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
                "latitude": gps_lat,
                "longitude": gps_lon
            }

            buffered_data.append(data)
            print(f"📦 Buffered {len(buffered_data)} readings.")
            time.sleep(1)

        # Stop GPRS and wait for ttyS0 to be free
        kill_ppp()
        wait_for_tty_free()

        # Try getting GPS data up to N times
        print("📡 Reading GPS...")
        for attempt in range(GPS_RETRIES):
            gps_lat, gps_lon = get_gsm_location()
            if gps_lat and gps_lon and gps_lat != "0":
                send_location_to_api(gps_lat, gps_lon)
                break
            print(f"🔁 GPS attempt {attempt+1} failed. Retrying...")
            time.sleep(2)
        else:
            print("⚠️ GPS failed after multiple attempts.")

        # Start GPRS again
        if not gprs_connected():
            start_gprs()

        set_gprs_as_default()
        print("✅ Default route set. Proceeding to send data...")

        # Update GPS in data and send
        for entry in buffered_data:
            entry["latitude"] = gps_lat
            entry["longitude"] = gps_lon
            send_data_to_api(entry)
            time.sleep(1)

        print("✅ Sent all buffered data.")

    except KeyboardInterrupt:
        print("🛑 Program stopped by user.")
    finally:
        cleanup_gpio()

if __name__ == "__main__":
    main()
