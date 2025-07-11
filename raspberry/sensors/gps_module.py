import requests
import time
import RPi.GPIO as GPIO
import subprocess
from sensors.DHT import get_temp_humidity
from sensors.sound import monitor_sound
from sensors.ir import read_ir_door_status
from sensors.hx711py.weightsensor import get_weight
from sensors.gps_module import get_gsm_location, send_location_to_api  # <- your module

API_URL = "http://bees-backend.aiiot.center/api/records"
GPRS_SCRIPT = "/home/pi/gprs_connect.sh"
MAX_READINGS = 3
GPS_RETRIES = 3


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


def kill_ppp():
    subprocess.run(["sudo", "poff", "-a"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)


def start_gprs():
    print("📲 GPRS not active. Connecting...")
    try:
        subprocess.run(["sudo", GPRS_SCRIPT])
    except Exception as e:
        print(f"⚠️ GPRS connection error: {e}")


def gprs_connected():
    result = subprocess.run(["ifconfig"], capture_output=True, text=True)
    return "ppp0" in result.stdout


def clear_environment():
    print("🧹 Cleaning environment before start...")
    subprocess.run(["sudo", "pkill", "-f", "pppd"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["sudo", "pkill", "-f", "chat"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["sudo", "rm", "-f", "/var/lock/LCK..ttyS0"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    print("✅ ttyS0 is now free after 1 second(s).")


def main():
    clear_environment()
    setup_gpio()
    buffered_data = []

    try:
        for i in range(MAX_READINGS):
            print("🔄 Starting new reading...")
            temperature, humidity = get_temp_humidity()
            sound = monitor_sound()
            door_open = read_ir_door_status()
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
                "latitude": "0",
                "longitude": "0"
            }
            buffered_data.append(data)
            print(f"📦 Buffered {len(buffered_data)} readings.")
            time.sleep(2)

        # Connect GPRS
        kill_ppp()
        if not gprs_connected():
            start_gprs()
            time.sleep(5)

        print("📡 Reading GPS...")
        lat, lon = None, None
        for attempt in range(GPS_RETRIES):
            lat, lon = get_gsm_location()
            if lat and lon:
                send_location_to_api(lat, lon)
                break
            print(f"🔁 GPS attempt {attempt+1} failed. Retrying...")
            time.sleep(2)
        else:
            print("⚠️ GPS failed after multiple attempts.")
            lat, lon = "0", "0"

        for entry in buffered_data:
            entry["latitude"] = str(lat)
            entry["longitude"] = str(lon)
            send_data_to_api(entry)
            time.sleep(1)

        print("✅ Sent all buffered data.")

    except KeyboardInterrupt:
        print("🛑 Interrupted by user.")
    finally:
        cleanup_gpio()


if __name__ == "__main__":
    while True:
        main()
        print("⏳ Waiting 20 minutes before next batch...")
        time.sleep(1200)  # 20 minutes
