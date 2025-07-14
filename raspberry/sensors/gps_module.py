# ~/bees-backend/raspberry/sensors/gps_module.py
import serial, time, requests
from ..gprs_manager import kill_ppp, start_gprs, is_up

GOOGLE_API_KEY    = "AIzaSyCysMdMd_f01vX0vF6EOJtohcAe0YvtipY"
GEOLOC_URL        = "https://www.googleapis.com/geolocation/v1/geolocate?key=" + GOOGLE_API_KEY
MCC = 286  # Turkey
MNC = 2    # Vodafone

def send_at(ser, cmd, delay=1):
    ser.write((cmd + "\r").encode())
    time.sleep(delay)
    return ser.read_all().decode(errors="ignore")

def parse_creg(resp):
    for line in resp.splitlines():
        if "+CREG:" in line:
            parts = line.split(",")
            return parts[2].strip().strip('"'), parts[3].strip().strip('"')
    return None, None

def get_cell_location_via_google():
    """
    1) Kill any existing PPP on /dev/ttyS0
    2) Open serial, get LAC/CID via AT+CREG?
    3) Start GPRS (pon) in background
    4) Call Google Geolocation API
    Returns (lat, lon) or (None, None) on failure.
    """
    kill_ppp()

    # 1. read tower info
    ser = serial.Serial('/dev/ttyS0', 115200, timeout=2)
    time.sleep(2)
    send_at(ser, "AT+CREG=2", delay=1)
    raw = send_at(ser, "AT+CREG?", delay=1)
    ser.close()

    lac, cid = parse_creg(raw)
    if not lac or not cid:
        print("❌ Could not parse LAC/CID:", repr(raw))
        return None, None

    # 2. bring up GPRS so we can reach Google
    if not is_up():
        start_gprs()

    # 3. call Google
    payload = {
        "cellTowers": [{
            "cellId": int(cid, 16),
            "locationAreaCode": int(lac, 16),
            "mobileCountryCode": MCC,
            "mobileNetworkCode": MNC
        }]
    }
    try:
        resp = requests.post(GEOLOC_URL, json=payload, timeout=10)
        data = resp.json()
        loc = data.get("location", {})
        return loc.get("lat"), loc.get("lng")
    except Exception as e:
        print("❌ Google Geolocation API error:", e)
        return None, None
