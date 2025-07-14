#!/usr/bin/env python3
import time, requests, RPi.GPIO as GPIO
from sensors.DHT import get_temp_humidity
from sensors.sound import monitor_sound
from sensors.ir import read_ir_door_status
# from sensors.hx711py.weightsensor import get_weight
from sensors.gps_module import get_cell_location_via_google

API_URL      = "http://bees-backend.aiiot.center/api/records"
MAX_READINGS = 3

def setup_gpio():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(7, GPIO.IN)
    GPIO.setup(9, GPIO.IN)

def cleanup_gpio():
    GPIO.cleanup()

def send_data(d):
    try:
        r = requests.post(API_URL, json=d, timeout=15)
        print("API→", r.status_code, r.text)
    except Exception as e:
        print("⚠️ send_data error:", e)

def main():
    setup_gpio()
    buffered = []

    try:
        # 1) take N sensor snapshots
        for _ in range(MAX_READINGS):
            t,h = get_temp_humidity()
            s   = monitor_sound()
            door= read_ir_door_status()
            # w   = get_weight(timeout=2) or 0
            buffered.append({
                "hiveId":"1","temperature":str(t),"humidity":str(h),
                "weight":0,"distance":0,
                "soundStatus":1 if s else 0,
                "isDoorOpen":1 if door else 0,
                "numOfIn":0,"numOfOut":0,
                "latitude":"0","longitude":"0",
                "status": True
            })
            time.sleep(2)

        # 2) get cell‑based location via Google
        print("🌐 Getting location via SIM900+Google…")
        lat, lon = get_cell_location_via_google()
        if not lat or not lon:
            lat, lon = 0, 0

        # 3) send each buffered reading with coords
        for entry in buffered:
            entry["latitude"]  = str(lat)
            entry["longitude"] = str(lon)
            print("📤", entry)
            send_data(entry)
            time.sleep(2)

    except KeyboardInterrupt:
        print("🛑 Interrupted")
    finally:
        cleanup_gpio()

if __name__=="__main__":
    while True:
        main()
        # optional: time.sleep(10)
