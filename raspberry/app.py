import requests
import random
import time
import RPi.GPIO as GPIO
import Adafruit_DHT
from hx711 import HX711

# API Endpoint
API_URL = "http://mybees.aiiot.center/dashboard"

# GPIO Pin Configuration
TRIG = 14
ECHO = 15
DHT_PIN = 18
DHT_SENSOR = Adafruit_DHT.DHT22
SOUND_SENSOR_PIN = 23
LDR_PIN = 24  # GPIO pin for the LDR circuit

# Setup GPIO
def setup_gpio():
    print("Setting up GPIO pins...")
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(TRIG, GPIO.OUT)
    GPIO.setup(ECHO, GPIO.IN)
    GPIO.setup(SOUND_SENSOR_PIN, GPIO.IN)
    GPIO.setup(LDR_PIN, GPIO.IN)

# Cleanup GPIO
def cleanup_gpio():
    print("Cleaning up GPIO pins...")
    GPIO.cleanup()

# Ultrasonic Distance Sensor
def get_distance():
    try:
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
        return None

# Temperature and Humidity Sensor
def get_temp_humidity():
    try:
        # Generate random data as placeholder
        temperature = round(random.uniform(20, 30), 1)
        humidity = round(random.uniform(50, 70), 1)
        print(f"Temperature: {temperature} °C, Humidity: {humidity} %")
        return temperature, humidity
    except Exception as e:
        print(f"Error reading temperature and humidity: {e}")
        return None, None

# Sound Sensor
def monitor_sound():
    try:
        sound_detected = GPIO.input(SOUND_SENSOR_PIN) == GPIO.HIGH
        print(f"Sound sensor status: {'Detected' if sound_detected else 'Not Detected'}")
        return sound_detected
    except Exception as e:
        print(f"Error reading sound sensor: {e}")
        return False

# Light Sensor (LDR)
def monitor_light():
    try:
        light_detected = GPIO.input(LDR_PIN) == GPIO.HIGH
        print(f"Light sensor status: {'Detected' if light_detected else 'Not Detected'}")
        return light_detected
    except Exception as e:
        print(f"Error reading light sensor: {e}")
        return False

# HX711 Weight Sensor
def initialize_hx711():
    print("Initializing HX711 weight sensor...")
    try:
        hx = HX711(5, 6)
        hx.set_reading_format("MSB", "MSB")
        hx.set_reference_unit(114)  # Adjust based on your setup
        hx.reset()
        hx.tare()
        print("HX711 initialized successfully.")
        return hx
    except Exception as e:
        print(f"Error initializing HX711: {e}")
        return None

def get_weight(hx):
    try:
        weight = hx.get_weight(5)
        print(f"Weight sensor reading: {weight:.2f} grams")
        return weight
    except Exception as e:
        print(f"Error reading weight sensor: {e}")
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
    setup_gpio()
    hx = initialize_hx711()

    if not hx:
        print("Failed to initialize HX711. Exiting...")
        return

    try:
        while True:
            print("\nCollecting sensor data...")
            
            # Get sensor data
            temperature, humidity = get_temp_humidity()
            weight = get_weight(hx)
            distance = get_distance()
            sound_detected = monitor_sound()
            light_detected = monitor_light()

            # Prepare data payload
            data = {
                "temperature": temperature if temperature is not None else 0,
                "humidity": humidity if humidity is not None else 0,
                "weight": weight if weight is not None else 0,
                "distance": distance if distance is not None else 0,
                "sound_status": int(sound_detected),
                "light_status": int(light_detected),
            }

            # Send data to the server
            send_data_to_api(data)

            # Wait before the next reading
            time.sleep(10)

    except KeyboardInterrupt:
        print("Program terminated by user.")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        cleanup_gpio()

# Run the script
if __name__ == "__main__":
    main()
