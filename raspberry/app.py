#!/usr/bin/env python3
import time
import requests
import subprocess
import RPi.GPIO as GPIO
import json
import os
import sqlite3
from pathlib import Path

from datetime import datetime, timezone

from sensors.DHT import get_temp_humidity
from sensors.sound import monitor_sound
from sensors.ir import read_ir_door_status

# Configuration
API_URL      = "http://100.70.97.126:9602/api/records"
# API_URL      = "http://198.187.28.245/api/records"
API_HOST     = "bees-backend.aiiot.center"
MAX_READINGS = 3
READING_INTERVAL = 180  # 3 minutes in seconds

# Offline storage configuration
DATA_DIR = Path("/home/pi/beehive_data")  # Change path as needed
DB_PATH = DATA_DIR / "offline_data.db"
MAX_RETRY_ATTEMPTS = 3
RETRY_INTERVAL = 30  # seconds between retry attempts

# Google Geolocation API Key
GOOGLE_API_KEY = "AIzaSyCysMdMd_f01vX0vF6EOJtohcAe0YvtipY"
USB_INTERFACE = "eth1"  # ZTE WCDMA modem creates eth1 interface


def setup_offline_storage():
    """
    Setup the offline storage directory and database
    """
    try:
        # Create data directory if it doesn't exist
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        # Create database and tables
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Table for sensor readings
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sensor_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hive_id TEXT,
                temperature TEXT,
                humidity TEXT,
                weight REAL,
                distance REAL,
                sound_status INTEGER,
                is_door_open INTEGER,
                num_of_in INTEGER,
                num_of_out INTEGER,
                latitude TEXT,
                longitude TEXT,
                status BOOLEAN,
                recorded_at TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sent BOOLEAN DEFAULT FALSE,
                retry_count INTEGER DEFAULT 0
            )
        ''')
        
        # Table for status updates
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS status_updates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hive_id INTEGER,
                status BOOLEAN,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sent BOOLEAN DEFAULT FALSE,
                retry_count INTEGER DEFAULT 0
            )
        ''')
        
        # Table for location data
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS location_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                latitude REAL,
                longitude REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sent BOOLEAN DEFAULT FALSE,
                retry_count INTEGER DEFAULT 0
            )
        ''')
        
        conn.commit()
        conn.close()
        
        print("✅ Offline storage initialized successfully")
        return True
        
    except Exception as e:
        print(f"⚠️ Error setting up offline storage: {e}")
        return False


def save_sensor_reading_offline(reading):
    """
    Save sensor reading to local database
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO sensor_readings (
                hive_id, temperature, humidity, weight, distance, sound_status,
                is_door_open, num_of_in, num_of_out, latitude, longitude,
                status, recorded_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            reading["hiveId"], reading["temperature"], reading["humidity"],
            reading["weight"], reading["distance"], reading["soundStatus"],
            reading["isDoorOpen"], reading["numOfIn"], reading["numOfOut"],
            reading["latitude"], reading["longitude"], reading["status"],
            reading["recordedAt"]
        ))
        
        conn.commit()
        conn.close()
        
        print(f"💾 Sensor reading saved offline (ID: {cursor.lastrowid})")
        return True
        
    except Exception as e:
        print(f"⚠️ Error saving sensor reading offline: {e}")
        return False


def save_status_update_offline(hive_id, status):
    """
    Save status update to local database
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO status_updates (hive_id, status) VALUES (?, ?)
        ''', (hive_id, status))
        
        conn.commit()
        conn.close()
        
        print(f"💾 Status update saved offline (ID: {cursor.lastrowid})")
        return True
        
    except Exception as e:
        print(f"⚠️ Error saving status update offline: {e}")
        return False


