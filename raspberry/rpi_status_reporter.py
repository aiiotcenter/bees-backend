import sys
import requests

HIVE_ID = 1
API_URL = f"http://bees-backend.aiiot.center/api/hives/status/{HIVE_ID}"

def report_status(status_value):
    try:
        data = {"status": int(status_value)}
        response = requests.post(API_URL, json=data)
        print(f"📡 Sent status {status_value} to {API_URL}, HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ Failed to report status {status_value}: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ["on", "off"]:
        print("Usage: python3 rpi_status_reporter.py [on|off]")
        sys.exit(1)

    status = 1 if sys.argv[1] == "on" else 0
    report_status(status)
