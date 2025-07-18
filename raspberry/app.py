#!/usr/bin/env python3
import time
import requests
import subprocess
import RPi.GPIO as GPIO

from sensors.DHT import get_temp_humidity
from sensors.sound import monitor_sound
from sensors.ir import read_ir_door_status
from sensors.gps_module import get_cell_location_via_google
from gprs_manager import start_gprs, is_up

# Configuration
API_URL      = "http://bees-backend.aiiot.center/api/records"
API_HOST     = "bees-backend.aiiot.center"
MAX_READINGS = 3


# def which_interface(host):
#     """
#     Resolve hostname to IPv4 and ask the kernel which interface it'll use.
#     """
#     res = subprocess.run(
#         ["getent", "ahostsv4", host], capture_output=True, text=True
#     )
#     ip = res.stdout.split()[0]
#     route = subprocess.run(
#         ["ip", "route", "get", ip], capture_output=True, text=True
#     ).stdout.strip()
#     return route

def which_interface():
    """
    Ask the kernel how it would reach the Internet (8.8.8.8),
    which tells us the default interface (ppp0 vs wlan0).
    """
    out = subprocess.run(
        ["ip", "route", "get", "8.8.8.8"],
        capture_output=True, text=True
    ).stdout
    return out.strip()


def setup_gpio():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(7, GPIO.IN)
    GPIO.setup(9, GPIO.IN)


def cleanup_gpio():
    GPIO.cleanup()


def send_data(entry):
    route = which_interface()
    print(f"🛣️  Default Route check: {route}")
    try:
        resp = requests.post(API_URL, json=entry, timeout=15)
        print(f"API→ {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"⚠️ send_data error: {e}")


def main():
    setup_gpio()
    buffered = []

    try:
        # 1) collect sensor readings
        for _ in range(MAX_READINGS):
            t,h = get_temp_humidity()
            s   = monitor_sound()
            door= read_ir_door_status()
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

        # 2) get location
        print("🌐 Getting location via SIM900+Google…")
        lat, lon = get_cell_location_via_google()
        if not lat or not lon:
            lat, lon = 0, 0

        # 3) bring up GPRS if needed
        if not is_up():
            print("📲 Starting GPRS for data link…")
            start_gprs()

        # 4) send buffered data with coords
        for entry in buffered:
            entry["latitude"]  = str(lat)
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
        time.sleep(10)