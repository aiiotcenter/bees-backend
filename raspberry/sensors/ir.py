import RPi.GPIO as GPIO

IR_SENSOR = 9

def read_ir_door_status():
    try:
        state = GPIO.input(IR_SENSOR)
        print(f"🚪 IR Sensor: {'CLOSED (LOW)' if state else 'OPEN (HIGH)'}")
        return state == GPIO.HIGH
    except Exception as e:
        print(f"⚠️ Error reading IR sensor: {e}")
        return True  # Assume open if error