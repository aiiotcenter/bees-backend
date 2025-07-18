# ~/bees-backend/raspberry/gprs_manager.py
import subprocess, time

GPRS_SCRIPT = "/home/pi/bees-backend/raspberry/gprs_connect.sh"

def kill_ppp():
    """Tear down old PPP daemons."""
    subprocess.run(["sudo","poff","-a"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["sudo","pkill","-9","-f","pppd"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["sudo","pkill","-9","-f","chat"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["sudo","rm","-f","/var/lock/LCK..ttyS0","/var/lock/LCK..serial0"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)

def start_gprs():
    """Run our connect script."""
    subprocess.Popen(
        ["sudo", GPRS_SCRIPT],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True
    )
    # Give it enough time to finish
    time.sleep(25)

def is_up():
    """Check ppp0 has an IP."""
    return bool(subprocess.run(
        ["ip","addr","show","ppp0"], capture_output=True, text=True
    ).stdout.split("inet "))
