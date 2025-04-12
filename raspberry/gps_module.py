import serial
import pynmea2

def get_gps_location():
    try:
        port = serial.Serial("/dev/serial0", baudrate=9600, timeout=1)
        data = port.readline().decode("utf-8", errors="ignore").strip()
        print(f"📡 GPS Raw: {data}")
        if data.startswith("$GPGGA") or data.startswith("$GPRMC"):
            try:
                msg = pynmea2.parse(data)
                if hasattr(msg, 'status') and msg.status == 'A':  # GPRMC
                    return msg.latitude, msg.longitude
                elif hasattr(msg, 'gps_qual') and int(msg.gps_qual) > 0:  # GPGGA
                    return msg.latitude, msg.longitude
            except pynmea2.ParseError:
                print("❌ Parse error")
        return None, None
    except Exception as e:
        print(f"⚠️ GPS read error: {e}")
        return None, None

def send_location_to_api(latitude, longitude):
    import requests
    try:
        data = {
            "latitude": latitude if latitude is not None else 0,
            "longitude": longitude if longitude is not None else 0
        }
        print(f"📤 Sending GPS location: {data}")
        response = requests.post(
            "http://mybees.aiiot.center/api/check-location/1",
            json=data  # ✅ send as JSON
        )
        print(f"✅ Location API: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"⚠️ Error sending location: {e}")
