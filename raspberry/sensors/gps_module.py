
import serial
import pynmea2
import requests

LOCATION_API_URL = "http://bees-backend.aiiot.center/api/hives/check-location/1"

def parse_gps_data(nmea_sentence):
    try:
        msg = pynmea2.parse(nmea_sentence)
        if isinstance(msg, pynmea2.types.talker.GGA):
            return msg.latitude, msg.longitude
        elif isinstance(msg, pynmea2.types.talker.RMC) and msg.status == 'A':
            return msg.latitude, msg.longitude
    except pynmea2.ParseError as e:
        print(f"❌ Parse error: {e}")
    return None, None

def get_gps_location():
    try:
        ser = serial.Serial("/dev/serial0", baudrate=112500, timeout=1)
        for _ in range(10):
            data = ser.readline().decode("utf-8", errors="ignore").strip()
            print(f"📡 GPS Raw: {data}")
            if data.startswith("$GPGGA") or data.startswith("$GPRMC"):
                lat, lon = parse_gps_data(data)
                if lat and lon:
                    return lat, lon
    except Exception as e:
        print(f"⚠️ GPS read error: {e}")
    return None, None

def send_location_to_api(latitude, longitude):
    try:
        data = {
            "latitude": latitude if latitude else 0,
            "longitude": longitude if longitude else 0
        }
        print(f"📤 Sending GPS location: {data}")
        response = requests.post(LOCATION_API_URL, json=data)
        print(f"✅ Location API: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"⚠️ Error sending location: {e}")