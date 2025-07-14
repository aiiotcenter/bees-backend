#!/usr/bin/env python3
import requests
import time
import RPi.GPIO as GPIO
import subprocess

from sensors.DHT import get_temp_humidity
from sensors.sound import monitor_sound
from sensors.ir import read_ir_door_status
# from sensors.hx711py.weightsensor import get_weight
from sensors.gps_module import send_location_to_api
from connectivity import get_location_then_connect

API_URL      = "http://bees-backend.aiiot.center/api/records"
MAX_READINGS = 3

GPRS_SCRIPT  = "/home/pi/gprs_connect.sh"


def setup_gpio():
    print("🔧 Setting up GPIO...")
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(7, GPIO.IN)   # Sound
    GPIO.setup(9, GPIO.IN)   # IR


def cleanup_gpio():
    print("🧼 Cleaning up GPIO...")
    GPIO.cleanup()


def send_data_to_api(data):
    try:
        print(f"📤 Sending buffered data: {data}")
        resp = requests.post(API_URL, json=data, timeout=15)
        print(f"✅ API Response: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"⚠️ Error sending data: {e}")


def main():
    setup_gpio()
    buffered_data = []

    try:
        # 1) Take sensor snapshots
        for i in range(MAX_READINGS):
            print("🔄 Starting new reading...")
            temperature, humidity = get_temp_humidity()
            sound      = monitor_sound()
            door_open  = read_ir_door_status()
            # weight     = get_weight(timeout=2) or 0

            entry = {
                "hiveId":      "1",
                "temperature": str(temperature),
                "humidity":    str(humidity),
                # "weight":      str(weight),
                "distance":    0,
                "soundStatus": 1 if sound else 0,
                "isDoorOpen":  1 if door_open else 0,
                "numOfIn":     0,
                "numOfOut":    0,
                "latitude":    "0",
                "longitude":   "0"
            }
            buffered_data.append(entry)
            print(f"📦 Buffered {len(buffered_data)} readings.")
            time.sleep(2)

        # 2) Read GPS & bring up GPRS non‑blocking
        print("📰 Reading & connecting…")
        lat, lon = get_location_then_connect()
        if lat and lon:
            send_location_to_api(lat, lon)
        else:
            print("⚠️ GPS failed, proceeding with zeros")

        # 3) Send all buffered readings with the obtained coords
        for entry in buffered_data:
            entry["latitude"]  = str(lat or 0)
            entry["longitude"] = str(lon or 0)
            send_data_to_api(entry)
            time.sleep(2)

        print("✅ Sent all buffered data.")

    except KeyboardInterrupt:
        print("🛑 Interrupted by user.")
    finally:
        cleanup_gpio()


if __name__ == "__main__":
    while True:
        main()
        # optionally add a delay here if you don't want back‑to‑back loops:
        # time.sleep(5)
