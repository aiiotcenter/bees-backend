# ~/bees-backend/raspberry/gprs_manager.py
import subprocess, time

GPRS_SCRIPT = "/home/pi/bees-backend/raspberry/gprs_connect.sh"

def start_gprs():
    subprocess.Popen(
        ["sudo", GPRS_SCRIPT],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True
    )
    time.sleep(10)  # give it time to finish
