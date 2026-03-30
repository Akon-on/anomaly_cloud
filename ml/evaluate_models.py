import json
import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import (
    accuracy_score,
    auc,
    precision_recall_curve,
    precision_recall_fscore_support,
    roc_curve,
)
from sklearn.neighbors import LocalOutlierFactor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import OneClassSVM

LOG_FILE = os.getenv("LOG_FILE", "/logs/access.log")
LABEL_FILE = os.getenv("LABEL_FILE", "/logs/traffic_labels.jsonl")
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/app/output"))
WINDOW_SIZE = int(os.getenv("EVAL_WINDOW_SIZE", "10"))
CONTAMINATION = float(os.getenv("EVAL_CONTAMINATION", "0.3"))


def format_metric(value):
    if pd.isna(value):
        return "N/A"
    return f"{float(value):.4f}"


def write_markdown_table(df, file_path):
    columns = list(df.columns)
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]

    for _, row in df.iterrows():
        values = [str(row[col]) for col in columns]
        lines.append("| " + " | ".join(values) + " |")

    with open(file_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def load_logs(file_path):
    records = []
    with open(file_path, "r", encoding="utf-8") as handle:
        for line in handle:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    if not records:
        return pd.DataFrame()

    return pd.DataFrame(records)


def load_attack_windows(file_path):
    if not os.path.exists(file_path):
        return set()

    windows = set()
    with open(file_path, "r", encoding="utf-8") as handle:
        for line in handle:
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue

            if item.get("label") != "attack":
                continue

            event_time = item.get("time")
            if event_time is None:
                continue

            windows.add(int(float(event_time) // WINDOW_SIZE))

    return windows


def build_feature_frame(raw_df, attack_windows):
    df = raw_df.copy()
    df["time"] = df["time"].astype(float)
    df["window"] = (df["time"] // WINDOW_SIZE).astype(int)

    grouped = df.groupby(["ip", "window"]).agg(
        requests_per_window=("endpoint", "count"),
        failed_logins=("status", lambda x: (x == "fail").sum()),
        login_attempts=("endpoint", lambda x: (x == "/login").sum()),
    )

    features = grouped.reset_index()

    if attack_windows:
        features["y_true"] = features["window"].isin(attack_windows).astype(int)
        label_source = "traffic_ground_truth"
    else:
        # Fallback for legacy logs without explicit labels.
        features["y_true"] = (features["failed_logins"] > 0).astype(int)
        label_source = "failed_login_proxy"

    return features, label_source


def model_definitions(contamination, n_samples):
    lof_neighbors = max(2, min(20, n_samples - 1))
    return {
        "isolation_forest": IsolationForest(
            n_estimators=100,
            contamination=contamination,
            random_state=42,
        ),
        "lof": LocalOutlierFactor(
            n_neighbors=lof_neighbors,
            contamination=contamination,
        ),
        "ocsvm": make_pipeline(
            StandardScaler(),
            OneClassSVM(nu=contamination, kernel="rbf", gamma="scale"),
        ),
    }


def fit_predict_and_score(name, model, X):
    if name == "lof":
        predictions = model.fit_predict(X)
        anomaly_score = -model.negative_outlier_factor_
        return predictions, anomaly_score

    if name == "ocsvm":
        model.fit(X)
        predictions = model.predict(X)
        anomaly_score = -model.decision_function(X)
        return predictions, anomaly_score

    predictions = model.fit_predict(X)
    anomaly_score = -model.decision_function(X)
    return predictions, anomaly_score


def compute_metrics(y_true, y_pred_binary, score):
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true,
        y_pred_binary,
        average="binary",
        zero_division=0,
    )

    accuracy = accuracy_score(y_true, y_pred_binary)

    roc_auc = np.nan
    pr_auc = np.nan
    roc_data = None
    pr_data = None

    if y_true.nunique() > 1:
        fpr, tpr, _ = roc_curve(y_true, score)
        roc_auc = auc(fpr, tpr)
        roc_data = (fpr, tpr)

        pr_precision, pr_recall, _ = precision_recall_curve(y_true, score)
        pr_auc = auc(pr_recall, pr_precision)
        pr_data = (pr_recall, pr_precision)

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "accuracy": accuracy,
        "roc_auc": roc_auc,
        "pr_auc": pr_auc,
        "roc_data": roc_data,
        "pr_data": pr_data,
    }


def plot_curves(results, output_dir):
    has_roc = False
    plt.figure()
    for model_name, metrics in results.items():
        if metrics["roc_data"] is None:
            continue
        has_roc = True
        fpr, tpr = metrics["roc_data"]
        plt.plot(fpr, tpr, label=f"{model_name} (AUC={metrics['roc_auc']:.3f})")

    plt.plot([0, 1], [0, 1], linestyle="--", linewidth=1)
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title("ROC Curve Comparison")
    if has_roc:
        plt.legend()
    plt.tight_layout()
    plt.savefig(output_dir / "roc_curve.png")
    plt.close()

    has_pr = False
    plt.figure()
    for model_name, metrics in results.items():
        if metrics["pr_data"] is None:
            continue
        has_pr = True
        recall, precision = metrics["pr_data"]
        plt.plot(recall, precision, label=f"{model_name} (AUC={metrics['pr_auc']:.3f})")

    plt.xlabel("Recall")
    plt.ylabel("Precision")
    plt.title("Precision-Recall Curve Comparison")
    if has_pr:
        plt.legend()
    plt.tight_layout()
    plt.savefig(output_dir / "pr_curve.png")
    plt.close()


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not os.path.exists(LOG_FILE):
        raise FileNotFoundError(f"Log file not found: {LOG_FILE}")

    raw_df = load_logs(LOG_FILE)
    if raw_df.empty:
        print("No log records found. Generate traffic first.")
        return

    attack_windows = load_attack_windows(LABEL_FILE)
    features, label_source = build_feature_frame(raw_df, attack_windows)
    if len(features) < 3:
        print("Not enough aggregated windows for model comparison.")
        return

    print(f"Label source: {label_source}")

    X = features[["requests_per_window", "failed_logins", "login_attempts"]]
    y_true = features["y_true"]

    results = {}
    rows = []

    for name, model in model_definitions(CONTAMINATION, len(features)).items():
        predictions, score = fit_predict_and_score(name, model, X)
        y_pred_binary = (predictions == -1).astype(int)

        metrics = compute_metrics(y_true, y_pred_binary, score)
        results[name] = metrics

        rows.append(
            {
                "model": name,
                "precision": metrics["precision"],
                "recall": metrics["recall"],
                "f1": metrics["f1"],
                "accuracy": metrics["accuracy"],
                "roc_auc": metrics["roc_auc"],
                "pr_auc": metrics["pr_auc"],
                "label_source": label_source,
            }
        )

    comparison_df = pd.DataFrame(rows).sort_values("f1", ascending=False)
    comparison_csv = OUTPUT_DIR / "model_comparison.csv"
    comparison_df.to_csv(comparison_csv, index=False)

    display_df = comparison_df.copy()
    for col in ["precision", "recall", "f1", "accuracy", "roc_auc", "pr_auc"]:
        display_df[col] = display_df[col].apply(format_metric)

    comparison_table_txt = OUTPUT_DIR / "model_comparison.txt"
    with open(comparison_table_txt, "w", encoding="utf-8") as handle:
        handle.write(display_df.to_string(index=False))
        handle.write("\n")

    comparison_md = OUTPUT_DIR / "model_comparison.md"
    write_markdown_table(display_df, comparison_md)

    report_txt = OUTPUT_DIR / "model_report.txt"
    with open(report_txt, "w", encoding="utf-8") as handle:
        handle.write("Model Report\n")
        handle.write("============\n\n")
        handle.write(f"Label source: {label_source}\n")
        handle.write(f"Samples: {len(features)}\n")
        handle.write(f"Window size: {WINDOW_SIZE}\n")
        handle.write(f"Contamination: {CONTAMINATION}\n\n")
        handle.write("Model comparison (sorted by F1)\n")
        handle.write("-------------------------------\n")
        handle.write(display_df.to_string(index=False))
        handle.write("\n")

    report_md = OUTPUT_DIR / "model_report.md"
    with open(report_md, "w", encoding="utf-8") as handle:
        handle.write("# Model Report\n\n")
        handle.write(f"- Label source: {label_source}\n")
        handle.write(f"- Samples: {len(features)}\n")
        handle.write(f"- Window size: {WINDOW_SIZE}\n")
        handle.write(f"- Contamination: {CONTAMINATION}\n\n")
        handle.write("## Model Comparison (Sorted by F1)\n\n")
        handle.write(comparison_md.read_text(encoding="utf-8"))

    plot_curves(results, OUTPUT_DIR)

    print("Saved evaluation artifacts:")
    print(f"- {comparison_csv}")
    print(f"- {comparison_table_txt}")
    print(f"- {comparison_md}")
    print(f"- {report_txt}")
    print(f"- {report_md}")
    print(f"- {OUTPUT_DIR / 'roc_curve.png'}")
    print(f"- {OUTPUT_DIR / 'pr_curve.png'}")


if __name__ == "__main__":
    main()
