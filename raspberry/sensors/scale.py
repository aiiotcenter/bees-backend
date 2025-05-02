# scale.py
import time
import RPi.GPIO as GPIO
from hx711 import HX711

# Pin configuration
DT = 3
SCK = 11

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

class Scale:
    def __init__(self, data_pin=DT, clk_pin=SCK):
        try:
            self.hx = HX711(data_pin, clk_pin)
            self.hx.set_reading_format("MSB", "MSB")
            self.hx.reset()
        except Exception as e:
            print(f"[ERROR] Failed to initialize HX711: {e}")
            GPIO.cleanup()
            raise

        self.calibration_factor = self.load_calibration()
        if self.calibration_factor:
            self.hx.set_reference_unit(self.calibration_factor)

    def tare(self):
        print("[INFO] Taring the scale... Please remove all weight.")
        time.sleep(2)
        if not self.hx.wait_ready(timeout=5):
            print("[ERROR] HX711 not ready. Check wiring and power.")
            GPIO.cleanup()
            raise RuntimeError("HX711 not responding.")
        self.hx.tare()
        print("[INFO] Tare complete.")

    def calibrate(self):
        print("[INFO] Place a known mass on the load cell.")
        known_weight = None
        while known_weight is None:
            try:
                known_weight = float(input("Enter known weight in grams: "))
            except ValueError:
                print("Invalid input. Try again.")

        if not self.hx.wait_ready(timeout=5):
            print("[ERROR] HX711 not ready during calibration. Check wiring and power.")
            GPIO.cleanup()
            raise RuntimeError("HX711 not responding during calibration.")

        raw_val = self.hx.get_weight(5)
        self.calibration_factor = raw_val / known_weight
        print(f"[INFO] Calibration complete. Calibration factor: {self.calibration_factor:.2f}")

        save = input("Save calibration factor to file? (y/n): ").lower()
        if save == 'y':
            with open("calibration.txt", "w") as f:
                f.write(str(self.calibration_factor))
            print("[INFO] Calibration factor saved.")

        self.hx.set_reference_unit(self.calibration_factor)
        return self.calibration_factor

    def load_calibration(self):
        try:
            with open("calibration.txt", "r") as f:
                return float(f.read().strip())
        except:
            return None

    def get_weight(self):
        if not self.hx.wait_ready(timeout=5):
            print("[ERROR] HX711 not ready during weight read.")
            return None
        weight = self.hx.get_weight(5)
        self.hx.power_down()
        self.hx.power_up()
        return weight

    def cleanup(self):
        GPIO.cleanup()

# Standalone usage
if __name__ == "__main__":
    try:
        scale = Scale()
        scale.tare()

        if scale.calibration_factor is None:
            scale.calibrate()

        print("[INFO] Starting standalone weight readings. Press Ctrl+C to stop.")
        while True:
            weight = scale.get_weight()
            if weight is not None:
                print(f"[WEIGHT] {weight:.2f} g")
            else:
                print("[WARN] Skipping reading due to HX711 not ready.")
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[INFO] Exiting standalone scale mode.")
    except Exception as e:
        print(f"[FATAL] {e}")
    finally:
        GPIO.cleanup()
