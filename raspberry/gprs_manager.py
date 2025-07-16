import subprocess, time

GPRS_SCRIPT = "/home/pi/bees-backend/raspberry/gprs_connect.sh"

def kill_ppp():
    subprocess.run(["sudo","poff","-a"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["sudo","pkill","-f","pppd"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["sudo","pkill","-f","chat"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["sudo","rm","-f","/var/lock/LCK..ttyS0","/var/lock/LCK..serial0"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)

def start_gprs():
    proc = subprocess.Popen(
        ["sudo", GPRS_SCRIPT],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True
    )
    time.sleep(5)
    return proc

def is_up():
    out = subprocess.run(["ip","route","show"], capture_output=True, text=True).stdout
    return "ppp0" in out