#!/usr/bin/env python3
import time
import requests
import subprocess
import RPi.GPIO as GPIO
from sensors.DHT import get_temp_humidity
from sensors.sound import monitor_sound
from sensors.ir import read_ir_door_status
from sensors.gps_module import get_cell_location_via_google

# Configuration
API_URL = "http://bees-backend.aiiot.center/api/records"
API_HOST = "bees-backend.aiiot.center"
MAX_READINGS = 3


def which_interface(host):
    """
    Resolve a hostname to its IPv4 address and ask the kernel which
    network interface will be used to reach it.
    """
    # Resolve hostname to IP
    res = subprocess.run(
        ["getent", "ahostsv4", host],
        capture_output=True, text=True
    )
    ip = res.stdout.split()[0]
    # Ask the kernel for the route
    route_res = subprocess.run(
        ["ip", "route", "get", ip],
        capture_output=True, text=True
    )
    return route_res.stdout.strip()


def setup_gpio():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(7, GPIO.IN)   # Sound sensor input
    GPIO.setup(9, GPIO.IN)   # IR sensor input


def cleanup_gpio():
    GPIO.cleanup()


def send_data(entry):
    # Log which interface will be used for the API call
    route = which_interface(API_HOST)
    print(f"🛣️  Route for {API_HOST}: {route}")
    try:
        response = requests.post(API_URL, json=entry, timeout=15)
        print(f"API→ {response.status_code} {response.text}")
    except Exception as e:
        print(f"⚠️ send_data error: {e}")


def main():
    setup_gpio()
    buffered = []

    try:
        # 1) take multiple sensor readings
        for _ in range(MAX_READINGS):
            t, h = get_temp_humidity()
            s    = monitor_sound()
            door = read_ir_door_status()
            buffered.append({
                "hiveId": "1",
                "temperature": str(t),
                "humidity": str(h),
                "weight": 0,
                "distance": 0,
                "soundStatus": 1 if s else 0,
                "isDoorOpen": 1 if door else 0,
                "numOfIn": 0,
                "numOfOut": 0,
                "latitude": "0",
                "longitude": "0",
                "status": True
            })
            print(f"📦 Buffered {len(buffered)} readings.")
            time.sleep(2)

        # 2) get location via SIM900 + Google
        print("🌐 Getting location via SIM900+Google…")
        lat, lon = get_cell_location_via_google()
        if not lat or not lon:
            lat, lon = 0, 0

        # 3) send buffered data with coords
        for entry in buffered:
            entry["latitude"] = str(lat)
            entry["longitude"] = str(lon)
            print(f"📤 Sending entry: {entry}")
            send_data(entry)
            time.sleep(2)

        print("✅ All data sent.")

    except KeyboardInterrupt:
        print("🛑 Interrupted by user.")
    finally:
        cleanup_gpio()


if __name__ == "__main__":
    while True:
        main()
        # Optional: sleep between cycles
        time.sleep(10)
