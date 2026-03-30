import json
import pandas as pd
import time
import os
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import OneClassSVM
import psycopg2
from psycopg2 import OperationalError

DB_HOST = os.getenv("DB_HOST", "db")
DB_NAME = os.getenv("DB_NAME", "logs")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "admin")
MODEL_TYPE = os.getenv("MODEL_TYPE", "isolation_forest").lower()
MODEL_CONTAMINATION = float(os.getenv("MODEL_CONTAMINATION", "0.3"))


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


def build_model(model_name, contamination):
    if model_name == "isolation_forest":
        return IsolationForest(
            n_estimators=100,
            contamination=contamination,
            random_state=42
        )

    if model_name == "lof":
        return LocalOutlierFactor(
            n_neighbors=20,
            contamination=contamination
        )

    if model_name == "ocsvm":
        return make_pipeline(
            StandardScaler(),
            OneClassSVM(nu=contamination, kernel="rbf", gamma="scale")
        )

    raise ValueError(
        "MODEL_TYPE must be one of: isolation_forest, lof, ocsvm"
    )


def predict_anomalies(model, model_name, features):
    if model_name == "lof":
        return model.fit_predict(features)

    if model_name == "ocsvm":
        model.fit(features)
        return model.predict(features)

    return model.fit_predict(features)


conn = connect_with_retry()

cursor = conn.cursor()

LOG_FILE = "/logs/access.log"
WINDOW_SIZE = 10
SLEEP_TIME = 10

print("ML service starting...")
print(f"Using model: {MODEL_TYPE} (contamination={MODEL_CONTAMINATION})")

# Wait for log file
while not os.path.exists(LOG_FILE):
    time.sleep(1)

print("Logs found. Starting real-time detection.")

last_processed_time = 0

while True:
    records = []

    with open(LOG_FILE) as f:
        for line in f:
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue  # skip non-JSON lines

            if data["time"] > last_processed_time:
                records.append(data)

    if not records:
        time.sleep(SLEEP_TIME)
        continue

    df = pd.DataFrame(records)
    df["time"] = df["time"].astype(float)
    last_processed_time = df["time"].max()

    df["window"] = (df["time"] // WINDOW_SIZE).astype(int)

    features = df.groupby(["ip", "window"]).agg(
        requests_per_window=("endpoint", "count"),
        failed_logins=("status", lambda x: (x == "fail").sum())
    ).reset_index()

    if len(features) < 2:
        time.sleep(SLEEP_TIME)
        continue

    X = features[["requests_per_window", "failed_logins"]]

    model = build_model(MODEL_TYPE, MODEL_CONTAMINATION)
    features["anomaly"] = predict_anomalies(model, MODEL_TYPE, X)

    anomalies = features[features["anomaly"] == -1]

    if not anomalies.empty:
        print("\n ANOMALY DETECTED ")
        print(anomalies)

        for _, row in anomalies.iterrows():
            cursor.execute(
                """
                INSERT INTO anomalies (
                    ip,
                    time_window,
                    requests_per_window,
                    failed_logins,
                    model_name
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    row["ip"],
                    int(row["window"]),  # Python variable
                    int(row["requests_per_window"]),
                    int(row["failed_logins"]),
                    MODEL_TYPE
                )
            )

        conn.commit()
    else:
        print("No anomalies.")

    time.sleep(SLEEP_TIME)
