import numpy as np
import pandas as pd

REQUIRED_LOG_COLUMNS = {"time", "ip", "endpoint", "status"}
FEATURE_COLUMNS = [
    "requests_per_window",
    "request_rate",
    "failed_logins",
    "successful_logins",
    "login_attempts",
    "login_ratio",
    "failed_login_ratio",
    "successful_requests",
    "distinct_endpoints",
    "unique_user_agents",
]


def prepare_log_frame(raw_df: pd.DataFrame, window_size: int) -> pd.DataFrame:
    missing_columns = REQUIRED_LOG_COLUMNS - set(raw_df.columns)
    if missing_columns:
        missing_list = ", ".join(sorted(missing_columns))
        raise ValueError(f"Log file is missing required columns: {missing_list}")

    df = raw_df.copy()
    df["time"] = df["time"].astype(float)
    df["ip"] = df["ip"].astype(str)
    df["endpoint"] = df["endpoint"].astype(str)
    df["status"] = df["status"].astype(str).str.lower()
    if "user_agent" not in df.columns:
        df["user_agent"] = "unknown"
    df["user_agent"] = df["user_agent"].astype(str)
    df["window"] = (df["time"] // window_size).astype(int)
    return df


def build_feature_frame(raw_df: pd.DataFrame, window_size: int) -> pd.DataFrame:
    df = prepare_log_frame(raw_df, window_size)

    grouped = df.groupby(["ip", "window"]).agg(
        requests_per_window=("endpoint", "count"),
        failed_logins=("status", lambda x: (x == "fail").sum()),
        successful_logins=("status", lambda x: (x == "success").sum()),
        login_attempts=("endpoint", lambda x: (x == "/login").sum()),
        successful_requests=("status", lambda x: (x == "ok").sum()),
        distinct_endpoints=("endpoint", "nunique"),
        unique_user_agents=("user_agent", "nunique"),
    )

    features = grouped.reset_index()
    features["request_rate"] = features["requests_per_window"] / window_size
    features["login_ratio"] = (
        features["login_attempts"] / features["requests_per_window"]
    ).fillna(0)
    features["failed_login_ratio"] = (
        features["failed_logins"] / features["login_attempts"].replace(0, np.nan)
    ).fillna(0)

    return features
