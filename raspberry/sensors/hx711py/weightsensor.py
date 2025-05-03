import time
from hx711py.hx711 import HX711  # Ensure HX711 is correctly imported

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

# Read the weight (average of multiple readings)
def get_weight(num_samples=5):
    try:
        # Get average weight from multiple samples
        weights = [hx.get_weight(5) for _ in range(num_samples)]
        avg_weight = sum(weights) / len(weights)  # Take the average to reduce noise
        return avg_weight
    except Exception as e:
        print(f"⚠️ Error reading weight: {e}")
        return None
