import requests
import time
import RPi.GPIO as GPIO
from sensors.gps_module import get_gps_location, send_location_to_api
from sensors.DHT import get_temp_humidity
from sensors.sound import monitor_sound
from sensors.ir import read_ir_door_status
from sensors.hx711py.weightsensor import tare, calibrate, load_calibration, get_weight, hx


# API Endpoint for sensor data
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
        response = requests.post(API_URL, data=data)
        print(f"✅ Sensor API Response: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"⚠️ Error sending sensor data: {e}")

def main():
    setup_gpio()
    
    #Initialize HX711 and tare the scale
    hx.reset()
    tare()
    
    # Load or calibrate the weight sensor
    cal_factor = load_calibration()
    if cal_factor is None:
        cal_factor = calibrate()
    else:
        print(f"[INFO] Using saved calibration factor: {cal_factor:.2f}")
    
    hx.set_reference_unit(cal_factor)

    try:
        while True:
            temperature, humidity = get_temp_humidity()
            #sound = monitor_sound()
            #door_open = read_ir_door_status()
            
            # Get weight reading
            #weight = get_weight()  
            #if weight is not None:
                #print(f"[WEIGHT] {weight:.2f} g")
            #else:
                #print("⚠️ Failed to read weight.")

            #hx.power_down()
            #hx.power_up()

            #latitude, longitude = get_gps_location()
            #if latitude is not None and longitude is not None:
            #    send_location_to_api(latitude, longitude)

            # Compose sensor data payload
            sensor_data = {
                "hiveId": 1,
                "temperature": temperature,
                "humidity": humidity,
                "weight": 0,#weight,
                "distance": 0,
                "soundStatus": 1,
                "isDoorOpen": 1, #int(door_open),
                "numOfIn": 0,
                "numOfOut": 0
            }

            send_data_to_api(sensor_data)
            print("🔄 Waiting for next cycle...\n")
            time.sleep(60)

    except KeyboardInterrupt:
        print("🛑 Program stopped by user.")
    finally:
        cleanup_gpio()

if __name__ == "__main__":
    main()
