import RPi.GPIO as GPIO

IR_PIN = 9

def read_ir_door_status():
    try:
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(IR_PIN, GPIO.IN)

        state = GPIO.input(IR_PIN)
        print(f"🚪 IR Sensor: {'OPEN(HIGH)' if state else 'CLOSED(LOW)'}")
        return state == GPIO.HIGH
    except Exception as e:
        print(f"⚠️ Error reading IR sensor: {e}")
        return True
