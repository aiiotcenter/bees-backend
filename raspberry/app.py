import requests
import time
import RPi.GPIO as GPIO
import Adafruit_DHT
from hx711 import HX711
# from gps_module import get_gps_location, send_location_to_api

# API Endpoint
API_URL = "http://bees-backend.aiiot.center/api/records" 

# GPIO Pin Configuration
TRIG = 8
ECHO = 7
DHT_PIN = 23
DHT_SENSOR = Adafruit_DHT.DHT11
SOUND_SENSOR_PIN = 2

# Setup GPIO
def setup_gpio():
    print("Setting up GPIO pins...")
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(TRIG, GPIO.OUT)
    GPIO.setup(ECHO, GPIO.IN)
    GPIO.setup(SOUND_SENSOR_PIN, GPIO.IN)

# Cleanup GPIO
def cleanup_gpio():
    print("Cleaning up GPIO pins...")
    GPIO.cleanup()

# Ultrasonic Distance Sensor
def get_distance():
    try:
        print("Reading distance sensor...")
        GPIO.output(TRIG, True)
        time.sleep(0.00001)
        GPIO.output(TRIG, False)

        start_time = time.time()
        while GPIO.input(ECHO) == 0:
            start_time = time.time()

        while GPIO.input(ECHO) == 1:
            end_time = time.time()

        elapsed_time = end_time - start_time
        distance = (elapsed_time * 34300) / 2  # Distance in cm
        print(f"Distance sensor reading: {distance:.2f} cm")
        return distance
    except Exception as e:
        print(f"Error reading distance sensor: {e}")
        return 0

# Temperature and Humidity Sensor
def get_temp_humidity():
    try:
        print("Reading temperature and humidity...")
        humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
        print(f"Raw DHT sensor data: Humidity={humidity}, Temperature={temperature}")
        if humidity is not None and temperature is not None:
            temperature = round(temperature, 1)
            humidity = round(humidity, 1)
            print(f"Temperature: {temperature} °C, Humidity: {humidity} %")
            return temperature, humidity
        else:
            print("Failed to get reading from DHT sensor.")
            return 0, 0
    except Exception as e:
        print(f"Error reading temperature and humidity: {e}")
        return 0, 0


# Sound Sensor
def monitor_sound():
    try:
        print("Reading sound sensor...")
        sound_detected = GPIO.input(SOUND_SENSOR_PIN) == GPIO.HIGH
        print(f"Sound sensor status: {'Detected' if sound_detected else 'Not Detected'}")
        return sound_detected
    except Exception as e:
        print(f"Error reading sound sensor: {e}")
        return False




def initialize_hx711():
    print("🔧 Initializing HX711 weight sensor...")
    try:
        hx = HX711(16, 20)

        hx.set_reading_format("MSB", "MSB")
        print("✅ Reading format set to MSB.")
        
        hx.set_reference_unit(114)  # Adjust based on calibration
        print("✅ Reference unit set to 114.")

        print("🔄 Resetting HX711...")
        hx.reset()

        print("⚖️ Performing tare (zeroing)...")
        hx.tare()
        print("✅ Tare complete. Ready to weigh.")
        return hx
    except Exception as e:
        print(f"❌ Error initializing HX711: {e}")
        return None


def get_weight(hx):
    try:
        print("📥 Reading weight...")
        raw = hx.get_raw_data_mean()
        print(f"📊 Raw data mean: {raw}")

        weight = hx.get_weight_mean(5)
        print(f"⚖️ Averaged weight over 5 readings: {weight:.2f} grams")

        hx.power_down()
        time.sleep(0.1)
        hx.power_up()

        return weight
    except Exception as e:
        print(f"❌ Error reading weight sensor: {e}")
        return None


# Send Data to API
def send_data_to_api(data):
    try:
        print(f"Sending data to API: {data}")
        response = requests.post(API_URL, data=data)
        print(f"Request Method: POST")
        print(f"Request URL: {response.request.url}")
        print(f"Request Headers: {response.request.headers}")
        print(f"Request Body: {response.request.body}")
        print(f"API Response: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error sending data to API: {e}")

def main():
    # hx = initialize_hx711()
    # if not hx:
    #     print("❌ Failed to initialize HX711. Exiting...")
    #     return

    try:
        while True:
            print("\nCollecting sensor data...")

            temperature, humidity = get_temp_humidity()
            # weight = get_weight(hx)  # 💬 Temporarily commented out
            weight = 0  # ➕ Default value for now

            sound_detected = monitor_sound()

            data = {
                "hiveId": 1,
                "temperature": temperature if temperature is not None else 0,
                "humidity": humidity if humidity is not None else 0,
                "weight": weight,
                "distance": 0,
                "soundStatus": int(sound_detected),
                "isDoorOpen": 0,
                "numOfIn": 0,
                "numOfOut": 0,
            }

            print(f"📦 Data payload: {data}")
            send_data_to_api(data)
            time.sleep(2)

    except KeyboardInterrupt:
        print("🛑 Program terminated by user.")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        cleanup_gpio()


# Run the script
if __name__ == "__main__":
    main()
