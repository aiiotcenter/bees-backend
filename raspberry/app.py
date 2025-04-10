import requests
import time
import RPi.GPIO as GPIO
import Adafruit_DHT
from hx711 import HX711

# API Endpoint
API_URL = "http://bees-backend.aiiot.center/api/records"

# GPIO Pins
TRIG = 8
ECHO = 7
DHT_PIN = 23
DHT_SENSOR = Adafruit_DHT.DHT11
SOUND_SENSOR_PIN = 2
IR_SENSOR_IN = 17
IR_SENSOR_OUT = 27
IR_SENSOR_MID = 10  # Adjust based on your wiring

def setup_gpio():
    print("🔧 Setting up GPIO...")
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)

    # Distance sensor
    GPIO.setup(TRIG, GPIO.OUT)
    GPIO.setup(ECHO, GPIO.IN)

    # Sensors
    GPIO.setup(SOUND_SENSOR_PIN, GPIO.IN)
    GPIO.setup(IR_SENSOR_IN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(IR_SENSOR_OUT, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(IR_SENSOR_MID, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

def cleanup_gpio():
    print("🧼 Cleaning up GPIO...")
    GPIO.cleanup()

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
        return round(distance, 2)
    except Exception as e:
        print(f"⚠️ Error reading distance: {e}")
        return 0

def get_temp_humidity():
    try:
        humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
        if humidity is not None and temperature is not None:
            return round(temperature, 1), round(humidity, 1)
        else:
            return 0, 0
    except Exception as e:
        print(f"⚠️ Error reading DHT sensor: {e}")
        return 0, 0

def monitor_sound():
    try:
        return GPIO.input(SOUND_SENSOR_PIN) == GPIO.HIGH
    except Exception as e:
        print(f"⚠️ Error reading sound sensor: {e}")
        return False

def initialize_hx711():
    try:
        hx = HX711(16, 20)
        hx.set_reading_format("MSB", "MSB")
        hx.set_reference_unit(114)
        hx.reset()
        hx.tare()
        return hx
    except Exception as e:
        print(f"⚠️ Error initializing HX711: {e}")
        return None

def get_weight(hx):
    try:
        weight = hx.get_weight_mean(5)
        hx.power_down()
        time.sleep(0.1)
        hx.power_up()
        return round(weight, 2)
    except Exception as e:
        print(f"⚠️ Error reading weight: {e}")
        return 0

def detect_bee_movement():
    in_count = 0
    out_count = 0

    ir_in = GPIO.input(IR_SENSOR_IN)
    ir_out = GPIO.input(IR_SENSOR_OUT)
    ir_mid = GPIO.input(IR_SENSOR_MID)

    if ir_in == GPIO.LOW:
        print("📍 IR IN triggered")
        start_time = time.time()
        while time.time() - start_time < 1.5:
            if GPIO.input(IR_SENSOR_OUT) == GPIO.LOW:
                print("✅ Bee exited (IN ➡ OUT)")
                out_count += 1
                break
        else:
            print("⚠️ No OUT detection after IN")

    elif ir_out == GPIO.LOW:
        print("📍 IR OUT triggered")
        start_time = time.time()
        while time.time() - start_time < 1.5:
            if GPIO.input(IR_SENSOR_IN) == GPIO.LOW:
                print("✅ Bee entered (OUT ➡ IN)")
                in_count += 1
                break
        else:
            print("⚠️ No IN detection after OUT")

    elif ir_mid == GPIO.LOW:
        print("👀 Movement detected at MID sensor")

    else:
        print("🕵️ No IR activity detected")

    return in_count, out_count

def send_data_to_api(data):
    try:
        print(f"📤 Sending data: {data}")
        response = requests.post(API_URL, data=data)
        print(f"✅ Response: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"⚠️ Error sending data: {e}")

def main():
    setup_gpio()
    # hx = initialize_hx711()
    # if not hx:
    #     print("❌ Failed to init HX711")
    #     return
    hx = None  # Temporarily disabled

    try:
        while True:
            temperature, humidity = get_temp_humidity()
            sound = monitor_sound()
            weight = get_weight(hx) if hx else 0
            num_in, num_out = detect_bee_movement()

            data = {
                "hiveId": 1,
                "temperature": temperature,
                "humidity": humidity,
                "weight": weight,
                "distance": 0,  # You can add get_distance() if needed
                "soundStatus": int(sound),
                "isDoorOpen": 0,
                "numOfIn": num_in,
                "numOfOut": num_out
            }

            send_data_to_api(data)
            time.sleep(2)

    except KeyboardInterrupt:
        print("🛑 Program stopped by user.")
    finally:
        cleanup_gpio()

if __name__ == "__main__":
    main()
