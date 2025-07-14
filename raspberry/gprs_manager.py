# gprs_manager.py
import subprocess
import time

GPRS_SCRIPT = "/home/pi/gprs_connect.sh"

def kill_ppp():
    """Stop any running PPP so /dev/ttyS0 is free for GPS."""
    subprocess.run(["sudo","poff","-a"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["sudo","pkill","-f","pppd"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["sudo","pkill","-f","chat"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["sudo","rm","-f","/var/lock/LCK..ttyS0"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)

def start_gprs():
    """Launch your GPRS script in the background so Python keeps running."""
    print("📲 Starting GPRS (background)…")
    # start_new_session=True detaches it from this terminal
    proc = subprocess.Popen(
        ["sudo", GPRS_SCRIPT],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True
    )
    time.sleep(5)  # give pppd a few seconds to settle
    print("✅ GPRS startup issued")
    return proc

def is_up():
    """Return True if ppp0 is present in ifconfig."""
    out = subprocess.run(["ifconfig"], capture_output=True, text=True).stdout
    return "ppp0" in out
