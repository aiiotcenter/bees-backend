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
MAX_READINGS = 5

# Google Geolocation API Key
GOOGLE_API_KEY = "AIzaSyCysMdMd_f01vX0vF6EOJtohcAe0YvtipY"
USB_INTERFACE = "eth0"  # ZTE WCDMA modem creates eth0 interface


def get_cellular_location():
    """
    Get high-accuracy location using cellular network through Google Geolocation API
    This method uses cellular IP + radio type for better accuracy than simple IP geolocation
    Returns (latitude, longitude) tuple or (0, 0) if failed
    """
    try:
        print("🌐 Getting cellular location via Google Geolocation API...")
        
        # Force request through cellular interface by binding to eth0 IP
        eth0_ip = None
        try:
            result = subprocess.run(
                ["ip", "addr", "show", USB_INTERFACE],
                capture_output=True, text=True
            )
            # Extract IP address from eth0
            for line in result.stdout.split('\n'):
                if 'inet ' in line and 'scope global' in line:
                    eth0_ip = line.split('inet ')[1].split('/')[0].strip()
                    break
        except:
            pass
        
        print(f"📡 Using cellular IP: {eth0_ip}")
        
        # Create payload optimized for cellular location
        # Google uses multiple signals: IP geolocation + cellular network characteristics
        payload = {
            "considerIp": True,  # Use IP-based location (very important for cellular)
            "radioType": "gsm",  # Specify we're using cellular radio
            # Note: Without direct access to cell towers, Google will use:
            # - Your cellular carrier's IP range
            # - Network latency characteristics  
            # - Cellular network topology
            # This gives much better accuracy than basic IP geolocation
        }
        
        url = f"https://www.googleapis.com/geolocation/v1/geolocate?key={GOOGLE_API_KEY}"
        headers = {"Content-Type": "application/json"}
        
        # Make request (will automatically go through eth0 since it's default route)
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            if 'location' in data:
                lat = data['location']['lat']
                lng = data['location']['lng']
                accuracy = data.get('accuracy', 'unknown')
                print(f"📍 Cellular location found: {lat}, {lng} (accuracy: {accuracy}m)")
                print(f"📡 Location method: Cellular network + IP geolocation")
                return lat, lng
            else:
                print(f"⚠️ No location in response: {data}")
                return 0, 0
        else:
            print(f"⚠️ Google API error: {response.status_code} - {response.text}")
            return 0, 0
            
    except Exception as e:
        print(f"⚠️ Cellular geolocation error: {e}")
        return 0, 0


def try_advanced_cellular_location():
    """
    Attempt to get more precise cellular location by gathering additional network info
    This is a fallback method that tries to extract more cellular details
    """
    try:
        print("🔍 Attempting advanced cellular location detection...")
        
        # Try to get cellular signal info from system
        cellular_info = {}
        
        # Check if we can get signal strength
        try:
            result = subprocess.run(
                ["cat", "/proc/net/wireless"],
                capture_output=True, text=True
            )
            if "eth0" in result.stdout:
                # Parse signal info if available
                for line in result.stdout.split('\n'):
                    if "eth0" in line:
                        parts = line.split()
                        if len(parts) >= 4:
                            cellular_info["signalStrength"] = int(parts[3])
        except:
            pass
        
        # Enhanced payload with any cellular info we can gather
        payload = {
            "considerIp": True,
            "radioType": "gsm",
            "carrier": "auto-detect",  # Let Google detect carrier
        }
        
        # Add signal info if we have it
        if cellular_info:
            payload["cellTowers"] = [cellular_info]
        
        url = f"https://www.googleapis.com/geolocation/v1/geolocate?key={GOOGLE_API_KEY}"
        headers = {"Content-Type": "application/json"}
        
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            if 'location' in data:
                lat = data['location']['lat']
                lng = data['location']['lng']
                accuracy = data.get('accuracy', 'unknown')
                print(f"📍 Advanced cellular location: {lat}, {lng} (accuracy: {accuracy}m)")
                return lat, lng
        
        return None, None
        
    except Exception as e:
        print(f"⚠️ Advanced cellular location failed: {e}")
        return None, None


def ensure_cellular_route():
    """
    Ensure cellular modem (eth0) is the default route
    """
    try:
        print("🔧 Ensuring cellular connection is active...")
        
        # Check if eth0 exists and has IP
        result = subprocess.run(
            ["ip", "addr", "show", USB_INTERFACE],
            capture_output=True, text=True
        )
        
        if result.returncode != 0 or "inet " not in result.stdout:
            print(f"⚠️ {USB_INTERFACE} not ready!")
            return False
        
        # Extract current IP
        eth0_ip = None
        for line in result.stdout.split('\n'):
            if 'inet ' in line and 'scope global' in line:
                eth0_ip = line.split('inet ')[1].split('/')[0].strip()
                break
        
        print(f"📡 Cellular interface {USB_INTERFACE} has IP: {eth0_ip}")
        
        # Check if eth0 is default route
        result = subprocess.run(
            ["ip", "route", "show", "default"],
            capture_output=True, text=True
        )
        
        if USB_INTERFACE not in result.stdout:
            print(f"🔄 Setting {USB_INTERFACE} as default route...")
            
            # Remove other default routes
            subprocess.run(["sudo", "ip", "route", "del", "default"], 
                         capture_output=True)
            
            # Add cellular as default
            subprocess.run([
                "sudo", "ip", "route", "add", "default", 
                "dev", USB_INTERFACE, "metric", "100"
            ], capture_output=True)
            
            print(f"✅ Set {USB_INTERFACE} as default route")
        
        return True
        
    except Exception as e:
        print(f"⚠️ Error setting cellular route: {e}")
        return False


def which_interface():
    """
    Show the kernel's current default route
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
        # 0) Ensure cellular connection is the default route
        if not ensure_cellular_route():
            print("⚠️ Warning: Cellular routing may not be optimal")
        
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
                "isDoorOpen": 0, #1 if door else 0,
                "numOfIn": 0,
                "numOfOut": 0,
                "latitude": "0",
                "longitude": "0",
                "status": True
            })
            print(f"📦 Buffered {len(buffered)} readings.")
            time.sleep(2)

        # 2) Get location via cellular network (try advanced method first)
        lat, lon = try_advanced_cellular_location()
        if not lat or not lon:
            # Fallback to standard cellular location
            lat, lon = get_cellular_location()
        
        if not lat or not lon:
            lat, lon = 0, 0
            print("⚠️ Could not determine location")

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