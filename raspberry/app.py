import requests
import time
import RPi.GPIO as GPIO
import subprocess
import serial
import re

from sensors.DHT import get_temp_humidity
from sensors.sound import monitor_sound
from sensors.ir import read_ir_door_status
from sensors.hx711py.weightsensor import get_weight

API_URL = "http://bees-backend.aiiot.center/api/records"
LOCATION_API = "https://www.googleapis.com/geolocation/v1/geolocate?key=YOUR_GOOGLE_API_KEY"
GPRS_SCRIPT = "/home/pi/gprs_connect.sh"
MAX_READINGS = 3
GPS_RETRIES = 3


def setup_gpio():
    print("\U0001f527 Setting up GPIO...")
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(7, GPIO.IN)
    GPIO.setup(9, GPIO.IN)


def cleanup_gpio():
    print("\U0001f9fc Cleaning up GPIO...")
    GPIO.cleanup()


def send_data_to_api(data):
    try:
        print(f"\U0001f4e4 Sending buffered data: {data}")
        response = requests.post(API_URL, json=data, timeout=10)
        print(f"\u2705 API Response: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"\u26a0\ufe0f Error sending data: {e}")


def get_gsm_location():
    try:
        ser = serial.Serial("/dev/ttyS0", baudrate=4800, timeout=2)
        ser.flushInput()

        ser.write(b"AT\r")
        time.sleep(1)
        ok = ser.read(64).decode(errors='ignore')
        if "OK" not in ok:
            print("\u26a0\ufe0f No response to AT command.")
            ser.close()
            return None, None

        ser.write(b"AT+CREG?\r")
        time.sleep(1)
        response = ser.read(128).decode(errors='ignore')
        print(f"\U0001f4f6 CREG Response: {repr(response)}")

        match = re.search(r'\+CREG: \d,\d,"([0-9A-F]+)","([0-9A-F]+)"', response)
        if not match:
            print("\u274c Could not extract LAC/CID.")
            ser.close()
            return None, None

        lac, cid = match.groups()
        print(f"\u2705 LAC: {lac}, CID: {cid}")

        data = {
            "cellTowers": [{
                "cellId": int(cid, 16),
                "locationAreaCode": int(lac, 16),
                "mobileCountryCode": 472,  # Replace with actual MCC
                "mobileNetworkCode": 1     # Replace with actual MNC
            }]
        }

        response = requests.post(LOCATION_API, json=data, timeout=10)
        if response.status_code == 200:
            location = response.json().get("location", {})
            lat, lon = location.get("lat"), location.get("lng")
            print(f"\U0001f30d Location from Google: {lat}, {lon}")
            ser.close()
            return lat, lon
        else:
            print(f"\u274c Location API error: {response.status_code}")
        ser.close()
        return None, None
    except Exception as e:
        print(f"\u26a0\ufe0f GSM error: {e}")
        return None, None


def send_location_to_api(lat, lon):
    try:
        print(f"\U0001f4e4 Sending to server: {{'latitude': {lat}, 'longitude': {lon}}}")
        resp = requests.post("http://bees-backend.aiiot.center/api/location", json={
            "latitude": lat,
            "longitude": lon
        }, timeout=10)
        print(f"\u2705 Server Response: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"\u26a0\ufe0f Failed to send location: {e}")


def kill_ppp():
    subprocess.run(["sudo", "poff", "-a"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)


def start_gprs():
    print("\U0001f4f2 GPRS not active. Connecting...")
    try:
        subprocess.run(["sudo", GPRS_SCRIPT])
    except Exception as e:
        print(f"\u26a0\ufe0f GPRS connection error: {e}")


def gprs_connected():
    result = subprocess.run(["ifconfig"], capture_output=True, text=True)
    return "ppp0" in result.stdout


def clear_environment():
    print("\U0001f9f9 Cleaning environment before start...")
    subprocess.run(["sudo", "pkill", "-f", "pppd"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["sudo", "pkill", "-f", "chat"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["sudo", "rm", "-f", "/var/lock/LCK..ttyS0"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    print("\u2705 ttyS0 is now free after 1 second(s).")


def main():
    clear_environment()
    setup_gpio()
    buffered_data = []

    try:
        for i in range(MAX_READINGS):
            print("\U0001f504 Starting new reading...")
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
            print(f"\U0001f4e6 Buffered {len(buffered_data)} readings.")
            time.sleep(2)

        kill_ppp()
        if not gprs_connected():
            start_gprs()
            time.sleep(5)

        print("\U0001f4f0 Reading GPS...")
        lat, lon = None, None
        for attempt in range(GPS_RETRIES):
            lat, lon = get_gsm_location()
            if lat and lon:
                send_location_to_api(lat, lon)
                break
            print(f"\U0001f501 GPS attempt {attempt+1} failed. Retrying...")
            time.sleep(2)
        else:
            print("\u26a0\ufe0f GPS failed after multiple attempts.")
            lat, lon = "0", "0"

        for entry in buffered_data:
            entry["latitude"] = str(lat)
            entry["longitude"] = str(lon)
            send_data_to_api(entry)
            time.sleep(1)

        print("\u2705 Sent all buffered data.")

    except KeyboardInterrupt:
        print("\U0001f6d1 Interrupted by user.")
    finally:
        cleanup_gpio()


if __name__ == "__main__":
    while True:
        main()
        print("⏳ Waiting 20 minutes before next batch...")
        time.sleep(1200)  # 20 minutes
