import time
import sys
import RPi.GPIO as GPIO
from hx711py.hx711 import HX711  # Corrected import to reflect your folder structure

# Pin configuration (adjust if using different GPIOs)
DT = 3    # HX711 Data pin (DOUT)
SCK = 11  # HX711 Clock pin (SCK)

# Initialize HX711
hx = HX711(DT, SCK)

# Set reading format
hx.set_reading_format("MSB", "MSB")

# Tare function
def tare():
    print("[INFO] Taring the scale... Please remove all weight.")
    time.sleep(2)
    hx.tare()
    print("[INFO] Tare complete.")

# Calibration function
def calibrate():
    print("[INFO] Place a known mass on the load cell (e.g. 100.0 grams).")
    known_weight = None
    while known_weight is None:
        try:
            known_weight = float(input("Enter known weight in grams: "))
        except ValueError:
            print("Invalid input. Try again.")

    raw_val = hx.get_weight(5)
    calibration_factor = raw_val / known_weight
    print(f"[INFO] Calibration complete. Calibration factor: {calibration_factor:.2f}")

    save = input("Save calibration factor to file? (y/n): ").lower()
    if save == 'y':
        with open("calibration.txt", "w") as f:
            f.write(str(calibration_factor))
        print("[INFO] Calibration factor saved to 'calibration.txt'.")

    return calibration_factor

# Load calibration factor if available
def load_calibration():
    try:
        with open("calibration.txt", "r") as f:
            return float(f.read().strip())
    except:
        return None

# Setup code
hx.reset()
tare()
cal_factor = load_calibration()

if cal_factor is None:
    cal_factor = calibrate()
else:
    print(f"[INFO] Using saved calibration factor: {cal_factor:.2f}")

hx.set_reference_unit(cal_factor)

# Start weight readings
print("[INFO] Starting weight readings. Press Ctrl+C to stop.")
try:
    while True:
        weight = hx.get_weight(5)
        print(f"[WEIGHT] {weight:.2f} g")
        time.sleep(1)
        hx.power_down()
        hx.power_up()
except (KeyboardInterrupt, SystemExit):
    print("\n[INFO] Exiting...")
    GPIO.cleanup()
    sys.exit()
