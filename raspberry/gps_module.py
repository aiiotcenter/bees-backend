import serial
import pynmea2
import requests

def parse_gps_data(nmea_sentence):
    try:
        msg = pynmea2.parse(nmea_sentence)

        if isinstance(msg, pynmea2.types.talker.GGA):  # GGA sentence
            latitude = msg.latitude
            longitude = msg.longitude
            altitude = msg.altitude
            hdop = msg.horizontal_dil
            satellites = msg.num_sats
            utc_time = msg.timestamp

            print(f"UTC Time: {utc_time}, Latitude: {latitude}, Longitude: {longitude}")
            print(f"Altitude: {altitude} m, HDOP: {hdop}, Satellites: {satellites}")
            print("--------------------------------------------------------------------")

            if latitude and longitude:
                return latitude, longitude

        elif isinstance(msg, pynmea2.types.talker.RMC):  # RMC sentence
            latitude = msg.latitude
            longitude = msg.longitude
            speed = msg.spd_over_grnd
            date = msg.datestamp
            time = msg.timestamp

            print(f"Date: {date}, Time: {time}")
            if speed:
                speed_kmh = float(speed) * 1.852
                print(f"Speed: {speed_kmh:.2f} km/h")

            if msg.status == 'A':  # Data valid
                return latitude, longitude

    except pynmea2.ParseError as e:
        print(f"❌ Parse error: {e}")
    return None, None

def get_gps_location():
    try:
        ser = serial.Serial("/dev/serial0", baudrate=9600, timeout=1)

        for _ in range(10):  # Try reading 10 lines max
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
        response = requests.post(
            "http://mybees.aiiot.center/api/check-location/1",
            json=data
        )
        print(f"✅ Location API: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"⚠️ Error sending location: {e}")

if __name__ == "__main__":
    lat, lon = get_gps_location()
    if lat and lon:
        send_location_to_api(lat, lon)
    else:
        print("⚠️ No valid GPS fix")
