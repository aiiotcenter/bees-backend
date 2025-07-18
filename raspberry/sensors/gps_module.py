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

def get_cell_location_via_google(max_retries=8, delay_between=3):
    kill_ppp()
    ser = serial.Serial('/dev/serial0', baudrate=115200, timeout=2)
    time.sleep(3)

    lac, cid = None, None
    for i in range(max_retries):
        _ = send_at(ser, "AT+CREG=2", delay=2)
        raw = send_at(ser, "AT+CREG?", delay=2)
        lac, cid = parse_creg(raw)
        if lac and cid:
            break
        print(f"🔁 [GPS] CREG parse failed (attempt {i+1}/{max_retries}), retrying…")
        time.sleep(delay_between)

    ser.close()
    if not (lac and cid):
        print("❌ [GPS] Could not parse LAC/CID after retries.")
        if not is_up():
            start_gprs()
        return None, None

    # bring up GPRS so Google + backend will work
    if not is_up():
        start_gprs()

    # query Google
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
