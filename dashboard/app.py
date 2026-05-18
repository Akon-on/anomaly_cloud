import logging
import os
from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, render_template, send_from_directory

app = Flask(__name__)
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/app/output"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("dashboard")


def read_model_comparison() -> pd.DataFrame:
    csv_path = OUTPUT_DIR / "model_comparison.csv"
    if not csv_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(csv_path)
    except Exception:
        logger.exception("Unable to read model comparison CSV: %s", csv_path)
        return pd.DataFrame()


def safe_float(value, default=0.0):
    if pd.isna(value):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value, default=0):
    if pd.isna(value):
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def read_batch_stats() -> dict:
    """Read batch overall ranking stats."""
    csv_path = OUTPUT_DIR / "batch_overall_ranking.csv"
    if not csv_path.exists():
        return {}
    try:
        df = pd.read_csv(csv_path)
        return df.to_dict(orient="records")
    except Exception:
        logger.exception("Unable to read batch ranking CSV: %s", csv_path)
        return {}


def read_batch_overview() -> dict:
    """Summarize how many scenarios and runs were used for batch results."""
    csv_path = OUTPUT_DIR / "batch_all_runs.csv"
    if not csv_path.exists():
        return {}
    try:
        df = pd.read_csv(csv_path)
        if df.empty or "scenario" not in df.columns or "run" not in df.columns:
            return {}

        scenario_count = int(df["scenario"].nunique())
        run_pairs = df[["scenario", "run"]].drop_duplicates()
        total_runs = int(len(run_pairs))
        runs_per_scenario = int(run_pairs.groupby("scenario").size().mode().iloc[0]) if not run_pairs.empty else 0

        return {
            "scenario_count": scenario_count,
            "runs_per_scenario": runs_per_scenario,
            "total_runs": total_runs,
            "model_evaluations": int(len(df)),
        }
    except Exception:
        logger.exception("Unable to read batch overview CSV: %s", csv_path)
        return {}


def get_overall_best_model() -> dict:
    """Get the overall best model from aggregate batch results."""
    csv_path = OUTPUT_DIR / "batch_overall_ranking.csv"
    if not csv_path.exists():
        return {}
    try:
        df = pd.read_csv(csv_path)
        if df.empty:
            return {}
        # First row is the best ranked model
        best_row = df.iloc[0]
        # Parse f1_score which is formatted as "0.6152 +/- 0.1171"
        f1_str = str(best_row.get("f1_score", "0"))
        f1_value = float(f1_str.split(" ")[0]) if " " in f1_str else float(f1_str)
        return {
            "model": str(best_row.get("model", "unknown")).upper(),
            "f1": f1_value,
        }
    except Exception:
        logger.exception("Unable to determine overall best model from: %s", csv_path)
        return {}


def collect_images() -> list[str]:
    """Collect all PNG images from OUTPUT_DIR, prioritizing key charts."""
    excluded = {
        "single_run_roc_top3.png",
        "single_run_pr_top3.png",
    }
    preferred = [
        "anomalies.png",
        "roc_curve.png",
        "pr_curve.png",
        "batch_average_roc_curve.png",
        "batch_average_pr_curve.png",
        "batch_f1_by_scenario.png",
        "batch_roc_auc_by_scenario.png",
        "batch_pr_auc_by_scenario.png",
        "batch_best_f1_by_scenario.png",
        "batch_ranked_summary_table.png",
        "batch_confusion_matrix_summary.png",
    ]
    available = []
    
    # Add preferred images if they exist
    for name in preferred:
        if name not in excluded and (OUTPUT_DIR / name).exists():
            available.append(name)
    
    # Add any other PNG files not in preferred list
    if OUTPUT_DIR.exists():
        for file in sorted(OUTPUT_DIR.glob("*.png")):
            if file.name not in available and file.name not in excluded:
                available.append(file.name)
    
    return available


