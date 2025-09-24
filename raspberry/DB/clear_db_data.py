import sqlite3

db = "/home/pi/beehive_data/offline_data.db"
conn = sqlite3.connect(db)
cur = conn.cursor()

for table in ["sensor_readings", "location_data", "status_updates"]:
    try:
        cur.execute(f"DELETE FROM {table}")
        print(f"Cleared table: {table}")
    except Exception as e:
        print(f"Error clearing {table}: {e}")

conn.commit()
conn.close()
print("✅ All data cleared, database structure kept.")
