import requests, time, json

HIVE_ID = 1
SERVER_URL = "https://100.70.97.126:9602/api/heartbeat"

def send_heartbeat():
    while True:
        try:
            response = requests.post(SERVER_URL, json={"hiveId": HIVE_ID})
            if response.status_code == 200:
                print("Heartbeat sent successfully")
            else:
                print("Failed:", response.text)
        except Exception as e:
            print("Error sending heartbeat:", e)
        time.sleep(120)  # every 2 minutes
