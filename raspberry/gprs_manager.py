import subprocess, time

GPRS_SCRIPT = "/home/pi/bees-backend/raspberry/gprs_connect.sh"

def kill_ppp():
    """Tear down any existing PPP so /dev/serial0 is free."""
    subprocess.run(["sudo","poff","-a"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["sudo","pkill","-9","-f","pppd"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["sudo","pkill","-9","-f","chat"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["sudo","rm","-f","/var/lock/LCK..ttyS0","/var/lock/LCK..serial0"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)

def start_gprs():
    """Run our gprs_connect.sh (which backgrounds pppd + installs host‑routes)."""
    subprocess.Popen(
        ["sudo", GPRS_SCRIPT],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True
    )
    # give it time to finish
    time.sleep(15)

def is_up():
    """Return True if ppp0 is up."""
    out = subprocess.run(["ip","link","show","ppp0"], capture_output=True, text=True).stdout
    return "state UP" in out
