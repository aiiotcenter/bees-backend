#!/usr/bin/env python3
import os
import time
import json
import threading
import subprocess
from typing import Tuple

# ──────────────────────────────────────────────────────────────────────────────
# External deps expected: uhubctl, requests, RPi.GPIO
# Your existing modules:
# ──────────────────────────────────────────────────────────────────────────────
import requests
import RPi.GPIO as GPIO

from sensors.DHT import get_temp_humidity
from sensors.sound import monitor_sound
from sensors.ir import read_ir_door_status
from sensors.gps_module import get_cell_location_via_google
from gprs_manager import start_gprs, is_up

# ──────────────────────────────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────────────────────────────
API_URL        = "http://100.70.97.126:9602/api/records"
API_HOST       = "http://100.70.97.126:9602"
MAX_READINGS   = 3                  # how many sensor samples to buffer each cycle
SEND_INTERVAL  = 20 * 60            # seconds between send cycles (20 minutes)
USB_ENUM_DELAY = 8                  # wait after turning USB ON
KEEP_ON_AFTER_SEND = 5              # keep USB ON briefly after sending

# Pi 4 hubs: USB3 root hub "2" (ports 1-4), USB2 root hub "1", upstream port "1"
USB3_HUB = "2"
USB3_PORT_RANGE = "1-4"
USB2_ROOT = "1"
USB2_UPSTREAM_PORT = "1"

MODEM_VIDPID = "19d2:1405"          # optional presence check

# ──────────────────────────────────────────────────────────────────────────────
# UTILITIES
# ──────────────────────────────────────────────────────────────────────────────
def run(cmd, check=True, capture=False):
    if capture:
        return subprocess.run(cmd, check=check, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True).stdout
    subprocess.run(cmd, check=check)

def sudo_prefix():
    return [] if os.geteuid() == 0 else ["sudo"]

def which_interface() -> str:
    try:
        return run(["ip","route","show","default"], check=True, capture=True).strip()
    except Exception:
        return ""

def lsusb_has(vidpid: str) -> bool:
    try:
        out = run(["lsusb"], check=True, capture=True)
        return vidpid.lower() in out.lower()
    except Exception:
        return False

def request_post(url: str, payload: dict, timeout: int = 15) -> Tuple[int, str]:
    try:
        r = requests.post(url, json=payload, timeout=timeout)
        return (r.status_code, r.text)
    except Exception as e:
        return (-1, str(e))

# ──────────────────────────────────────────────────────────────────────────────
# USB POWER CONTROL + GUARD
# ──────────────────────────────────────────────────────────────────────────────
def usb_all_off():
    sp = sudo_prefix()
    # USB3 ports off
    run(sp + ["uhubctl","-l",USB3_HUB,"-p",USB3_PORT_RANGE,"-a","off"], check=False)
    # USB2 upstream off (kills the whole USB2 tree incl. hub 1-1)
    run(sp + ["uhubctl","-l",USB2_ROOT,"-p",USB2_UPSTREAM_PORT,"-a","off"], check=False)

def usb_all_on():
    sp = sudo_prefix()
    # Bring USB2 upstream first, then USB3 ports
    run(sp + ["uhubctl","-l",USB2_ROOT,"-p",USB2_UPSTREAM_PORT,"-a","on"], check=False)
    run(sp + ["uhubctl","-l",USB3_HUB,"-p",USB3_PORT_RANGE,"-a","on"], check=False)

class USBOffGuard:
    """Re-asserts USB OFF every second while active. Pause before ON; resume after OFF."""
    def __init__(self, interval_sec: float = 1.0):
        self.interval = interval_sec
        self._stop = threading.Event()
        self._paused = threading.Event()
        self._paused.clear()  # active

    def start(self):
        t = threading.Thread(target=self._worker, daemon=True)
        t.start()
        self._thread = t

    def _worker(self):
        while not self._stop.is_set():
            if not self._paused.is_set():
                try: usb_all_off()
                except Exception: pass
            time.sleep(self.interval)

    def pause(self):  self._paused.set()
    def resume(self): self._paused.clear()
    def stop(self):   self._stop.set()

# ──────────────────────────────────────────────────────────────────────────────
# GPIO
# ──────────────────────────────────────────────────────────────────────────────
def setup_gpio():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(7, GPIO.IN)
    GPIO.setup(9, GPIO.IN)

def cleanup_gpio():
    GPIO.cleanup()

# ──────────────────────────────────────────────────────────────────────────────
# SENDING LOGIC
# ──────────────────────────────────────────────────────────────────────────────
def send_data(entry: dict):
    route = which_interface()
    print(f"🛣️ Default route: {route}")
    code, text = request_post(API_URL, entry, timeout=15)
    print(f"API→ {code} {text[:200]}")

def do_one_send_cycle(guard: USBOffGuard):
    """
    1) Collect sensor data while USB is OFF
    2) Turn USB ON, wait for enumeration
    3) Ensure GPRS up
    4) Send buffered data
    5) Turn USB OFF and resume guard
    """
    # 1) Read sensors (USB OFF)
    buffered = []
    for _ in range(MAX_READINGS):
        t, h = get_temp_humidity()
        s = monitor_sound()
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

    # 2) Get location (move below ON if your method needs the modem)
    print("🌐 Getting location via SIM900+Google…")
    try:
        lat, lon = get_cell_location_via_google()
    except Exception as e:
        print("⚠️ get_cell_location_via_google error:", e)
        lat, lon = (0, 0)
    if not lat or not lon:
        lat, lon = (0, 0)

    # 3) Turn USB ON + wait for enumeration
    print("🔌 Turning ALL USB ON…")
    guard.pause()
    usb_all_on()
    time.sleep(USB_ENUM_DELAY)

    # 4) Bring up GPRS if needed
    try:
        if not is_up():
            print("📲 Starting GPRS for data link…")
            start_gprs()
    except Exception as e:
        print("⚠️ GPRS bring-up error:", e)

    # 5) Send buffered data
    for entry in buffered:
        entry["latitude"], entry["longitude"] = str(lat), str(lon)
        print("📤 Sending:", json.dumps(entry))
        send_data(entry)
        time.sleep(2)

    print("✅ All data sent. Keeping USB ON briefly…")
    time.sleep(KEEP_ON_AFTER_SEND)

    # 6) USB OFF + resume guard
    print("🪫 Turning ALL USB OFF…")
    usb_all_off()
    guard.resume()
    print("🛡️ Guard resumed (USB stays OFF).")

# ──────────────────────────────────────────────────────────────────────────────
# MAIN LOOP
# ──────────────────────────────────────────────────────────────────────────────
def main():
    setup_gpio()

    # Force USB OFF immediately on startup (so you're dark from the get-go)
    usb_all_off()

    guard = USBOffGuard(interval_sec=1.0)
    try:
        guard.start()
        print("🛡️ USB OFF guard is active.")

        if os.getenv("SINGLE_CYCLE") == "1":
            # one send then exit (quick test mode)
            do_one_send_cycle(guard)
            return

        while True:
            start_ts = time.time()
            do_one_send_cycle(guard)
            elapsed = time.time() - start_ts
            sleep_left = max(0, SEND_INTERVAL - elapsed)
            print(f"⏱️ Waiting {int(sleep_left)}s until next cycle…")
            time.sleep(sleep_left)

    except KeyboardInterrupt:
        print("🛑 Interrupted by user.")
    finally:
        guard.stop()
        cleanup_gpio()

if __name__ == "__main__":
    main()
