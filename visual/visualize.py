import psycopg2
import pandas as pd
import matplotlib.pyplot as plt
import os
import time
from psycopg2 import OperationalError

DB_HOST = os.getenv("DB_HOST", "db")
DB_NAME = os.getenv("DB_NAME", "logs")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "admin")
OUTPUT_IMAGE = "output/anomalies.png"
MODEL_COMPARISON_FILE = "output/model_comparison.csv"


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

# Connect to DB
conn = connect_with_retry()

query = """
SELECT
    ip,
    time_window,
    requests_per_window,
    failed_logins,
    COALESCE(model_name, 'unknown') AS model_name
FROM anomalies;
"""

df = pd.read_sql(query, conn)

conn.close()

if df.empty:
    plt.figure(figsize=(10, 5))

    if os.path.exists(MODEL_COMPARISON_FILE):
        model_df = pd.read_csv(MODEL_COMPARISON_FILE)
        if not model_df.empty and "model" in model_df.columns:
            models = model_df["model"].astype(str).tolist()
            f1_vals = model_df["f1"].astype(float).tolist()
            roc_vals = model_df["roc_auc"].astype(float).tolist()
            pr_vals = model_df["pr_auc"].astype(float).tolist()

            x = range(len(models))
            width = 0.25

            plt.bar([i - width for i in x], f1_vals, width=width, label="F1")
            plt.bar(x, roc_vals, width=width, label="ROC-AUC")
            plt.bar([i + width for i in x], pr_vals, width=width, label="PR-AUC")
            plt.xticks(list(x), models)
            plt.ylim(0, 1)
            plt.title("No DB anomalies yet: latest model metrics")
            plt.xlabel("Model")
            plt.ylabel("Score")
            plt.grid(axis="y", alpha=0.3)
            plt.legend()
            plt.tight_layout()
            plt.savefig(OUTPUT_IMAGE, dpi=160)
            print(
                "No anomalies found in database. "
                "Saved fallback metrics chart to output/anomalies.png"
            )
            raise SystemExit(0)

    plt.text(
        0.5,
        0.5,
        "No anomalies found in database\nRun traffic + ML detection first",
        ha="center",
        va="center",
        fontsize=12
    )
    plt.axis("off")
    plt.title("Detected anomalies")
    plt.tight_layout()
    plt.savefig(OUTPUT_IMAGE, dpi=160)
    print("No anomalies found in database. Saved placeholder output/anomalies.png")
    raise SystemExit(0)

point_counts = (
    df.groupby(
        ["requests_per_window", "failed_logins", "model_name"],
        as_index=False
    )
    .size()
    .rename(columns={"size": "point_count"})
)

windows = (
    df.groupby("time_window", as_index=False)
    .size()
    .rename(columns={"size": "anomaly_count"})
    .sort_values("time_window")
)

models = (
    df.groupby("model_name", as_index=False)
    .size()
    .rename(columns={"size": "anomaly_count"})
)

all_models = ["isolation_forest", "lof", "ocsvm"]
for model_name in df["model_name"].unique().tolist():
    if model_name not in all_models:
        all_models.append(model_name)

models = (
    models.set_index("model_name")
    .reindex(all_models, fill_value=0)
    .reset_index()
)

window_min = int(windows["time_window"].min())
windows["window_offset"] = windows["time_window"].astype(int) - window_min
windows["window_label"] = windows["window_offset"].apply(lambda x: f"W+{x}")

fig, axes = plt.subplots(1, 3, figsize=(18, 5), constrained_layout=True)

for model_name, model_points in point_counts.groupby("model_name"):
    axes[0].scatter(
        model_points["requests_per_window"],
        model_points["failed_logins"],
        s=60 + model_points["point_count"] * 25,
        alpha=0.8,
        label=model_name
    )

axes[0].set_xlabel("Requests per window")
axes[0].set_ylabel("Failed logins")
axes[0].set_title("Anomaly feature space")
axes[0].grid(alpha=0.3)
axes[0].legend(title="Model")

axes[1].bar(
    windows["window_label"],
    windows["anomaly_count"],
    color="#3f7f93"
)
axes[1].set_title("Anomalies per time window")
axes[1].set_xlabel("Relative window")
axes[1].set_ylabel("Count")
axes[1].tick_params(axis="x", rotation=45)

model_colors = {
    "isolation_forest": "#4C78A8",
    "lof": "#F58518",
    "ocsvm": "#54A24B"
}
bar_colors = [model_colors.get(name, "#9b6db3") for name in models["model_name"]]

axes[2].bar(
    models["model_name"],
    models["anomaly_count"],
    color=bar_colors
)
axes[2].set_title("Anomalies by model")
axes[2].set_xlabel("Model")
axes[2].set_ylabel("Count")
axes[2].tick_params(axis="x", rotation=30)

total_anomalies = len(df)
unique_ips = df["ip"].nunique()
fig.suptitle(
    f"Detected anomalies: {total_anomalies} records across {unique_ips} IP(s)",
    fontsize=13
)

plt.savefig("output/anomalies.png", dpi=160)

print("Saved output/anomalies.png")
