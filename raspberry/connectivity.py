# connectivity.py
from sensors.gps_module import get_gsm_location
import gprs_manager

def get_location_then_connect():
    # 1) Free up /dev/ttyS0 if GPRS was running
    gprs_manager.kill_ppp()

    # 2) Read GPS (cell‑tower lookup)
    lat, lon = get_gsm_location()

    # 3) Bring up GPRS if it’s not already up
    if not gprs_manager.is_up():
        gprs_manager.start_gprs()

    return lat, lon
