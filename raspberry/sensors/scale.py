# scale.py
import time
import RPi.GPIO as GPIO
from hx711 import HX711

# Pin configuration
DT = 3
SCK = 11

class Scale:
    def __init__(self, data_pin=DT, clk_pin=SCK):
        self.hx = HX711(data_pin, clk_pin)
        self.hx.set_reading_format("MSB", "MSB")
        self.hx.reset()
        self.calibration_factor = self.load_calibration()

        if self.calibration_factor:
            self.hx.set_reference_unit(self.calibration_factor)

    def tare(self):
        print("[INFO] Taring the scale... Please remove all weight.")
        time.sleep(2)
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
        weight = self.hx.get_weight(5)
        self.hx.power_down()
        self.hx.power_up()
        return weight

    def cleanup(self):
        GPIO.cleanup()
