import time
import sys
import RPi.GPIO as GPIO
from hx711v0_5_1 import HX711

# Set up GPIO mode
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)  # Disable warnings for pin conflicts

# Set DOUT and SCK GPIO pins
DOUT = 3  # BCM Pin 2 (GPIO 3)
SCK = 11  # BCM Pin 17 (GPIO 11)

# Create HX711 instance
hx = HX711(DOUT, SCK)

# Polling based reading
def getRawBytesAndPrintAll():
    rawBytes = hx.getRawBytes()
    longValue = hx.rawBytesToLong(rawBytes)
    longWithOffsetValue = hx.rawBytesToLongWithOffset(rawBytes)
    weightValue = hx.rawBytesToWeight(rawBytes)
    print(f"[INFO] POLLING_BASED | longValue: {longValue} | longWithOffsetValue: {longWithOffsetValue} | weight (grams): {weightValue}")

# Automatically set the offset and reference unit
hx.autosetOffset()
offsetValue = hx.getOffset()
print(f"[INFO] Finished automatically setting the offset. The new value is '{offsetValue}'.")

referenceUnit = 114
print(f"[INFO] Setting the 'referenceUnit' at {referenceUnit}.")
hx.setReferenceUnit(referenceUnit)

while True:
    try:
        getRawBytesAndPrintAll()
        time.sleep(1)  # Sleep for 1 second before the next read
    except (KeyboardInterrupt, SystemExit):
        GPIO.cleanup()
        print("[INFO] 'KeyboardInterrupt Exception' detected. Cleaning and exiting...")
        sys.exit()
