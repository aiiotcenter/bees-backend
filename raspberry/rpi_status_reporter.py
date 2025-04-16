import sys
import requests
import time

HIVE_ID = 1
API_URL = f"https://bees-backend.aiiot.center/api/hives/status/{HIVE_ID}"

def report_status(is_online=True, retries=10, wait_seconds=40):
    data = {"status": bool(is_online)}
    headers = {"Content-Type": "application/json"}

    for attempt in range(1, retries + 1):
        try:
            response = requests.put(API_URL, json=data, headers=headers)
            print(f"📡 Attempt {attempt}: Sent status {data['status']} to {API_URL}, HTTP {response.status_code}")
            print(f"Response: {response.text}")

            if response.status_code == 200:
                print("✅ Successfully reported status.")
                return True  # Exit on success

        except Exception as e:
            print(f"❌ Attempt {attempt} failed: {e}")

        print(f"⏳ Retrying in {wait_seconds} seconds...")
        time.sleep(wait_seconds)

    print("❗ Gave up after multiple attempts.")
    return False

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ["on", "off"]:
        print("Usage: python3 rpi_status_reporter.py [on|off]")
        sys.exit(1)

    status = sys.argv[1] == "on"
    report_status(status)