def save_location_data_offline(latitude, longitude):
    """
    Save location data to local database
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO location_data (latitude, longitude) VALUES (?, ?)
        ''', (latitude, longitude))
        
        conn.commit()
        conn.close()
        
        print(f"💾 Location data saved offline (ID: {cursor.lastrowid})")
        return True
        
    except Exception as e:
        print(f"⚠️ Error saving location data offline: {e}")
        return False


def check_internet_connectivity():
    """
    Check if internet connection is available by trying to reach the API host
    """
    try:
        # Try a quick HTTP request to the API host
        response = requests.get(f"http://{API_HOST}", timeout=10)
        print("🌐 Internet connection: ✅ Available")
        return True
    except:
        try:
            # Fallback: try to ping Google DNS
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "3", "8.8.8.8"],
                capture_output=True
            )
            if result.returncode == 0:
                print("🌐 Internet connection: ✅ Available (via ping)")
                return True
        except:
            pass
    
    print("🌐 Internet connection: ❌ Not available")
    return False


def send_pending_data():
    """
    Send all pending data from the offline database
    """
    if not check_internet_connectivity():
        print("📡 No internet connection, skipping send attempt")
        return False
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        total_sent = 0
        
        # Send pending sensor readings
        cursor.execute('''
            SELECT * FROM sensor_readings 
            WHERE sent = FALSE AND retry_count < ? 
            ORDER BY created_at ASC
        ''', (MAX_RETRY_ATTEMPTS,))
        
        readings = cursor.fetchall()
        
        for row in readings:
            reading_id = row[0]
            reading_data = {
                "hiveId": row[1],
                "temperature": row[2],
                "humidity": row[3],
                "weight": row[4],
                "distance": row[5],
                "soundStatus": row[6],
                "isDoorOpen": row[7],
                "numOfIn": row[8],
                "numOfOut": row[9],
                "latitude": row[10],
                "longitude": row[11],
                "status": row[12],
                "recordedAt": row[13]
            }
            
            if send_data_direct(reading_data):
                # Mark as sent
                cursor.execute('''
                    UPDATE sensor_readings SET sent = TRUE WHERE id = ?
                ''', (reading_id,))
                total_sent += 1
                print(f"📤 Sent offline sensor reading (ID: {reading_id})")
            else:
                # Increment retry count
                cursor.execute('''
                    UPDATE sensor_readings SET retry_count = retry_count + 1 WHERE id = ?
                ''', (reading_id,))
                print(f"⚠️ Failed to send sensor reading (ID: {reading_id})")
        
        # Send pending status updates
        cursor.execute('''
            SELECT * FROM status_updates 
            WHERE sent = FALSE AND retry_count < ? 
            ORDER BY created_at ASC
        ''', (MAX_RETRY_ATTEMPTS,))
        
        status_updates = cursor.fetchall()
        
        for row in status_updates:
            update_id = row[0]
            hive_id = row[1]
            status = row[2]
            
            if send_status_update_direct(hive_id, status):
                cursor.execute('''
                    UPDATE status_updates SET sent = TRUE WHERE id = ?
                ''', (update_id,))
                total_sent += 1
                print(f"📤 Sent offline status update (ID: {update_id})")
            else:
                cursor.execute('''
                    UPDATE status_updates SET retry_count = retry_count + 1 WHERE id = ?
                ''', (update_id,))
                print(f"⚠️ Failed to send status update (ID: {update_id})")
        
        # Send pending location data
        cursor.execute('''
            SELECT * FROM location_data 
            WHERE sent = FALSE AND retry_count < ? 
            ORDER BY created_at ASC
        ''', (MAX_RETRY_ATTEMPTS,))
        
        locations = cursor.fetchall()
        
        for row in locations:
            location_id = row[0]
            latitude = row[1]
            longitude = row[2]
            
            if send_location_data_direct(latitude, longitude):
                cursor.execute('''
                    UPDATE location_data SET sent = TRUE WHERE id = ?
                ''', (location_id,))
                total_sent += 1
                print(f"📤 Sent offline location data (ID: {location_id})")
            else:
                cursor.execute('''
                    UPDATE location_data SET retry_count = retry_count + 1 WHERE id = ?
                ''', (location_id,))
                print(f"⚠️ Failed to send location data (ID: {location_id})")
        
        conn.commit()
        conn.close()
        
        if total_sent > 0:
            print(f"✅ Successfully sent {total_sent} pending records")
        
        return total_sent > 0
        
    except Exception as e:
        print(f"⚠️ Error sending pending data: {e}")
        return False


def cleanup_old_data():
    """
    Clean up old sent data and failed records that exceeded max retry attempts
    Keep data for 7 days for debugging purposes
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Delete sent records older than 7 days
        cursor.execute('''
            DELETE FROM sensor_readings 
            WHERE sent = TRUE AND created_at < datetime('now', '-7 days')
        ''')
        
        cursor.execute('''
            DELETE FROM status_updates 
            WHERE sent = TRUE AND created_at < datetime('now', '-7 days')
        ''')
        
        cursor.execute('''
            DELETE FROM location_data 
            WHERE sent = TRUE AND created_at < datetime('now', '-7 days')
        ''')
        
        # Delete failed records that exceeded max retries and are older than 1 day
        cursor.execute('''
            DELETE FROM sensor_readings 
            WHERE retry_count >= ? AND created_at < datetime('now', '-1 day')
        ''', (MAX_RETRY_ATTEMPTS,))
        
        cursor.execute('''
            DELETE FROM status_updates 
            WHERE retry_count >= ? AND created_at < datetime('now', '-1 day')
        ''', (MAX_RETRY_ATTEMPTS,))
        
        cursor.execute('''
            DELETE FROM location_data 
            WHERE retry_count >= ? AND created_at < datetime('now', '-1 day')
        ''', (MAX_RETRY_ATTEMPTS,))
        
        conn.commit()
        conn.close()
        
        print("🧹 Cleaned up old data")
        
    except Exception as e:
        print(f"⚠️ Error cleaning up old data: {e}")


