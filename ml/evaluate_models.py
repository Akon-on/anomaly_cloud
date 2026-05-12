import json
import logging
import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import (
    accuracy_score,
    auc,
    confusion_matrix,
    precision_recall_curve,
    precision_recall_fscore_support,
    roc_curve,
)
from sklearn.neighbors import LocalOutlierFactor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import OneClassSVM

from feature_engineering import FEATURE_COLUMNS, build_feature_frame as build_base_feature_frame

LOG_FILE = os.getenv("LOG_FILE", "/logs/access.log")
LABEL_FILE = os.getenv("LABEL_FILE", "/logs/traffic_labels.jsonl")
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/app/output"))
WINDOW_SIZE = int(os.getenv("EVAL_WINDOW_SIZE", "10"))
CONTAMINATION = float(os.getenv("EVAL_CONTAMINATION", "0.3"))
MIN_BASELINE_WINDOWS = int(os.getenv("EVAL_MIN_BASELINE_WINDOWS", "3"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("ml_eval")


def format_metric(value: object) -> str:
    if pd.isna(value):
        return "N/A"
    return f"{float(value):.4f}"


def write_markdown_table(df: pd.DataFrame, file_path: Path) -> None:
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


def load_logs(file_path: str) -> pd.DataFrame:
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


def load_label_targets(
    file_path: str,
) -> tuple[set[int], set[int], set[tuple[str, int]], set[tuple[str, int]]]:
    if not os.path.exists(file_path):
        return set(), set(), set(), set()

    attack_windows = set()
    normal_windows = set()
    attack_pairs = set()
    normal_pairs = set()
    with open(file_path, "r", encoding="utf-8") as handle:
        for line in handle:
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue

            label = item.get("label")
            event_time = item.get("time")
            if label not in {"normal", "attack"} or event_time is None:
                continue

            window = int(float(event_time) // WINDOW_SIZE)
            client_ip = item.get("client_ip")
            if label == "attack":
                attack_windows.add(window)
                if client_ip:
                    attack_pairs.add((client_ip, window))
            else:
                normal_windows.add(window)
                if client_ip:
                    normal_pairs.add((client_ip, window))

    return attack_windows, normal_windows, attack_pairs, normal_pairs


def build_feature_frame(
    raw_df: pd.DataFrame,
    attack_windows: set[int],
    attack_pairs: set[tuple[str, int]],
) -> tuple[pd.DataFrame, str]:
    features = build_base_feature_frame(raw_df, WINDOW_SIZE)

    if attack_pairs:
        features["y_true"] = features.apply(
            lambda row: int((row["ip"], int(row["window"])) in attack_pairs),
            axis=1,
        )
        if features["y_true"].sum() > 0:
            label_source = "traffic_ground_truth_ip_window"
        else:
            features["y_true"] = features["window"].isin(attack_windows).astype(int)
            label_source = "traffic_ground_truth_window_fallback"
    elif attack_windows:
        features["y_true"] = features["window"].isin(attack_windows).astype(int)
        label_source = "traffic_ground_truth"
    else:
        # Fallback for legacy logs without explicit labels.
        features["y_true"] = (features["failed_logins"] > 0).astype(int)
        label_source = "failed_login_proxy"

    return features, label_source


def select_training_frame(
    features: pd.DataFrame,
    attack_windows: set[int],
    normal_windows: set[int],
) -> tuple[pd.DataFrame, str]:
    if attack_windows:
        first_attack_window = min(attack_windows)
        baseline_mask = (
            features["window"].isin(normal_windows)
            & ~features["window"].isin(attack_windows)
            & (features["window"] < first_attack_window)
        )
        training = features[baseline_mask]

        if len(training) < MIN_BASELINE_WINDOWS:
            training = features[features["y_true"] == 0]

        if len(training) >= MIN_BASELINE_WINDOWS:
            return training, "warmup_normal_baseline"

    return features, "in_sample_unsupervised"


def model_definitions(contamination: float, n_samples: int) -> dict[str, object]:
    lof_neighbors = max(2, min(20, n_samples - 1))
    return {
        "isolation_forest": IsolationForest(
            n_estimators=100,
            contamination=contamination,
            random_state=42,
        ),
        "isolation_forest_tuned": IsolationForest(
            n_estimators=300,
            max_samples="auto",
            contamination=contamination,
            bootstrap=True,
            random_state=42,
        ),
        "lof": LocalOutlierFactor(
            n_neighbors=lof_neighbors,
            contamination=contamination,
            novelty=True,
        ),
        "ocsvm": make_pipeline(
            StandardScaler(),
            OneClassSVM(nu=contamination, kernel="rbf", gamma="scale"),
        ),
    }


def fit_predict_and_score(
    model: object,
    X_train: pd.DataFrame,
    X_eval: pd.DataFrame,
) -> tuple[np.ndarray, np.ndarray]:
    if isinstance(model, LocalOutlierFactor):
        X_train = X_train.to_numpy()
        X_eval = X_eval.to_numpy()

    model.fit(X_train)
    predictions = model.predict(X_eval)
    anomaly_score = -model.decision_function(X_eval)
    return predictions, anomaly_score


def compute_metrics(
    y_true: pd.Series,
    y_pred_binary: pd.Series,
    score: np.ndarray,
) -> dict[str, object]:
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true,
        y_pred_binary,
        average="binary",
        zero_division=0,
    )

    accuracy = accuracy_score(y_true, y_pred_binary)
    tn, fp, fn, tp = confusion_matrix(
        y_true,
        y_pred_binary,
        labels=[0, 1],
    ).ravel()

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
        "true_negatives": tn,
        "false_positives": fp,
        "false_negatives": fn,
        "true_positives": tp,
        "roc_auc": roc_auc,
        "pr_auc": pr_auc,
        "roc_data": roc_data,
        "pr_data": pr_data,
    }


def compute_best_f1_threshold(
    y_true: pd.Series,
    score: np.ndarray,
) -> dict[str, object]:
    if y_true.nunique() <= 1:
        return {
            "best_threshold": np.nan,
            "best_precision": np.nan,
            "best_recall": np.nan,
            "best_f1": np.nan,
            "best_true_negatives": np.nan,
            "best_false_positives": np.nan,
            "best_false_negatives": np.nan,
            "best_true_positives": np.nan,
        }

    precision, recall, thresholds = precision_recall_curve(y_true, score)
    if len(thresholds) == 0:
        return {
            "best_threshold": np.nan,
            "best_precision": np.nan,
            "best_recall": np.nan,
            "best_f1": np.nan,
            "best_true_negatives": np.nan,
            "best_false_positives": np.nan,
            "best_false_negatives": np.nan,
            "best_true_positives": np.nan,
        }

    f1_scores = []
    for p_value, r_value in zip(precision[:-1], recall[:-1]):
        denominator = p_value + r_value
        f1_scores.append(0 if denominator == 0 else 2 * p_value * r_value / denominator)

    best_index = int(np.argmax(f1_scores))
    best_threshold = thresholds[best_index]
    tuned_pred = (score >= best_threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, tuned_pred, labels=[0, 1]).ravel()

    return {
        "best_threshold": best_threshold,
        "best_precision": precision[best_index],
        "best_recall": recall[best_index],
        "best_f1": f1_scores[best_index],
        "best_true_negatives": tn,
        "best_false_positives": fp,
        "best_false_negatives": fn,
        "best_true_positives": tp,
    }


def compute_feature_importance(
    model_name: str,
    model: object,
    X_eval: pd.DataFrame,
    score: np.ndarray,
) -> pd.DataFrame:
    # Tree-based model importance when available.
    if hasattr(model, "feature_importances_"):
        values = np.asarray(model.feature_importances_, dtype=float)
    else:
        # Correlation-based proxy importance for models without native feature importance.
        values = []
        for col in X_eval.columns:
            col_values = X_eval[col].to_numpy(dtype=float)
            if np.std(col_values) == 0 or np.std(score) == 0:
                values.append(0.0)
                continue
            corr = np.corrcoef(col_values, score)[0, 1]
            if np.isnan(corr):
                corr = 0.0
            values.append(abs(float(corr)))
        values = np.asarray(values, dtype=float)

    total = values.sum()
    if total > 0:
        values = values / total

    return pd.DataFrame(
        {
            "model": model_name,
            "feature": list(X_eval.columns),
            "importance": values,
        }
    ).sort_values("importance", ascending=False)


def plot_curves(results: dict[str, dict[str, object]], output_dir: Path) -> None:
    # --- ROC: full set ---
    roc_entries = []
    for model_name, metrics in results.items():
        if metrics.get("roc_data") is None:
            continue
        fpr, tpr = metrics["roc_data"]
        roc_entries.append((model_name, metrics.get("roc_auc", 0.0), fpr, tpr))

    if roc_entries:
        # Full comparison (all models)
        plt.figure()
        for model_name, auc_val, fpr, tpr in roc_entries:
            plt.plot(fpr, tpr, label=f"{model_name} (AUC={auc_val:.3f})")
        plt.plot([0, 1], [0, 1], linestyle="--", linewidth=1)
        plt.xlabel("False Positive Rate")
        plt.ylabel("True Positive Rate")
        plt.title("Single Run ROC Curve Comparison (All Models)")
        plt.legend()
        plt.tight_layout()
        plt.savefig(output_dir / "roc_curve.png")
        plt.close()

    # --- PR: full set ---
    pr_entries = []
    for model_name, metrics in results.items():
        if metrics.get("pr_data") is None:
            continue
        recall, precision = metrics["pr_data"]
        pr_entries.append((model_name, metrics.get("pr_auc", 0.0), recall, precision))

    if pr_entries:
        # Full comparison (all models)
        plt.figure()
        for model_name, auc_val, recall, precision in pr_entries:
            plt.plot(recall, precision, label=f"{model_name} (AUC={auc_val:.3f})")
        plt.xlabel("Recall")
        plt.ylabel("Precision")
        plt.title("Single Run Precision-Recall Curve Comparison (All Models)")
        plt.legend()
        plt.tight_layout()
        plt.savefig(output_dir / "pr_curve.png")
        plt.close()


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not os.path.exists(LOG_FILE):
        raise FileNotFoundError(f"Log file not found: {LOG_FILE}")

    raw_df = load_logs(LOG_FILE)
    if raw_df.empty:
        logger.warning("No log records found. Generate traffic first.")
        return

    attack_windows, normal_windows, attack_pairs, normal_pairs = load_label_targets(LABEL_FILE)
    features, label_source = build_feature_frame(raw_df, attack_windows, attack_pairs)
    if len(features) < 3:
        logger.warning("Not enough aggregated windows for model comparison.")
        return

    logger.info("Label source: %s", label_source)

    training_features, evaluation_mode = select_training_frame(
        features,
        attack_windows,
        normal_windows,
    )
    X_train = training_features[FEATURE_COLUMNS]
    X_eval = features[FEATURE_COLUMNS]
    y_true = features["y_true"]

    logger.info("Evaluation mode: %s", evaluation_mode)
    logger.info("Training samples: %s", len(training_features))

    results = {}
    rows = []
    prediction_map = {}
    score_map = {}
    importance_frames = []

    for name, model in model_definitions(CONTAMINATION, len(training_features)).items():
        predictions, score = fit_predict_and_score(model, X_train, X_eval)
        y_pred_binary = (predictions == -1).astype(int)
        prediction_map[name] = y_pred_binary
        score_map[name] = score

        metrics = compute_metrics(y_true, y_pred_binary, score)
        threshold_metrics = compute_best_f1_threshold(y_true, score)
        importance_frames.append(compute_feature_importance(name, model, X_eval, score))
        results[name] = metrics

        rows.append(
            {
                "model": name,
                "precision": metrics["precision"],
                "recall": metrics["recall"],
                "f1": metrics["f1"],
                "accuracy": metrics["accuracy"],
                "true_negatives": metrics["true_negatives"],
                "false_positives": metrics["false_positives"],
                "false_negatives": metrics["false_negatives"],
                "true_positives": metrics["true_positives"],
                "roc_auc": metrics["roc_auc"],
                "pr_auc": metrics["pr_auc"],
                "best_threshold": threshold_metrics["best_threshold"],
                "best_precision": threshold_metrics["best_precision"],
                "best_recall": threshold_metrics["best_recall"],
                "best_f1": threshold_metrics["best_f1"],
                "best_true_negatives": threshold_metrics["best_true_negatives"],
                "best_false_positives": threshold_metrics["best_false_positives"],
                "best_false_negatives": threshold_metrics["best_false_negatives"],
                "best_true_positives": threshold_metrics["best_true_positives"],
                "label_source": label_source,
                "evaluation_mode": evaluation_mode,
                "train_samples": len(training_features),
            }
        )

    # Majority-vote ensemble from the three baseline unsupervised models.
    ensemble_members = ["isolation_forest", "lof", "ocsvm"]
    if all(name in prediction_map for name in ensemble_members):
        stacked_preds = np.vstack([prediction_map[name] for name in ensemble_members])
        ensemble_pred = (stacked_preds.sum(axis=0) >= 2).astype(int)

        stacked_scores = np.vstack([score_map[name] for name in ensemble_members])
        ensemble_score = stacked_scores.mean(axis=0)

        ensemble_metrics = compute_metrics(y_true, pd.Series(ensemble_pred), ensemble_score)
        ensemble_threshold = compute_best_f1_threshold(y_true, ensemble_score)
        results["ensemble_majority_vote"] = ensemble_metrics

        rows.append(
            {
                "model": "ensemble_majority_vote",
                "precision": ensemble_metrics["precision"],
                "recall": ensemble_metrics["recall"],
                "f1": ensemble_metrics["f1"],
                "accuracy": ensemble_metrics["accuracy"],
                "true_negatives": ensemble_metrics["true_negatives"],
                "false_positives": ensemble_metrics["false_positives"],
                "false_negatives": ensemble_metrics["false_negatives"],
                "true_positives": ensemble_metrics["true_positives"],
                "roc_auc": ensemble_metrics["roc_auc"],
                "pr_auc": ensemble_metrics["pr_auc"],
                "best_threshold": ensemble_threshold["best_threshold"],
                "best_precision": ensemble_threshold["best_precision"],
                "best_recall": ensemble_threshold["best_recall"],
                "best_f1": ensemble_threshold["best_f1"],
                "best_true_negatives": ensemble_threshold["best_true_negatives"],
                "best_false_positives": ensemble_threshold["best_false_positives"],
                "best_false_negatives": ensemble_threshold["best_false_negatives"],
                "best_true_positives": ensemble_threshold["best_true_positives"],
                "label_source": label_source,
                "evaluation_mode": evaluation_mode,
                "train_samples": len(training_features),
            }
        )

        importance_frames.append(
            compute_feature_importance(
                "ensemble_majority_vote",
                object(),
                X_eval,
                ensemble_score,
            )
        )

    comparison_df = pd.DataFrame(rows).sort_values("f1", ascending=False)
    comparison_csv = OUTPUT_DIR / "model_comparison.csv"
    comparison_df.to_csv(comparison_csv, index=False)

    display_df = comparison_df.copy()
    for col in [
        "precision",
        "recall",
        "f1",
        "accuracy",
        "roc_auc",
        "pr_auc",
        "best_threshold",
        "best_precision",
        "best_recall",
        "best_f1",
    ]:
        display_df[col] = display_df[col].apply(format_metric)

    comparison_table_txt = OUTPUT_DIR / "model_comparison.txt"
    with open(comparison_table_txt, "w", encoding="utf-8") as handle:
        handle.write(display_df.to_string(index=False))
        handle.write("\n")

    comparison_md = OUTPUT_DIR / "model_comparison.md"
    write_markdown_table(display_df, comparison_md)

    feature_importance_df = pd.concat(importance_frames, ignore_index=True)
    feature_importance_csv = OUTPUT_DIR / "feature_importance.csv"
    feature_importance_df.to_csv(feature_importance_csv, index=False)

    feature_importance_display = feature_importance_df.copy()
    feature_importance_display["importance"] = feature_importance_display["importance"].apply(format_metric)
    feature_importance_md = OUTPUT_DIR / "feature_importance.md"
    write_markdown_table(feature_importance_display, feature_importance_md)

    report_txt = OUTPUT_DIR / "model_report.txt"
    with open(report_txt, "w", encoding="utf-8") as handle:
        handle.write("Model Report\n")
        handle.write("============\n\n")
        handle.write(f"Label source: {label_source}\n")
        handle.write(f"Evaluation mode: {evaluation_mode}\n")
        handle.write(f"Training samples: {len(training_features)}\n")
        handle.write(f"Samples: {len(features)}\n")
        handle.write(f"Window size: {WINDOW_SIZE}\n")
        handle.write(f"Contamination: {CONTAMINATION}\n\n")
        handle.write("Features\n")
        handle.write("--------\n")
        handle.write(", ".join(FEATURE_COLUMNS))
        handle.write("\n\n")
        handle.write("Model comparison (sorted by F1)\n")
        handle.write("-------------------------------\n")
        handle.write(display_df.to_string(index=False))
        handle.write("\n")

    report_md = OUTPUT_DIR / "model_report.md"
    with open(report_md, "w", encoding="utf-8") as handle:
        handle.write("# Model Report\n\n")
        handle.write(f"- Label source: {label_source}\n")
        handle.write(f"- Evaluation mode: {evaluation_mode}\n")
        handle.write(f"- Training samples: {len(training_features)}\n")
        handle.write(f"- Samples: {len(features)}\n")
        handle.write(f"- Window size: {WINDOW_SIZE}\n")
        handle.write(f"- Contamination: {CONTAMINATION}\n\n")
        handle.write("- Features: " + ", ".join(FEATURE_COLUMNS) + "\n\n")
        handle.write("## Model Comparison (Sorted by F1)\n\n")
        handle.write(comparison_md.read_text(encoding="utf-8"))

    plot_curves(results, OUTPUT_DIR)

    logger.info("Saved evaluation artifacts:")
    logger.info("- %s", comparison_csv)
    logger.info("- %s", comparison_table_txt)
    logger.info("- %s", comparison_md)
    logger.info("- %s", feature_importance_csv)
    logger.info("- %s", feature_importance_md)
    logger.info("- %s", report_txt)
    logger.info("- %s", report_md)
    logger.info("- %s", OUTPUT_DIR / "roc_curve.png")
    logger.info("- %s", OUTPUT_DIR / "pr_curve.png")


if __name__ == "__main__":
    main()
