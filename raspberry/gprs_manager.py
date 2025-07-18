# ~/bees-backend/raspberry/gprs_manager.py
import subprocess
import time

GPRS_SCRIPT = "/home/pi/bees-backend/raspberry/gprs_connect.sh"

def kill_ppp():
    """
    Free /dev/serial0 (and any old PPP daemons) so AT commands can run.
    """
    subprocess.run(["sudo", "poff", "-a"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["sudo", "pkill", "-9", "-f", "pppd"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["sudo", "pkill", "-9", "-f", "chat"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["sudo", "rm", "-f",
                    "/var/lock/LCK..ttyS0",
                    "/var/lock/LCK..serial0"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # give it a moment to fully tear down
    time.sleep(1)

def start_gprs():
    """
    Launch the connect script (which backgrounds pon & installs host‑routes).
    """
    subprocess.Popen(
        ["sudo", GPRS_SCRIPT],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True
    )
    # wait long enough for ppp0 to come up
    time.sleep(10)

def is_up():
    """
    Return True if ppp0 is currently up.
    """
    out = subprocess.run(["ip", "link", "show", "ppp0"],
                         capture_output=True, text=True).stdout
    return "state UP" in out
