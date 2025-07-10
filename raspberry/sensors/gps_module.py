import serial
import time
import requests

GOOGLE_API_KEY = "AIzaSyCysMdMd_f01vX0vF6EOJtohcAe0YvtipY"
LOCATION_API_URL = "http://bees-backend.aiiot.center/api/hives/check-location/1"

MCC = 286  # Turkey
MNC = 2    # Vodafone

def send_at_command(ser, command, delay=1):
    ser.write((command + "\r").encode())
    time.sleep(delay)
    return ser.read_all().decode(errors="ignore")

def parse_creg(response):
    try:
        for line in response.split('\n'):
            if "+CREG:" in line:
                parts = line.split(",")
                lac = parts[2].replace('"', '').strip()
                cid = parts[3].replace('"', '').strip()
                return lac, cid
    except Exception as e:
        print("❌ Parse error:", e)
    return None, None

def get_gsm_location():
    try:
        ser = serial.Serial('/dev/ttyS0', baudrate=115200, timeout=2)
        time.sleep(2)

        # Enable detailed network info
        send_at_command(ser, "AT+CREG=2")
        time.sleep(1)

        # Request registration info
        ser.write(b"AT+CREG?\r")
        time.sleep(1)
        response = ser.read_all().decode(errors="ignore")
        print("📶 CREG Response:", repr(response))

        lac, cid = parse_creg(response)
        if lac and cid:
            print(f"✅ LAC: {lac}, CID: {cid}")
            return query_google_geolocation_api(lac, cid)
        else:
            print("❌ Could not extract LAC/CID.")
    except Exception as e:
        print("⚠️ GSM error:", e)
    return None, None

def query_google_geolocation_api(lac, cid):
    try:
        url = f"https://www.googleapis.com/geolocation/v1/geolocate?key={GOOGLE_API_KEY}"
        payload = {
            "cellTowers": [{
                "cellId": int(cid, 16),
                "locationAreaCode": int(lac, 16),
                "mobileCountryCode": MCC,
                "mobileNetworkCode": MNC
            }]
        }
        print("📡 Querying Google Geolocation API...")
        res = requests.post(url, json=payload)
        data = res.json()
        if "location" in data:
            lat = data["location"]["lat"]
            lon = data["location"]["lng"]
            print(f"🌍 Location from Google: {lat}, {lon}")
            return lat, lon
        else:
            print("❌ Google API response:", data)
    except Exception as e:
        print("❌ Google API Error:", e)
    return None, None

def send_location_to_api(latitude, longitude):
    try:
        payload = {
            "latitude": latitude,
            "longitude": longitude
        }
        print(f"📤 Sending to server: {payload}")
        response = requests.post(LOCATION_API_URL, json=payload)
        print(f"✅ Server Response: {response.status_code} - {response.text}")
    except Exception as e:
        print("⚠️ Failed to send to server:", e)

if __name__ == "__main__":
    lat, lon = get_gsm_location()
    if lat and lon:
        send_location_to_api(lat, lon)
    else:
        print("⚠️ No location found via GSM.")
