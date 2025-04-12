import serial
import pynmea2
import requests

# Get GPS location (latitude and longitude)
def get_gps_location():
    try:
        port = serial.Serial("/dev/serial0", baudrate=9600, timeout=1)
        while True:
            print("Reading GPS data...")
            data = port.readline().decode("utf-8", errors="ignore").strip()
            print(f"Raw GPS data: {data}")
            if data.startswith("$GPGGA") or data.startswith("$GPRMC"):
                try:
                    msg = pynmea2.parse(data)
                    if hasattr(msg, 'latitude') and hasattr(msg, 'longitude'):
                        # Check for valid fix
                        if hasattr(msg, 'status') and msg.status == 'A':  # for GPRMC
                            print(f"✅ Valid fix (GPRMC)")
                            print(f"GPS Location: Latitude={msg.latitude}, Longitude={msg.longitude}")
                            return msg.latitude, msg.longitude
                        elif hasattr(msg, 'gps_qual') and int(msg.gps_qual) > 0:  # for GPGGA
                            print(f"✅ Valid fix (GPGGA)")
                            print(f"GPS Location: Latitude={msg.latitude}, Longitude={msg.longitude}")
                            return msg.latitude, msg.longitude
                        else:
                            print("❌ No fix yet, waiting...")
                except pynmea2.ParseError:
                    print("❌ NMEA Parse error")
    except Exception as e:
        print(f"Error reading GPS data: {e}")
        return None, None

# Send the location to your server
def send_location_to_api(latitude, longitude):
    try:
        data = {
            "latitude": latitude if latitude is not None else 0,
            "longitude": longitude if longitude is not None else 0
        }
        print(f"Sending GPS location: {data}")
        response = requests.post("http://mybees.aiiot.center/api/check-location/1", json=data)
        print(f"Location API Response: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error sending location: {e}")
