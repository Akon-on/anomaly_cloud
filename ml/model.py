import json
import logging
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2
from psycopg2 import OperationalError
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import OneClassSVM

from feature_engineering import FEATURE_COLUMNS, build_feature_frame

DB_HOST = os.getenv("DB_HOST", "db")
DB_NAME = os.getenv("DB_NAME", "logs")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "admin")
MODEL_TYPE = os.getenv("MODEL_TYPE", "isolation_forest").lower()
MODEL_CONTAMINATION = float(os.getenv("MODEL_CONTAMINATION", "0.3"))
USE_THRESHOLD_TUNING = os.getenv("USE_THRESHOLD_TUNING", "true").lower() == "true"
ANOMALY_THRESHOLD = float(os.getenv("ANOMALY_THRESHOLD", "0.1"))  # Calibrated threshold
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/app/output"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
REQUIRED_LOG_FIELDS = {"time", "ip", "endpoint", "status"}
LOG_FILE = os.getenv("LOG_FILE", "/logs/access.log")
WINDOW_SIZE = int(os.getenv("WINDOW_SIZE", "10"))
SLEEP_TIME = int(os.getenv("SLEEP_TIME", "10"))
HISTORY_WINDOWS = int(os.getenv("HISTORY_WINDOWS", "60"))

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("ml")


def normalize_log_record(record):
    missing_fields = REQUIRED_LOG_FIELDS - set(record.keys())
    if missing_fields:
        return None

    try:
        record["time"] = float(record["time"])
    except (TypeError, ValueError):
        return None

    return record


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
            logger.warning(
                "DB not ready (attempt %s/%s): %s",
                attempt,
                max_retries,
                exc,
            )
            time.sleep(delay_seconds)

    raise RuntimeError("Unable to connect to DB after retries")


def build_model(model_name, contamination, n_samples):
    if model_name == "isolation_forest":
        return IsolationForest(
            n_estimators=100,
            contamination=contamination,
            random_state=42
        )

    if model_name == "isolation_forest_tuned":
        return IsolationForest(
            n_estimators=300,
            max_samples="auto",
            contamination=contamination,
            bootstrap=True,
            random_state=42,
        )

    if model_name == "lof":
        lof_neighbors = max(1, min(20, n_samples - 1))
        return LocalOutlierFactor(
            n_neighbors=lof_neighbors,
            contamination=contamination,
            novelty=True
        )

    if model_name == "ocsvm":
        return make_pipeline(
            StandardScaler(),
            OneClassSVM(nu=contamination, kernel="rbf", gamma="scale")
        )

    raise ValueError(
        "MODEL_TYPE must be one of: isolation_forest, isolation_forest_tuned, lof, ocsvm"
    )


def predict_anomalies(model, model_name, features):
    """Predict anomalies with optional threshold tuning.
    
    Returns: (predictions, scores) tuple
      - predictions: binary array (-1 for anomaly, 1 for normal)
      - scores: anomaly scores (higher = more anomalous)
    """
    if model_name == "ocsvm":
        model.fit(features)
        preds = model.predict(features)
        scores = -model.decision_function(features)
        return preds, scores

    model.fit(features)
    preds = model.predict(features)
    
    # Get decision scores for threshold tuning
    if hasattr(model, 'decision_function'):
        scores = -model.decision_function(features)
    elif hasattr(model, 'score_samples'):
        scores = -model.score_samples(features)
    else:
        # Fallback: no scores available
        scores = None
    
    return preds, scores


def score_to_predictions(scores, threshold):
    return np.where(np.asarray(scores) >= threshold, -1, 1)


def load_threshold_from_comparison(model_name: str) -> tuple[float | None, str]:
    comparison_file = OUTPUT_DIR / "model_comparison.csv"
    if not comparison_file.exists():
        return None, "missing_comparison_file"

    try:
        comparison_df = pd.read_csv(comparison_file)
    except Exception as exc:
        logger.warning("Unable to read model comparison file: %s", exc)
        return None, "comparison_read_failed"

    if comparison_df.empty or "model" not in comparison_df.columns or "best_threshold" not in comparison_df.columns:
        return None, "comparison_missing_columns"

    model_rows = comparison_df[comparison_df["model"].astype(str) == model_name]
    if model_rows.empty:
        return None, "model_not_found_in_comparison"

    threshold = model_rows.iloc[0].get("best_threshold")
    if pd.isna(threshold):
        return None, "threshold_not_available"

    return float(threshold), "comparison_file"


