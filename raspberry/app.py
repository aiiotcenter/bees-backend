#!/usr/bin/env python3
import os
import time
import json
import threading
import subprocess
import shutil
from typing import Tuple

import requests
import RPi.GPIO as GPIO

from sensors.DHT import get_temp_humidity
from sensors.sound import monitor_sound
from sensors.ir import read_ir_door_status
from sensors.gps_module import get_cell_location_via_google
from gprs_manager import start_gprs, is_up

# ── CONFIG ────────────────────────────────────────────────────────────────────
API_URL        = "http://100.70.97.126:9602/api/records"
MAX_READINGS   = 3
SEND_INTERVAL  = 20 * 60
USB_ENUM_DELAY = 8
KEEP_ON_AFTER_SEND = 5

USB3_HUB = "2"          # Pi 4 USB3 root hub
USB3_PORT_RANGE = "1-4" # all four ports
USB2_ROOT = "1"         # Pi 4 USB2 root hub
USB2_UPSTREAM_PORT = "1"
MODEM_VIDPID = "19d2:1405"  # ZTE

GUARD_INTERVAL = 1.0    # seconds

# Resolve uhubctl path (systemd/cron may have different PATH)
UHUBCTL = shutil.which("uhubctl") or "/usr/sbin/uhubctl"

# ── UTILITIES ────────────────────────────────────────────────────────────────
def run(cmd, check=True, capture=False):
    if capture:
        p = subprocess.run(cmd, check=check, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return p.stdout
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

def wait_for_lsusb(vidpid: str, present: bool, timeout_s: float) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        if lsusb_has(vidpid) == present:
            return True
        time.sleep(0.5)
    return False

# ── USB POWER CONTROL + GUARD ────────────────────────────────────────────────
def usb_all_off():
    sp = sudo_prefix()
    # OFF USB3
    cmd1 = sp + [UHUBCTL, "-l", USB3_HUB, "-p", USB3_PORT_RANGE, "-a", "off"]
    # OFF USB2 upstream
    cmd2 = sp + [UHUBCTL, "-l", USB2_ROOT, "-p", USB2_UPSTREAM_PORT, "-a", "off"]
    print("UHUB→", " ".join(cmd1)); run(cmd1, check=True)
    print("UHUB→", " ".join(cmd2)); run(cmd2, check=True)

def usb_all_on():
    sp = sudo_prefix()
    # ON USB2 upstream first, then USB3 (order matters)
    cmd1 = sp + [UHUBCTL, "-l", USB2_ROOT, "-p", USB2_UPSTREAM_PORT, "-a", "on"]
    cmd2 = sp + [UHUBCTL, "-l", USB3_HUB, "-p", USB3_PORT_RANGE, "-a", "on"]
    print("UHUB→", " ".join(cmd1)); run(cmd1, check=True)
    print("UHUB→", " ".join(cmd2)); run(cmd2, check=True)

class USBOffGuard:
    """Re-asserts USB OFF every second while active. Pause before ON; resume after OFF."""
    def __init__(self, interval_sec: float = GUARD_INTERVAL):
        self.interval = interval_sec
        self._stop = threading.Event()
        self._paused = threading.Event()  # when set => paused
        self._paused.clear()              # start active

    def start(self):
        t = threading.Thread(target=self._worker, daemon=True)
        t.start()
        self._thread = t

    def _worker(self):
        while not self._stop.is_set():
            if not self._paused.is_set():
                try:
                    usb_all_off()
                except Exception as e:
                    print("Guard OFF error:", e)
            time.sleep(self.interval)

    def pause(self):
        print("🛑 Pausing guard")
        self._paused.set()

    def resume(self):
        print("🟢 Resuming guard")
        self._paused.clear()

    def stop(self):
        self._stop.set()

# ── GPIO ─────────────────────────────────────────────────────────────────────
def setup_gpio():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(7, GPIO.IN)
    GPIO.setup(9, GPIO.IN)

def cleanup_gpio():
    GPIO.cleanup()

# ── SENDING LOGIC ────────────────────────────────────────────────────────────
def send_data(entry: dict):
    route = which_interface()
    print(f"🛣️ Default route: {route}")
    try:
        r = requests.post(API_URL, json=entry, timeout=15)
        print(f"API→ {r.status_code} {r.text[:200]}")
    except Exception as e:
        print("⚠️ send_data error:", e)

def do_one_send_cycle(guard: USBOffGuard):
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

    # 2) Location (move below ON if your method needs the modem)
    print("🌐 Getting location via SIM900+Google…")
    try:
        lat, lon = get_cell_location_via_google()
    except Exception as e:
        print("⚠️ get_cell_location_via_google error:", e)
        lat, lon = (0, 0)
    if not lat or not lon:
        lat, lon = (0, 0)

    # 3) USB ON + wait for enumeration
    guard.pause()
    usb_all_on()
    print("⏳ Waiting for USB enumeration…")
    time.sleep(USB_ENUM_DELAY)

    # Optional: wait for modem to show up (adjust VID:PID if needed)
    if MODEM_VIDPID:
        appeared = wait_for_lsusb(MODEM_VIDPID, present=True, timeout_s=20)
        print(f"🔎 Modem present after ON: {appeared}")

    # 4) Bring up GPRS if needed
    try:
        if not is_up():
            print("📲 Starting GPRS…")
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
    usb_all_off()
    # Optional: verify modem gone
    if MODEM_VIDPID:
        gone = wait_for_lsusb(MODEM_VIDPID, present=False, timeout_s=10)
        print(f"🪫 Modem gone after OFF: {gone}")
    guard.resume()

# ── MAIN LOOP ────────────────────────────────────────────────────────────────
def main():
    if not os.path.exists(UHUBCTL):
        raise RuntimeError(f"uhubctl not found at {UHUBCTL}. Install it: sudo apt install uhubctl")

    setup_gpio()

    # Force OFF immediately so we start dark
    print("🔌 Forcing ALL USB OFF at startup…")
    usb_all_off()

    guard = USBOffGuard(interval_sec=GUARD_INTERVAL)
    try:
        guard.start()
        print("🛡️ USB OFF guard active.")

        if os.getenv("SINGLE_CYCLE") == "1":
            do_one_send_cycle(guard)
            return

        while True:
            t0 = time.time()
            do_one_send_cycle(guard)
            elapsed = time.time() - t0
            sleep_left = max(0, SEND_INTERVAL - elapsed)
            print(f"⏱️ Sleeping {int(sleep_left)}s until next cycle…")
            time.sleep(sleep_left)

    except KeyboardInterrupt:
        print("🛑 Interrupted by user.")
    finally:
        guard.stop()
        cleanup_gpio()

if __name__ == "__main__":
    main()
