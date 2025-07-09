import requests
import time
import RPi.GPIO as GPIO
from sensors.DHT import get_temp_humidity
from sensors.sound import monitor_sound
from sensors.ir import read_ir_door_status
# from sensors.hx711py.weightsensor import tare, calibrate, load_calibration, get_weight, hx

API_URL = "http://bees-backend.aiiot.center/api/records"

def setup_gpio():
    print("🔧 Setting up GPIO...")
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(7, GPIO.IN)  # Sound sensor
    GPIO.setup(9, GPIO.IN)  # IR sensor

def cleanup_gpio():
    print("🧼 Cleaning up GPIO...")
    GPIO.cleanup()

def send_data_to_api(data):
    try:
        print(f"📤 Sending sensor data: {data}")
        response = requests.post(API_URL, data=data, timeout=5)
        print(f"✅ Sensor API Response: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"⚠️ Error sending sensor data: {e}")

def main():
    setup_gpio()
    try:
        # Read sensors
        temperature, humidity = get_temp_humidity()
        print(f"🌡️ Temp: {temperature} °C, 💧 Humidity: {humidity}%")

        sound = monitor_sound()
        print(f"🎧 Sound: {sound}")

        door_open = read_ir_door_status()
        print(f"🚪 Door: {'Open' if door_open else 'Closed'}")

        # Weight placeholder (optional to implement later)
        weight = 0
        # weight = get_weight()

        # Compose sensor data payload
        sensor_data = {
            "hiveId": 1,
            "temperature": temperature,
            "humidity": humidity,
            "weight": weight,
            "distance": 0,
            "soundStatus": sound,
            "isDoorOpen": int(door_open),
            "numOfIn": 0,
            "numOfOut": 0
        }

        send_data_to_api(sensor_data)
        print("✅ Finished test run.\n")

    finally:
        cleanup_gpio()

if __name__ == "__main__":
    main()