def get_pending_count():
    """
    Get count of pending records
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                (SELECT COUNT(*) FROM sensor_readings WHERE sent = FALSE) as readings,
                (SELECT COUNT(*) FROM status_updates WHERE sent = FALSE) as status,
                (SELECT COUNT(*) FROM location_data WHERE sent = FALSE) as location
        ''')
        
        result = cursor.fetchone()
        conn.close()
        
        return {
            'readings': result[0],
            'status': result[1], 
            'location': result[2],
            'total': result[0] + result[1] + result[2]
        }
        
    except Exception as e:
        print(f"⚠️ Error getting pending count: {e}")
        return {'readings': 0, 'status': 0, 'location': 0, 'total': 0}


def send_status_update(hive_id: int, status: bool):
    """
    Send a status update (true/false) to the backend with offline support
    """
    # Try to send immediately if internet is available
    if check_internet_connectivity():
        if send_status_update_direct(hive_id, status):
            return True
    
    # Save offline if sending failed or no internet
    print(f"💾 Saving status update offline: hive_id={hive_id}, status={status}")
    return save_status_update_offline(hive_id, status)


def send_status_update_direct(hive_id: int, status: bool):
    """
    Direct API call to send status update (without offline handling)
    """
    status_url = f"http://100.70.97.126:9602/api/hives/status/{hive_id}"
    payload = {"status": status}
    route = which_interface()
    print(f"🛣️  Default route: {route} (sending hive status)")

    try:
        r = requests.put(status_url, json=payload, timeout=15)
        print(f"🔔 Status API→ {r.status_code} {r.text}")
        return r.status_code == 200
    except Exception as e:
        print(f"⚠️ send_status_update_direct error: {e}")
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
    """
    Send sensor data with offline support
    """
    # Try to send immediately if internet is available
    if check_internet_connectivity():
        if send_data_direct(entry):
            return True
    
    # Save offline if sending failed or no internet
    print(f"💾 Saving sensor data offline")
    return save_sensor_reading_offline(entry)


def send_data_direct(entry):
    """
    Direct API call to send sensor data (without offline handling)
    """
    route = which_interface()
    print(f"🛣️  Default route: {route}")
    try:
        r = requests.post(API_URL, json=entry, timeout=15)
        print(f"API→ {r.status_code} {r.text}")
        return r.status_code == 200
    except Exception as e:
        print(f"⚠️ send_data_direct error:", e)
        return False


def send_location_data(latitude, longitude):
    """
    Send location data with offline support
    """
    # Try to send immediately if internet is available
    if check_internet_connectivity():
        if send_location_data_direct(latitude, longitude):
            return True
    
    # Save offline if sending failed or no internet
    print(f"💾 Saving location data offline")
    return save_location_data_offline(latitude, longitude)


def send_location_data_direct(latitude, longitude):
    """
    Direct API call to send location data (without offline handling)
    """
    location_url = "http://100.70.97.126:9602/api/hives/check-location/1"
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
        print(f"⚠️ send_location_data_direct error:", e)
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
    print("🐝 Bee-Hive Monitor with Offline Support is ON.")
    
    # Initialize offline storage
    if not setup_offline_storage():
        print("⚠️ Failed to setup offline storage, continuing anyway...")
    
    # Send initial status = True to backend
    send_status_update(hive_id=1, status=True)

    try:
        # Ensure cellular connection is the default route
        if not ensure_cellular_route():
            print("⚠️ Warning: Cellular routing may not be optimal")
        
        cycle_count = 0
        
        while True:
            cycle_count += 1
            buffered = []
            print(f"\n🔄 Starting cycle #{cycle_count} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Check for pending data and try to send it
            pending = get_pending_count()
            if pending['total'] > 0:
                print(f"📦 Found {pending['total']} pending records (readings: {pending['readings']}, status: {pending['status']}, location: {pending['location']})")
                send_pending_data()
                
                # Clean up old data every 10 cycles
                if cycle_count % 10 == 0:
                    cleanup_old_data()
            
            # 1) Collect sensor readings every 3 minutes for 9 minutes total
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
                        "recordedAt": datetime.now(timezone.utc).isoformat(timespec='milliseconds')
                    })
                
                # Wait 3 minutes before next reading (except for the last reading)
                if reading_num < MAX_READINGS - 1:
                    print(f"⏱️  Waiting {READING_INTERVAL} seconds until next reading...")
                    time.sleep(READING_INTERVAL)

            # 2) Get location once per cycle
            print(f"\n🌍 Getting location after {MAX_READINGS} readings...")
            lat, lon = try_advanced_cellular_location()
            if not lat or not lon:
                # Fallback to standard cellular location
                lat, lon = get_cellular_location()
            
            if not lat or not lon:
                lat, lon = 0, 0
                print("⚠️ Could not determine location, using default (0, 0)")
            else:
                print(f"✅ Location acquired: {lat}, {lon}")
                
                # Send location data to the location endpoint
                print(f"📍 Sending location data to location endpoint...")
                location_sent = send_location_data(lat, lon)
                if location_sent:
                    print("✅ Location data sent successfully")
                else:
                    print("⚠️ Location data saved offline for later transmission")

            # 3) Send all buffered data with the same coordinates
            print(f"\n📤 Sending {len(buffered)} readings to server...")
            for i, entry in enumerate(buffered, 1):
                entry["latitude"] = str(lat)
                entry["longitude"] = str(lon)
                print(f"📤 Sending reading {i}/{len(buffered)}: {entry}")
                send_data(entry)
                time.sleep(2)  # Small delay between API calls

            print(f"✅ Completed cycle #{cycle_count} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Show pending data summary
            pending = get_pending_count()
            if pending['total'] > 0:
                print(f"📊 Pending records: {pending['total']} (will retry next cycle)")
            
            print("="*50)

    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user.")
        # Try to send any remaining data before exit
        print("📤 Attempting to send pending data before exit...")
        send_pending_data()
    except Exception as e:
        print(f"⚠️ Unexpected error in main loop: {e}")
        # Save error state offline if needed
        save_status_update_offline(1, False)
    finally:
        cleanup_gpio()
        print("🐝 Bee-Hive Monitor shutdown complete.")


if __name__ == "__main__":
    main()