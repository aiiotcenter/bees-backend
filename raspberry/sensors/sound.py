import RPi.GPIO as GPIO

SOUND_PIN = 7

def monitor_sound():
    try:
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(SOUND_PIN, GPIO.IN)

        state = GPIO.input(SOUND_PIN)
        print(f"🎤 Sound Sensor: {'HIGH (Detected)' if state else 'LOW (No sound)'}")
        return state == GPIO.HIGH
    except Exception as e:
        print(f"⚠️ Error reading sound sensor: {e}")
        return False
