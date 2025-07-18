import serial, time, requests
from gprs_manager import kill_ppp, start_gprs, is_up

GOOGLE_API_KEY = "AIzaSyCysMdMd_f01vX0vF6EOJtohcAe0YvtipY"
GEOLOC_URL     = f"https://www.googleapis.com/geolocation/v1/geolocate?key={GOOGLE_API_KEY}"
MCC, MNC       = 286, 2

def send_at(ser, cmd, delay=2):
    ser.write((cmd + "\r").encode())
    time.sleep(delay)
    return ser.read_all().decode(errors="ignore")

def parse_creg(resp):
    for line in resp.splitlines():
        if "+CREG:" in line:
            parts = [p.strip().strip('"') for p in line.split(",")]
            # parts = [<mode>,<stat>,<lac>,<cid>]
            if len(parts) >= 4 and parts[1] in ("1","5"):
                return parts[2], parts[3]
    return None, None

def get_cell_location_via_google(max_retries=5):
    # 1) free the serial port
    kill_ppp()

    # 2) open & configure UART
    ser = serial.Serial('/dev/serial0', baudrate=115200, timeout=2)
    time.sleep(2)

    # 3) loop until we get a usable LAC/CID
    lac = cid = None
    for i in range(max_retries):
        _ = send_at(ser, "AT+CREG=2", delay=2)
        raw = send_at(ser, "AT+CREG?", delay=2)
        lac, cid = parse_creg(raw)
        if lac and cid:
            break
        print(f"🔁 CREG parse failed (attempt {i+1}), retrying…")
        time.sleep(2)

    ser.close()

    if not lac or not cid:
        print("❌ Could not parse LAC/CID after retries.")
        # ensure we’re back on data link
        if not is_up():
            start_gprs()
        return None, None

    # 4) bring up GPRS so Google + backend will work
    if not is_up():
        start_gprs()

    # 5) query Google
    payload = {"cellTowers":[{"cellId":int(cid,16),
                               "locationAreaCode":int(lac,16),
                               "mobileCountryCode":MCC,
                               "mobileNetworkCode":MNC}]}
    try:
        r = requests.post(GEOLOC_URL, json=payload, timeout=10)
        loc = r.json().get("location",{})
        return loc.get("lat"), loc.get("lng")
    except Exception as e:
        print("❌ Google Geolocation API error:", e)
        return None, None