@app.get("/")
def index():
    df = read_model_comparison()
    rows = []
    columns = []
    if not df.empty:
        columns = df.columns.tolist()
        rows = df.to_dict(orient="records")

    batch_stats = read_batch_stats()
    batch_overview = read_batch_overview()

    return render_template(
        "index.html",
        columns=columns,
        rows=rows,
        images=collect_images(),
        batch_stats=batch_stats,
        batch_overview=batch_overview,
    )


@app.get("/api/dashboard")
def api_dashboard():
    """Comprehensive dashboard data endpoint."""
    df = read_model_comparison()
    if df.empty:
        return jsonify({
            "models": [],
            "batch_stats": [],
            "batch_overview": {},
            "images": collect_images(),
            "summary": None
        })

    # Build model details with threshold improvements
    models = []
    for _, row in df.iterrows():
        model_name = str(row.get("model", "unknown"))
        f1_baseline = safe_float(row.get("f1", 0))
        f1_tuned = safe_float(row.get("best_f1", f1_baseline), f1_baseline)
        f1_improvement = ((f1_tuned - f1_baseline) / abs(f1_baseline)) * 100 if f1_baseline != 0 else 0

        fp_baseline = safe_int(row.get("false_positives", 0))
        fp_tuned = safe_int(row.get("best_false_positives", fp_baseline), fp_baseline)
        fp_reduction = ((fp_baseline - fp_tuned) / max(fp_baseline, 1)) * 100

        models.append({
            "model": model_name,
            "f1": round(f1_baseline, 4),
            "best_f1": round(f1_tuned, 4),
            "f1_improvement_pct": round(f1_improvement, 2),
            "precision": round(safe_float(row.get("precision", 0)), 4),
            "recall": round(safe_float(row.get("recall", 0)), 4),
            "accuracy": round(safe_float(row.get("accuracy", 0)), 4),
            "roc_auc": round(safe_float(row.get("roc_auc", 0)), 4),
            "pr_auc": round(safe_float(row.get("pr_auc", 0)), 4),
            "best_precision": round(safe_float(row.get("best_precision", 0)), 4),
            "best_recall": round(safe_float(row.get("best_recall", 0)), 4),
            "best_threshold": round(safe_float(row.get("best_threshold", 0)), 4),
            "false_positives": fp_baseline,
            "best_false_positives": fp_tuned,
            "fp_reduction_pct": round(fp_reduction, 2),
            "true_positives": safe_int(row.get("true_positives", 0)),
            "false_negatives": safe_int(row.get("false_negatives", 0)),
            "label_source": str(row.get("label_source", "unknown")),
        })

    # Best model for each metric
    if models:
        best_model_from_latest = max(models, key=lambda x: x["best_f1"])
        summary = {
            "best_model": best_model_from_latest["model"],
            "best_f1": best_model_from_latest["best_f1"],
            "total_models": len(models),
        }
    else:
        summary = None

    # Override with overall best model from batch results
    overall_best = get_overall_best_model()
    if overall_best:
        summary = {
            "best_model": overall_best["model"],
            "best_f1": overall_best["f1"],
            "total_models": len(models),
            "note": "Best model from aggregate batch results across all runs",
        }

    batch_stats = read_batch_stats()
    batch_overview = read_batch_overview()

    return jsonify({
        "models": models,
        "batch_stats": batch_stats,
        "batch_overview": batch_overview,
        "images": collect_images(),
        "summary": summary,
    })


@app.get("/api/latest")
def api_latest():
    df = read_model_comparison()
    if df.empty:
        return jsonify({"rows": [], "images": collect_images()})

    numeric_cols = [
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
    ]
    payload = []
    for _, row in df.iterrows():
        item = {
            "model": row.get("model", "unknown"),
            "label_source": row.get("label_source", "unknown"),
            "evaluation_mode": row.get("evaluation_mode", "unknown"),
        }
        for col in numeric_cols:
            value = row.get(col)
            if pd.isna(value):
                item[col] = None
            else:
                item[col] = float(value)
        payload.append(item)

    return jsonify({"rows": payload, "images": collect_images()})


@app.get("/output/<path:filename>")
def output_file(filename: str):
    return send_from_directory(OUTPUT_DIR, filename)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
