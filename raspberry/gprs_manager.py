# ~/bees-backend/raspberry/gprs_manager.py
import subprocess, time

GPRS_SCRIPT = "/home/pi/gprs.sh"

def kill_ppp():
    """Free /dev/ttyS0 so AT commands can run."""
    subprocess.run(["sudo","poff","-a"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["sudo","pkill","-f","pppd"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["sudo","pkill","-f","chat"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["sudo","rm","-f","/var/lock/LCK..ttyS0"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)

def start_gprs():
    """Launch pon/pppd in the background, returning immediately."""
    proc = subprocess.Popen(
        ["sudo", GPRS_SCRIPT],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True
    )
    time.sleep(5)  # let pppd negotiate
    return proc

def is_up():
    out = subprocess.run(["ifconfig"], capture_output=True, text=True).stdout
    return "ppp0" in out
