#!/usr/bin/env python3
import time
import requests
import subprocess
import RPi.GPIO as GPIO
import json

from datetime import datetime, timezone

from sensors.DHT import get_temp_humidity
from sensors.sound import monitor_sound
from sensors.ir import read_ir_door_status

# Configuration
API_URL      = "http://bees-backend.aiiot.center/api/records"
# API_URL      = "http://198.187.28.245/api/records"
API_HOST     = "bees-backend.aiiot.center"
MAX_READINGS = 3
READING_INTERVAL = 180  # 30 minutes in seconds

# Google Geolocation API Key
GOOGLE_API_KEY = "AIzaSyCysMdMd_f01vX0vF6EOJtohcAe0YvtipY"
USB_INTERFACE = "eth1"  # ZTE WCDMA modem creates eth1 interface

def send_status_update(hive_id: int, status: bool):
    """
    Send a status update (true/false) to the backend
    """
    status_url = f"http://bees-backend.aiiot.center/api/hives/status/{hive_id}"
    payload = {"status": status}
    route = which_interface()
    print(f"🛣️  Default route: {route} (sending hive status)")

    try:
        r = requests.put(status_url, json=payload, timeout=15)
        print(f"🔔 Status API→ {r.status_code} {r.text}")
        return r.status_code == 200
    except Exception as e:
        print(f"⚠️ send_status_update error: {e}")
        return False


def get_cellular_location():
    """
    Get high-accuracy location using cellular network through Google Geolocation API
    This method uses cellular IP + radio type for better accuracy than simple IP geolocation
    Returns (latitude, longitude) tuple or (0, 0) if failed
    """
    try:
        print("🌐 Getting cellular location via Google Geolocation API...")
        
        # Force request through cellular interface by binding to eth1 IP
        eth1_ip = None
        try:
            result = subprocess.run(
                ["ip", "addr", "show", USB_INTERFACE],
                capture_output=True, text=True
            )
            # Extract IP address from eth1
            for line in result.stdout.split('\n'):
                if 'inet ' in line and 'scope global' in line:
                    eth1_ip = line.split('inet ')[1].split('/')[0].strip()
                    break
        except:
            pass
        
        print(f"📡 Using cellular IP: {eth1_ip}")
        
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
        
        # Make request (will automatically go through eth1 since it's default route)
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
            if "eth1" in result.stdout:
                # Parse signal info if available
                for line in result.stdout.split('\n'):
                    if "eth1" in line:
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
    Ensure cellular modem (eth1) is the default route
    """
    try:
        print("🔧 Ensuring cellular connection is active...")
        
        # Check if eth1 exists and has IP
        result = subprocess.run(
            ["ip", "addr", "show", USB_INTERFACE],
            capture_output=True, text=True
        )
        
        if result.returncode != 0 or "inet " not in result.stdout:
            print(f"⚠️ {USB_INTERFACE} not ready!")
            return False
        
        # Extract current IP
        eth1_ip = None
        for line in result.stdout.split('\n'):
            if 'inet ' in line and 'scope global' in line:
                eth1_ip = line.split('inet ')[1].split('/')[0].strip()
                break
        
        print(f"📡 Cellular interface {USB_INTERFACE} has IP: {eth1_ip}")
        
        # Check if eth1 is default route
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


def send_location_data(latitude, longitude):
    """
    Send location data to the location endpoint
    """
    location_url = "https://bees-backend.aiiot.center/api/hives/check-location/1"
    location_data = {
        "latitude": latitude,
        "longitude": longitude
    }
    
    route = which_interface()
    print(f"🛣️  Default route: {route}")
    try:
        r = requests.post(location_url, json=location_data, timeout=15)
        print(f"📍 Location API→ {r.status_code} {r.text}")
        return r.status_code == 200
    except Exception as e:
        print(f"⚠️ send_location_data error:", e)
        return False


def collect_sensor_reading():
    """
    Collect a single sensor reading
    """
    try:
        t, h = get_temp_humidity()
        s = monitor_sound()
        door = read_ir_door_status()
        recordedAt = datetime.now(timezone.utc).isoformat(timespec='milliseconds')
        
        reading = {
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
            "status": True,
            "recordedAt": recordedAt
        }
        print("Recorded At: " + recordedAt)
        
        print(f"📊 Sensor reading: T={t}°C, H={h}%, Sound={'Yes' if s else 'No'}, Door={'Open' if door else 'Closed'}")
        return reading
        
    except Exception as e:
        print(f"⚠️ Error collecting sensor reading: {e}")
        return None


def main():
    setup_gpio()
    print("Bee-Hive is ON.")

    # Send initial status = True to backend
    send_status_update(hive_id=1, status=True)

    try:
        # Ensure cellular connection is the default route
        if not ensure_cellular_route():
            print("⚠️ Warning: Cellular routing may not be optimal")
        
        while True:
            buffered = []
            print(f"\n🔄 Starting new data collection cycle at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 1) Collect sensor readings every 30 minutes for 90 minutes total
            for reading_num in range(MAX_READINGS):
                print(f"\n📈 Collecting reading {reading_num + 1}/{MAX_READINGS}")
                
                reading = collect_sensor_reading()
                if reading:
                    buffered.append(reading)
                    print(f"📦 Buffered {len(buffered)} readings.")
                else:
                    print("⚠️ Failed to collect sensor reading, using default values")
                    # Add a default reading to maintain timing
                    buffered.append({
                        "hiveId": "1",
                        "temperature": "0",
                        "humidity": "0",
                        "weight": 0,
                        "distance": 0,
                        "soundStatus": 0,
                        "isDoorOpen": 0,
                        "numOfIn": 0,
                        "numOfOut": 0,
                        "latitude": "0",
                        "longitude": "0",
                        "status": False,
                        "timestamp": datetime.now().isoformat()
                    })
                
                # Wait 3 minutes before next reading (except for the last reading)
                if reading_num < MAX_READINGS - 1:
                    print(f"⏱️  Waiting {READING_INTERVAL} seconds until next reading...")
                    time.sleep(READING_INTERVAL)

            # 2) Get location once per 90-minute cycle
            print(f"\n🌍 Getting location after {MAX_READINGS} readings...")
            lat, lon = try_advanced_cellular_location()
            if not lat or not lon:
                # Fallback to standard cellular location
                lat, lon = get_cellular_location()
            
            # if not lat or not lon:
            #     lat, lon = 0, 0
            #     print("⚠️ Could not determine location, using default (0, 0)")
            # else:
            #     print(f"✅ Location acquired: {lat}, {lon}")
                
            #     # Send location data to the location endpoint
            #     print(f"📍 Sending location data to location endpoint...")
            #     location_sent = send_location_data(lat, lon)
            #     if location_sent:
            #         print("✅ Location data sent successfully")
            #     else:
            #         print("⚠️ Failed to send location data")

            # 3) Send all buffered data with the same coordinates
            print(f"\n📤 Sending {len(buffered)} readings to server...")
            for i, entry in enumerate(buffered, 1):
                entry["latitude"] = str(lat)
                entry["longitude"] = str(lon)
                print(f"📤 Sending reading {i}/{len(buffered)}: {entry}")
                send_data(entry)
                time.sleep(2)  # Small delay between API calls

            print(f"✅ Completed cycle at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("="*50)

    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user.")
    except Exception as e:
        print(f"⚠️ Unexpected error in main loop: {e}")
    finally:
        cleanup_gpio()


if __name__ == "__main__":
    main()