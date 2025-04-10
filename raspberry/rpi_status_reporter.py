import sys
import requests

HIVE_ID = 1
API_URL = f"https://bees-backend.aiiot.center/api/hives/status/{HIVE_ID}"

def report_status(is_online=True):
    try:
        data = {"status": bool(is_online)}
        headers = {"Content-Type": "application/json"}
        response = requests.put(API_URL, json=data, headers=headers)
        print(f"📡 Sent status {data['status']} to {API_URL}, HTTP {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ Failed to report status: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ["on", "off"]:
        print("Usage: python3 rpi_status_reporter.py [on|off]")
        sys.exit(1)

    status = sys.argv[1] == "on"  # True if "on", False if "off"
    report_status(status)
