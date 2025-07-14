import serial
import time
import requests

# Absolute import of your GPRS manager
from gprs_manager import kill_ppp, start_gprs, is_up

GOOGLE_API_KEY = "AIzaSyCysMdMd_f01vX0vF6EOJtohcAe0YvtipY"
GEOLOC_URL     = (
    "https://www.googleapis.com/geolocation/v1/geolocate?key="
    + GOOGLE_API_KEY
)
MCC = 286  # Turkey
MNC = 2    # Vodafone

def send_at(ser, cmd, delay=2):
    """Send AT command and read all, with a longer default delay."""
    ser.write((cmd + "\r").encode())
    time.sleep(delay)
    return ser.read_all().decode(errors="ignore")

def parse_creg(resp):
    """Extract LAC/CID from a +CREG response."""
    for line in resp.splitlines():
        if "+CREG:" in line:
            parts = line.split(",")
            lac = parts[2].strip().strip('"')
            cid = parts[3].strip().strip('"')
            return lac, cid
    return None, None

def get_cell_location_via_google():
    """
    1) Kill any existing PPP so /dev/serial0 is free
    2) Read +CREG at a slower pace
    3) Always start GPRS afterwards (even on parse failure)
    4) Call Google Geolocation API
    """
    # Step 1: free the serial port
    kill_ppp()

    # Step 2: open the *hardware* UART
    ser = serial.Serial('/dev/serial0', baudrate=115200, timeout=2)
    time.sleep(2)                        # let the port settle

    # enable detailed CREG, then query it
    _ = send_at(ser, "AT+CREG=2", delay=2)
    raw = send_at(ser, "AT+CREG?", delay=2)
    ser.close()

    lac, cid = parse_creg(raw)
    if not lac or not cid:
        print("❌ Could not parse LAC/CID:", repr(raw))
        # still bring up GPRS so you regain Internet
        if not is_up():
            start_gprs()
        return None, None

    # Step 3: now that you have tower info, ensure data link is up
    if not is_up():
        start_gprs()

    # Step 4: query Google
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
