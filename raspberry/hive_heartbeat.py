import requests, time, json

HIVE_ID = 1
SERVER_URL = "http://100.70.97.126:9602/api/hives/heartbeat"

def send_heartbeat():
    while True:
        try:
            response = requests.post(SERVER_URL, json={"hiveId": HIVE_ID}, verify=False, timeout=10)
            if response.status_code == 200:
                print("Heartbeat sent successfully")
            else:
                print("Failed:", response.text)
        except Exception as e:
            print("Error sending heartbeat:", e)
        time.sleep(120)  # every 2 minutes

# ADD THIS - Actually call the function
if __name__ == "__main__":
    print(f"Starting heartbeat service for Hive ID: {HIVE_ID}")
    print(f"Target: {SERVER_URL}")
    send_heartbeat()