def read_new_records(log_file, last_processed_time):
    records = []
    with open(log_file, encoding="utf-8") as handle:
        for line in handle:
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue

            normalized = normalize_log_record(data)
            if normalized is None:
                continue

            if normalized["time"] > last_processed_time:
                records.append(normalized)

    return records


def trim_history(records, newest_time):
    min_time = newest_time - (WINDOW_SIZE * HISTORY_WINDOWS)
    return [record for record in records if record["time"] >= min_time]


def insert_anomalies(cursor, anomalies):
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
                int(row["window"]),
                int(row["requests_per_window"]),
                int(row["failed_logins"]),
                MODEL_TYPE
            )
        )


def run_detector():
    anomaly_threshold = ANOMALY_THRESHOLD
    conn = connect_with_retry()
    cursor = conn.cursor()

    logger.info("ML service starting...")
    logger.info("Using model: %s (contamination=%s)", MODEL_TYPE, MODEL_CONTAMINATION)
    if USE_THRESHOLD_TUNING:
        loaded_threshold, threshold_source = load_threshold_from_comparison(MODEL_TYPE)
        if loaded_threshold is not None:
            anomaly_threshold = loaded_threshold
            logger.info(
                "Loaded tuned threshold for %s from model_comparison.csv (source=%s)",
                MODEL_TYPE,
                threshold_source,
            )
        else:
            logger.info(
                "No tuned threshold found for %s; using configured threshold",
                MODEL_TYPE,
            )
        logger.info("Threshold tuning enabled (threshold=%.4f)", anomaly_threshold)
    else:
        logger.info("Using default contamination-based detection")

    while not os.path.exists(LOG_FILE):
        time.sleep(1)

    logger.info("Logs found. Starting real-time detection.")

    last_processed_time = 0
    record_history = []
    emitted_anomalies = set()

    while True:
        records = read_new_records(LOG_FILE, last_processed_time)

        if not records:
            time.sleep(SLEEP_TIME)
            continue

        newest_time = max(record["time"] for record in records)
        last_processed_time = newest_time
        record_history.extend(records)
        record_history = trim_history(record_history, newest_time)

        features = build_feature_frame(pd.DataFrame(record_history), WINDOW_SIZE)

        if len(features) < 2:
            logger.info("Waiting for more feature windows before fitting model.")
            time.sleep(SLEEP_TIME)
            continue

        X = features[FEATURE_COLUMNS]

        model = build_model(MODEL_TYPE, MODEL_CONTAMINATION, len(features))
        preds, scores = predict_anomalies(model, MODEL_TYPE, X)

        if USE_THRESHOLD_TUNING and scores is not None:
            features["anomaly"] = score_to_predictions(scores, anomaly_threshold)
            features["anomaly_score"] = scores
            logger.info(
                "Applied threshold tuning (threshold=%.4f) to %d windows",
                anomaly_threshold,
                len(features),
            )
        else:
            features["anomaly"] = preds

        anomalies = features[features["anomaly"] == -1].copy()
        if not anomalies.empty:
            anomalies["dedupe_key"] = list(zip(anomalies["ip"], anomalies["window"]))
            anomalies = anomalies[~anomalies["dedupe_key"].isin(emitted_anomalies)]

        if not anomalies.empty:
            logger.warning("ANOMALY DETECTED")
            logger.info("%s", anomalies.drop(columns=["dedupe_key"]).to_string(index=False))

            try:
                insert_anomalies(cursor, anomalies)
                conn.commit()
                emitted_anomalies.update(anomalies["dedupe_key"])
            except Exception:
                conn.rollback()
                logger.exception("Failed to persist detected anomalies")
        else:
            logger.info("No new anomalies.")

        time.sleep(SLEEP_TIME)


if __name__ == "__main__":
    run_detector()
