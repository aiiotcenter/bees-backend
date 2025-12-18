#!/usr/bin/env python3
import sqlite3
import time
import requests
from datetime import datetime, timezone

DB_PATH = "/home/pi/beehive_data/offline_data.db"

API_RECORDS = "https://bees-backend.aiiot.center/api/records"
API_STATUS_FMT = "https://bees-backend.aiiot.center/api/hives/status/{hive_id}"
API_LOCATION = "https://bees-backend.aiiot.center/api/hives/check-location/1"

BATCH_SIZE = 50
HTTP_TIMEOUT = 15
MAX_RETRIES_PER_ROW = 10 
SLEEP_BETWEEN_SENDS = 0.08
STOP_AFTER_CONSEC_FAILS = 10      # safety stop


def utc_now_str():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ensure_lock_column(conn: sqlite3.Connection, table: str):
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cur.fetchall()]
    if "locked_at" not in cols:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN locked_at TEXT")
        conn.commit()


def internet_ok() -> bool:
    try:
        r = requests.get("https://bees-backend.aiiot.center", timeout=8)
        return r.status_code < 500
    except Exception:
        return False


def request_with_backoff(method, url, payload):
    delay = 1.0
    last = ""
    for _ in range(MAX_RETRIES_PER_ROW):
        try:
            r = requests.request(method, url, json=payload, timeout=HTTP_TIMEOUT)
            if r.status_code in (200, 201):
                return True, f"{r.status_code} {r.text}"
            if r.status_code == 429:
                time.sleep(min(delay * 3, 30))
            else:
                time.sleep(min(delay, 15))
            delay *= 2
            last = f"{r.status_code} {r.text}"
        except Exception as e:
            last = str(e)
            time.sleep(min(delay, 15))
            delay *= 2
    return False, last


def claim_batch(conn, table, where_sql, batch_size):
    """
    Claims rows by setting locked_at for rows not locked and not sent.
    Returns list of row ids claimed.
    """
    cur = conn.cursor()
    now = utc_now_str()

    cur.execute(f"""
        SELECT id FROM {table}
        WHERE sent = 0
          AND (locked_at IS NULL OR locked_at = '')
          AND {where_sql}
        ORDER BY created_at ASC
        LIMIT ?
    """, (batch_size,))
    ids = [r[0] for r in cur.fetchall()]

    if not ids:
        return []

    # Mark as locked
    cur.executemany(
        f"UPDATE {table} SET locked_at = ? WHERE id = ?",
        [(now, i) for i in ids]
    )
    conn.commit()
    return ids


def mark_sent(conn, table, row_id):
    cur = conn.cursor()
    cur.execute(f"UPDATE {table} SET sent = 1, locked_at = NULL WHERE id = ?", (row_id,))
    conn.commit()


def bump_retry(conn, table, row_id):
    cur = conn.cursor()
    cur.execute(f"UPDATE {table} SET retry_count = retry_count + 1, locked_at = NULL WHERE id = ?", (row_id,))
    conn.commit()


def fetch_row(conn, table, row_id):
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM {table} WHERE id = ?", (row_id,))
    return cur.fetchone()


def send_sensor_reading(row):
    # sensor_readings schema indices based on your CREATE TABLE order:
    # 0 id, 1 hive_id, 2 temperature, 3 humidity, 4 weight, 5 distance,
    # 6 sound_status, 7 is_door_open, 8 num_of_in, 9 num_of_out, 10 latitude,
    # 11 longitude, 12 status, 13 recorded_at, 14 created_at, 15 sent, 16 retry_count, 17 locked_at(optional)
    payload = {
        "hiveId": row[1],
        "temperature": row[2],
        "humidity": row[3],
        "weight": row[4],
        "distance": row[5],
        "soundStatus": row[6],
        "isDoorOpen": row[7],
        "numOfIn": row[8],
        "numOfOut": row[9],
        "latitude": row[10],
        "longitude": row[11],
        "status": bool(row[12]),
        "recordedAt": row[13],
    }
    return request_with_backoff("POST", API_RECORDS, payload)


def send_status_update(row):
    # status_updates: 0 id, 1 hive_id, 2 status, 3 created_at, 4 sent, 5 retry_count, 6 locked_at(optional)
    hive_id = row[1]
    payload = {"status": bool(row[2])}
    url = API_STATUS_FMT.format(hive_id=hive_id)
    return request_with_backoff("PUT", url, payload)


def send_location(row):
    # location_data: 0 id, 1 latitude, 2 longitude, 3 created_at, 4 sent, 5 retry_count, 6 locked_at(optional)
    payload = {"latitude": row[1], "longitude": row[2]}
    return request_with_backoff("POST", API_LOCATION, payload)


def drain_table(conn, table, sender_fn, where_sql="1=1"):
    ensure_lock_column(conn, table)
    total_sent = 0
    consec_fail = 0

    while True:
        if not internet_ok():
            print("🌐 Internet not OK. Stopping.")
            break

        ids = claim_batch(conn, table, where_sql=where_sql, batch_size=BATCH_SIZE)
        if not ids:
            break

        for row_id in ids:
            row = fetch_row(conn, table, row_id)
            if not row:
                continue

            ok, info = sender_fn(row)
            if ok:
                mark_sent(conn, table, row_id)
                total_sent += 1
                consec_fail = 0
                print(f"✅ Sent {table} id={row_id} -> {info}")
                time.sleep(SLEEP_BETWEEN_SENDS)
            else:
                bump_retry(conn, table, row_id)
                consec_fail += 1
                print(f"❌ Failed {table} id={row_id} -> {info}")

                if consec_fail >= STOP_AFTER_CONSEC_FAILS:
                    print("🛑 Too many consecutive failures. Stopping to avoid hammering.")
                    return total_sent

    return total_sent


def main():
    conn = sqlite3.connect(DB_PATH)

    print("📤 Draining sensor_readings...")
    s1 = drain_table(conn, "sensor_readings", send_sensor_reading)

    print("📤 Draining status_updates...")
    s2 = drain_table(conn, "status_updates", send_status_update)

    print("📤 Draining location_data...")
    s3 = drain_table(conn, "location_data", send_location)

    conn.close()
    print(f"\n✅ Done. Sent totals: readings={s1}, status={s2}, location={s3}")


if __name__ == "__main__":
    main()
