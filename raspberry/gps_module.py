import serial
import pynmea2
import requests

# Get GPS location (latitude and longitude)
def get_gps_location():
    try:
        port = serial.Serial("/dev/serial0", baudrate=9600, timeout=1)
        while True:
            data = port.readline().decode("utf-8", errors="ignore")
            if data.startswith("$GPGGA") or data.startswith("$GPRMC"):
                msg = pynmea2.parse(data)
                if hasattr(msg, 'latitude') and hasattr(msg, 'longitude'):
                    lat = msg.latitude
                    lon = msg.longitude
                    print(f"GPS Location: Latitude={lat}, Longitude={lon}")
                    return lat, lon
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
        response = requests.post("http://mybees.aiiot.center/api/check-location/1", data=data)
        print(f"Location API Response: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error sending location: {e}")
