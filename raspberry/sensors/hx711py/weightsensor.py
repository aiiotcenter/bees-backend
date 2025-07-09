import time
import sys
import RPi.GPIO as GPIO
from hx711 import HX711

DT = 3    # DOUT
SCK = 11  # SCK

def create_hx():
    hx = HX711(DT, SCK)
    hx.set_reading_format("MSB", "MSB")
    return hx

def tare(hx):
    print("[INFO] Taring the scale... Please remove all weight.")
    time.sleep(2)
    hx.tare()
    print("[INFO] Tare complete.")

def calibrate(hx):
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

def load_calibration():
    try:
        with open("calibration.txt", "r") as f:
            return float(f.read().strip())
    except:
        return None

def get_weight(timeout=2):
    import signal

    class TimeoutException(Exception): pass

    def handler(signum, frame):
        raise TimeoutException()

    signal.signal(signal.SIGALRM, handler)
    signal.alarm(timeout)

    try:
        hx = create_hx()
        cal = load_calibration()
        if cal:
            hx.set_reference_unit(cal)
        else:
            hx.set_reference_unit(1)

        weight = hx.get_weight(5)
        hx.power_down()
        hx.power_up()
        signal.alarm(0)  # cancel alarm
        return weight
    except TimeoutException:
        print("⏱️ Weight reading timed out.")
        return None
    except Exception as e:
        print(f"⚠️ Error reading weight: {e}")
        return None
    finally:
        GPIO.cleanup()
        signal.alarm(0)

# Optional CLI test
if __name__ == "__main__":
    try:
        hx = create_hx()
        tare(hx)
        cal = load_calibration() or calibrate(hx)
        hx.set_reference_unit(cal)

        print("[INFO] Starting weight readings. Press Ctrl+C to stop.")
        while True:
            weight = get_weight()
            if weight is not None:
                print(f"[WEIGHT] {weight:.2f} g")
            time.sleep(1)

    except (KeyboardInterrupt, SystemExit):
        print("\n[INFO] Exiting...")
        GPIO.cleanup()
        sys.exit()
