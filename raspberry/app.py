import requests
import RPi.GPIO as GPIO

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
        sensor_data = {
            "hiveId": 1,
            "temperature": 1,
            "humidity": 1,
            "weight": 0,
            "distance": 0,
            "soundStatus": 1,
            "isDoorOpen": 1,
            "numOfIn": 0,
            "numOfOut": 0
        }

        send_data_to_api(sensor_data)
        print("✅ Finished test run.")
    finally:
        cleanup_gpio()

if __name__ == "__main__":
    main()
