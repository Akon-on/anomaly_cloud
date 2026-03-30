import psycopg2
import pandas as pd
import os
import time
from psycopg2 import OperationalError

DB_HOST = os.getenv("DB_HOST", "db")
DB_NAME = os.getenv("DB_NAME", "logs")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "admin")


def connect_with_retry(max_retries=30, delay_seconds=2):
    for attempt in range(1, max_retries + 1):
        try:
            return psycopg2.connect(
                host=DB_HOST,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD
            )
        except OperationalError as exc:
            print(
                f"DB not ready (attempt {attempt}/{max_retries}): {exc}"
            )
            time.sleep(delay_seconds)

    raise RuntimeError("Unable to connect to DB after retries")


conn = connect_with_retry()

# Load anomalies
df = pd.read_sql("SELECT * FROM anomalies", conn)
conn.close()

print("\n=== METRICS REPORT ===\n")

if df.empty:
    print("No anomalies detected yet.")
    raise SystemExit(0)

# 1. Total anomalies
print(f"Total anomalies detected: {len(df)}")

# 2. Anomalies per IP
print("\nAnomalies per IP:")
print(df["ip"].value_counts())

# 3. Time-based distribution
print("\nAnomalies per time window:")
print(df["time_window"].value_counts().sort_index())

# 4. Attack intensity
print("\nAttack intensity statistics:")
print(df[["requests_per_window", "failed_logins"]].describe())
