import RPi.GPIO as GPIO
IR_PIN = 9  

def read_ir_door_status():
    try:
        state = GPIO.input(IR_SENSOR)
        print(f"🚪 IR Sensor: {'OPEN(HIGH)' if state else 'CLOSED(LOW)'}")
        return state == GPIO.HIGH
    except Exception as e:
        print(f"⚠️ Error reading IR sensor: {e}")
        return True  # Assume open if error 