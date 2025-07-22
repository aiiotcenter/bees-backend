#!/usr/bin/env python3
import time
import requests
import subprocess
import RPi.GPIO as GPIO
import json

from sensors.DHT import get_temp_humidity
from sensors.sound import monitor_sound
from sensors.ir import read_ir_door_status

# Configuration
API_URL      = "http://bees-backend.aiiot.center/api/records"
# API_URL      = "http://198.187.28.245/api/records"
API_HOST     = "bees-backend.aiiot.center"
MAX_READINGS = 3

# Path to your WiFi geolocation shell script
WIFI_LOCATION_SCRIPT = "./wifi_location.sh"  # Update this path as needed


def get_ip_location():
    """
    Get location using IP-based geolocation (works with any internet connection)
    Returns (latitude, longitude) tuple or (0, 0) if failed
    """
    try:
        print("🌐 Getting location via IP geolocation...")
        
        # Try multiple IP geolocation services
        services = [
            "http://ip-api.com/json/",
            "https://ipapi.co/json/",
            "https://freegeoip.app/json/"
        ]
        
        for service in services:
            try:
                response = requests.get(service, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    
                    # Different services use different field names
                    lat = data.get('lat') or data.get('latitude')
                    lon = data.get('lon') or data.get('longitude')
                    
                    if lat and lon:
                        print(f"📍 Location found via {service}: {lat}, {lon}")
                        return float(lat), float(lon)
                        
            except Exception as e:
                print(f"⚠️ Failed to get location from {service}: {e}")
                continue
        
        print("⚠️ All IP geolocation services failed")
        return 0, 0
            
    except Exception as e:
        print(f"⚠️ IP geolocation error: {e}")
        return 0, 0


def which_interface():
    """
    Show the kernel's current default route.  
    (This tells us whether ppp0 or wlan0 is being used.)
    """
    try:
        out = subprocess.run(
            ["ip", "route", "show", "default"],
            capture_output=True, text=True
        ).stdout
        return out.strip()
    except Exception as e:
        print(f"⚠️ Error getting interface info: {e}")
        return "unknown"


def setup_gpio():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(7, GPIO.IN)
    GPIO.setup(9, GPIO.IN)


def cleanup_gpio():
    GPIO.cleanup()


def send_data(entry):
    route = which_interface()
    print(f"🛣️  Default route: {route}")
    try:
        r = requests.post(API_URL, json=entry, timeout=15)
        print(f"API→ {r.status_code} {r.text}")
    except Exception as e:
        print(f"⚠️ send_data error:", e)


def main():
    setup_gpio()
    buffered = []

    try:
        # 1) collect sensor readings
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

        # 2) get location via IP geolocation
        lat, lon = get_ip_location()
        if not lat or not lon:
            lat, lon = 0, 0

        # 3) send buffered data with coordinates
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
        time.sleep(10)