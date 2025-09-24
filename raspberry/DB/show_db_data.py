import sqlite3
from tabulate import tabulate  # install with: pip install tabulate

DB_PATH = "/home/pi/beehive_data/offline_data.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
    SELECT id, hive_id, temperature, humidity, sound_status, is_door_open,
           latitude, longitude, recorded_at, sent, retry_count
    FROM sensor_readings
    ORDER BY created_at DESC
    LIMIT 10
""")
rows = cursor.fetchall()

headers = ["ID", "Hive", "Temp", "Hum", "Sound", "Door",
           "Lat", "Long", "RecordedAt", "Sent", "Tries"]

print(tabulate(rows, headers=headers, tablefmt="grid"))

conn.close()

