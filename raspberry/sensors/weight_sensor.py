import time
from sensors.hx711 import HX711

def initialize_hx711():
    try:
        hx = HX711(3, 11)
        hx.set_reading_format("MSB", "MSB")
        hx.set_reference_unit(114)
        hx.reset()
        hx.tare()  # Tare the scale to set the current weight as 0
        print("⚖️ HX711 initialized")
        return hx
    except Exception as e:
        print(f"⚠️ Error initializing HX711: {e}")
        return None

def get_weight(hx, samples=10):
    try:
        # Get the current weight (assuming it’s the baseline)
        weights = []
        for _ in range(samples):
            weights.append(hx.get_weight(1))
            time.sleep(0.05)
        average_weight = sum(weights) / len(weights)
        
        # After reading, tare it again to reset to baseline zero if anything changed
        hx.power_down()
        time.sleep(0.1)
        hx.power_up()
        hx.tare()

        # Return the average weight (which will now be based on the current load + any additional weight)
        print(f"⚖️ Weight: {round(average_weight, 2)} g")
        return round(average_weight, 2)
    except Exception as e:
        print(f"⚠️ Error reading weight: {e}")
        return 0
