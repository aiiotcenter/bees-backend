import requests
import time
import RPi.GPIO as GPIO
import logging
from sensors.gps_module import get_gps_location, send_location_to_api
from sensors.DHT import get_temp_humidity
from sensors.sound import monitor_sound
from sensors.ir import read_ir_door_status
from sensors.weight_sensor import initialize_hx711, get_weight

# API Endpoint for sensor data
API_URL = "http://bees-backend.aiiot.center/api/records"

# Set up logging
logging.basicConfig(level=logging.DEBUG)

def setup_gpio():
    logging.debug("🔧 Setting up GPIO...")
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    
    # Setup GPIO pins for sensors
    GPIO.setup(7, GPIO.IN)  # Sound sensor
    GPIO.setup(9, GPIO.IN)  # IR sensor

def cleanup_gpio():
    logging.debug("🧼 Cleaning up GPIO...")
    GPIO.cleanup()

def send_data_to_api(data, timeout=10):
    try:
        logging.debug(f"📤 Sending sensor data: {data}")
        response = requests.post(API_URL, data=data, timeout=timeout)  # Timeout after 10 seconds
        logging.debug(f"✅ Sensor API Response: {response.status_code} - {response.text}")
    except requests.exceptions.Timeout:
        logging.warning("⚠️ Timeout: API request took too long")
    except Exception as e:
        logging.error(f"⚠️ Error sending sensor data: {e}")

def main():
    setup_gpio()
    hx = initialize_hx711()
    logging.debug("📡 Starting sensor data collection...")

    try:
        while True:
            start_time = time.time()
            
            # Collect sensor data
            temperature, humidity = get_temp_humidity()
            sound = monitor_sound()
            door_open = read_ir_door_status()
            weight = get_weight(hx, 10) if hx else 0

            # Get GPS location (with timeout)
            latitude, longitude = get_gps_location(timeout=10)
            if latitude is not None and longitude is not None:
                send_location_to_api(latitude, longitude)

            # Prepare sensor data for API
            sensor_data = {
                "hiveId": 1,
                "temperature": temperature,
                "humidity": humidity,
                "weight": weight,
                "distance": 0,
                "soundStatus": int(sound),
                "isDoorOpen": int(door_open),
                "numOfIn": 0,
                "numOfOut": 0
            }

            # Send the data to API
            send_data_to_api(sensor_data)

            logging.debug("🔄 Waiting for next cycle...\n")

            # Timeout for each cycle (avoid hanging indefinitely)
            if time.time() - start_time > 30:  # 30 seconds per cycle max
                logging.warning("⚠️ Timeout: Cycle took too long!")
                break

            time.sleep(20)  # Wait for the next cycle

    except KeyboardInterrupt:
        logging.info("🛑 Program stopped by user.")
    finally:
        cleanup_gpio()

if __name__ == "__main__":
    main()
