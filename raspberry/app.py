
import requests
import time
import RPi.GPIO as GPIO
import Adafruit_DHT
from hx711 import HX711

# API Endpoint
API_URL = "http://bees-backend.aiiot.center/api/records"

# GPIO Pin Configuration
TRIG = 8
ECHO = 7
DHT_PIN = 23
DHT_SENSOR = Adafruit_DHT.DHT11
SOUND_SENSOR_PIN = 2
IR_SENSOR_IN = 17
IR_SENSOR_OUT = 27

# Setup GPIO
def setup_gpio():
    print("Setting up GPIO pins...")
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(TRIG, GPIO.OUT)
    GPIO.setup(ECHO, GPIO.IN)
    GPIO.setup(SOUND_SENSOR_PIN, GPIO.IN)
    GPIO.setup(IR_SENSOR_IN, GPIO.IN)
    GPIO.setup(IR_SENSOR_OUT, GPIO.IN)

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
        distance = (elapsed_time * 34300) / 2
        return distance
    except Exception as e:
        print(f"Error reading distance sensor: {e}")
        return 0

# Temperature and Humidity
def get_temp_humidity():
    try:
        humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
        if humidity is not None and temperature is not None:
            return round(temperature, 1), round(humidity, 1)
        else:
            return 0, 0
    except Exception as e:
        print(f"Error reading DHT sensor: {e}")
        return 0, 0

# Sound Sensor
def monitor_sound():
    try:
        return GPIO.input(SOUND_SENSOR_PIN) == GPIO.HIGH
    except Exception as e:
        print(f"Error reading sound sensor: {e}")
        return False

# Weight Sensor (HX711)
def initialize_hx711():
    try:
        hx = HX711(16, 20)
        hx.set_reading_format("MSB", "MSB")
        hx.set_reference_unit(114)
        hx.reset()
        hx.tare()
        return hx
    except Exception as e:
        print(f"Error initializing HX711: {e}")
        return None

def get_weight(hx):
    try:
        weight = hx.get_weight_mean(5)
        hx.power_down()
        time.sleep(0.1)
        hx.power_up()
        return weight
    except Exception as e:
        print(f"Error reading weight: {e}")
        return 0

# Bee Movement Detection
def detect_bee_movement():
    in_count = 0
    out_count = 0

    if GPIO.input(IR_SENSOR_IN) == GPIO.LOW:
        start_time = time.time()
        while time.time() - start_time < 0.5:
            if GPIO.input(IR_SENSOR_OUT) == GPIO.LOW:
                print("🐝 Bee exited")
                out_count += 1
                break

    elif GPIO.input(IR_SENSOR_OUT) == GPIO.LOW:
        start_time = time.time()
        while time.time() - start_time < 0.5:
            if GPIO.input(IR_SENSOR_IN) == GPIO.LOW:
                print("🐝 Bee entered")
                in_count += 1
                break

    return in_count, out_count

# Send data to API
def send_data_to_api(data):
    try:
        print(f"Sending data: {data}")
        response = requests.post(API_URL, data=data)
        print(f"Response: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error sending data: {e}")


    
def main():
    # hx = initialize_hx711()
    # if not hx:
    #     print("❌ Failed to initialize HX711. Exiting...")
    #     return

    setup_gpio()
    hx = initialize_hx711()
    if not hx:
        print("Failed to initialize HX711")
        return

    try:
        while True:
            temperature, humidity = get_temp_humidity()
            weight = get_weight(hx)
            sound_detected = monitor_sound()
            num_in, num_out = detect_bee_movement()

            data = {
                "hiveId": 1,
                "temperature": temperature,
                "humidity": humidity,
                "weight": weight,
                "distance": 0,  # Optional: get_distance() if needed
                "soundStatus": int(sound_detected),
                "isDoorOpen": 0,
                "numOfIn": num_in,
                "numOfOut": num_out
            }

            send_data_to_api(data)
            time.sleep(2)

    except KeyboardInterrupt:
        print("Program stopped by user.")
    finally:
        cleanup_gpio()

if __name__ == "__main__":
    main()
