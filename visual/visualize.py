import logging
import os
import time

import matplotlib.pyplot as plt
import pandas as pd
import psycopg2
from psycopg2 import OperationalError

DB_HOST = os.getenv("DB_HOST", "db")
DB_NAME = os.getenv("DB_NAME", "logs")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "admin")
OUTPUT_IMAGE = "output/anomalies.png"
MODEL_COMPARISON_FILE = "output/model_comparison.csv"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("visual")


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

best_threshold_summary = None
comparison_df = None
if os.path.exists(MODEL_COMPARISON_FILE):
    try:
        comparison_df = pd.read_csv(MODEL_COMPARISON_FILE)
        if not comparison_df.empty and {"model", "best_threshold", "best_precision", "best_f1"}.issubset(comparison_df.columns):
            best_row = comparison_df.sort_values("best_f1", ascending=False).iloc[0]
            best_threshold_summary = {
                "model": str(best_row["model"]),
                "threshold": float(best_row["best_threshold"]),
                "precision": float(best_row["best_precision"]),
                "f1": float(best_row["best_f1"]),
            }
    except Exception:
        best_threshold_summary = None

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
            logger.info(
                "No anomalies found in database. Saved fallback metrics chart to output/anomalies.png"
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
    logger.info("No anomalies found in database. Saved placeholder output/anomalies.png")
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

# If runtime DB only contains one model (common when ml service runs a single MODEL_TYPE),
# prefer showing batch evaluation counts from model_comparison.csv so dashboard reflects
# all evaluated models. Use tuned counts (best_true_positives + best_false_positives)
# when available, else fall back to raw true_positives + false_positives.
if models["model_name"].nunique() < 2 and comparison_df is not None and not comparison_df.empty:
    try:
        # Build an estimated anomaly count per model from evaluation results
        comp = comparison_df.copy()
        # prefer tuned counts if present
        if {"best_true_positives", "best_false_positives"}.issubset(comp.columns):
            comp["est_anomaly_count"] = comp["best_true_positives"].fillna(0).astype(int) + comp["best_false_positives"].fillna(0).astype(int)
        else:
            comp["est_anomaly_count"] = comp["true_positives"].fillna(0).astype(int) + comp["false_positives"].fillna(0).astype(int)

        models = comp[["model", "est_anomaly_count"]].rename(columns={"model": "model_name", "est_anomaly_count": "anomaly_count"})
    except Exception:
        # fallback to runtime models if anything goes wrong
        pass

window_min = int(windows["time_window"].min())
windows["window_offset"] = windows["time_window"].astype(int) - window_min
windows["window_label"] = windows["window_offset"].apply(lambda x: f"W+{x}")

fig, axes = plt.subplots(2, 2, figsize=(20, 11), constrained_layout=True)
axes = axes.ravel()

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

summary_ax = axes[3]
summary_ax.set_title("Multi-model evaluation summary")
summary_ax.axis("off")

if comparison_df is not None and not comparison_df.empty:
    display_df = comparison_df.copy()
    display_df = display_df.sort_values("best_f1", ascending=False)
    display_df = display_df[["model", "f1", "best_f1", "false_positives", "best_false_positives"]]

    rows = []
    for _, row in display_df.iterrows():
        rows.append([
            str(row["model"]),
            f"{float(row['f1']):.3f}",
            f"{float(row['best_f1']):.3f}",
            f"{int(row['false_positives'])}",
            f"{int(row['best_false_positives'])}",
        ])

    table = summary_ax.table(
        cellText=rows,
        colLabels=["model", "f1", "best_f1", "fp", "best_fp"],
        cellLoc="center",
        loc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1, 1.5)

    for (r, c), cell in table.get_celld().items():
        if r == 0:
            cell.set_facecolor("#2f4b7c")
            cell.set_text_props(weight="bold", color="white")
        elif r % 2 == 0:
            cell.set_facecolor("#f3f6fb")

    if best_threshold_summary is not None:
        summary_ax.text(
            0.5,
            0.97,
            f"Best tuned model: {best_threshold_summary['model'].upper()} | threshold {best_threshold_summary['threshold']:.4f}",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
            transform=summary_ax.transAxes,
        )
else:
    summary_ax.text(
        0.5,
        0.5,
        "Multi-model summary unavailable\nRun model_comparison.csv generation first",
        ha="center",
        va="center",
        fontsize=12,
    )

total_anomalies = len(df)
unique_ips = df["ip"].nunique()
fig.suptitle(
    f"Detected anomalies: {total_anomalies} records across {unique_ips} IP(s)",
    fontsize=15,
    fontweight="bold",
)

plt.savefig("output/anomalies.png", dpi=160)

logger.info("Saved output/anomalies.png")
