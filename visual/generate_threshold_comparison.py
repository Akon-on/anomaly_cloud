#!/usr/bin/env python3
"""Generate threshold-tuning comparison from the latest batch outputs."""

import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def resolve_output_dir() -> Path:
    candidates = []
    if os.getenv("OUTPUT_DIR"):
        candidates.append(Path(os.getenv("OUTPUT_DIR")))
    candidates.extend(
        [
            Path("/app/output"),
            Path(__file__).resolve().parent.parent / "output",
            Path.cwd() / "output",
        ]
    )

    for candidate in candidates:
        if (candidate / "batch_all_runs.csv").exists():
            return candidate

    return candidates[0]


def choose_model(df: pd.DataFrame, output_dir: Path) -> str:
    requested = os.getenv("THRESHOLD_MODEL")
    if requested:
        requested = requested.strip()
        if requested in set(df["model"]):
            return requested
        raise ValueError(f"THRESHOLD_MODEL={requested!r} not found in batch_all_runs.csv")

    ranking_path = output_dir / "batch_overall_ranking.csv"
    if ranking_path.exists():
        ranking = pd.read_csv(ranking_path)
        if not ranking.empty and "model" in ranking.columns:
            return str(ranking.iloc[0]["model"])

    return (
        df.groupby("model", as_index=False)["f1"]
        .mean()
        .sort_values("f1", ascending=False)
        .iloc[0]["model"]
    )


def mean_metric(df: pd.DataFrame, column: str) -> float:
    values = pd.to_numeric(df[column], errors="coerce").dropna()
    if values.empty:
        return 0.0
    return float(values.mean())


def percent_delta(before: float, after: float) -> str:
    if before == 0:
        return "N/A"
    value = ((after - before) / abs(before)) * 100
    return f"{value:+.0f}%"


def count_delta(before: float, after: float) -> str:
    if before == 0:
        return "N/A"
    value = ((before - after) / abs(before)) * 100
    return f"-{value:.0f}%" if value >= 0 else f"+{abs(value):.0f}%"


def add_bar_labels(ax, bars, values, formatter, tuned_note=None):
    for index, (bar, value) in enumerate(zip(bars, values)):
        height = bar.get_height()
        offset = 0.02 if max(values) <= 1.2 else max(values) * 0.02
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            height + offset,
            formatter(value),
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
        )
        if index == 1 and tuned_note:
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                max(height * 0.55, 0.03),
                tuned_note,
                ha="center",
                va="center",
                fontsize=9,
                color="white",
                fontweight="bold",
                bbox={"boxstyle": "round", "facecolor": "#263238", "alpha": 0.75},
            )


def main() -> None:
    output_dir = resolve_output_dir()
    batch_path = output_dir / "batch_all_runs.csv"
    if not batch_path.exists():
        raise FileNotFoundError(f"Missing batch input: {batch_path}")

    df = pd.read_csv(batch_path)
    for column in [
        "precision",
        "recall",
        "f1",
        "false_positives",
        "false_negatives",
        "best_precision",
        "best_recall",
        "best_f1",
        "best_false_positives",
        "best_false_negatives",
    ]:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    model_name = choose_model(df, output_dir)
    model_df = df[df["model"] == model_name].copy()
    if model_df.empty:
        raise ValueError(f"No rows found for model={model_name}")

    display_name = model_name.replace("_", " ").upper()
    labels = [f"{display_name}\nDefault", f"{display_name}\nThreshold-Tuned"]
    precision = [
        mean_metric(model_df, "precision"),
        mean_metric(model_df, "best_precision"),
    ]
    recall = [
        mean_metric(model_df, "recall"),
        mean_metric(model_df, "best_recall"),
    ]
    f1_score = [
        mean_metric(model_df, "f1"),
        mean_metric(model_df, "best_f1"),
    ]
    false_positives = [
        mean_metric(model_df, "false_positives"),
        mean_metric(model_df, "best_false_positives"),
    ]
    false_negatives = [
        mean_metric(model_df, "false_negatives"),
        mean_metric(model_df, "best_false_negatives"),
    ]

    color_default = "#FF7F7F"
    color_tuned = "#6BD17D"

    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    fig.suptitle(
        f"Threshold Tuning Impact for {display_name}: Default vs Calibrated Detection\n"
        f"Batch averages across {model_df['scenario'].nunique()} scenarios and {len(model_df)} model evaluations",
        fontsize=15,
        fontweight="bold",
        y=1.00,
    )

    bar_colors = [color_default, color_tuned]

    ax = axes[0, 0]
    bars = ax.bar(labels, precision, color=bar_colors, alpha=0.85, edgecolor="black")
    ax.set_ylabel("Precision", fontweight="bold")
    ax.set_ylim(0, 1.05)
    ax.set_title("Precision (Higher is Better)", fontweight="bold")
    add_bar_labels(ax, bars, precision, lambda value: f"{value:.1%}", percent_delta(*precision))
    ax.grid(axis="y", alpha=0.25)

    ax = axes[0, 1]
    bars = ax.bar(labels, recall, color=bar_colors, alpha=0.85, edgecolor="black")
    ax.set_ylabel("Recall", fontweight="bold")
    ax.set_ylim(0, 1.05)
    ax.set_title("Recall (Attack Detection Rate)", fontweight="bold")
    add_bar_labels(ax, bars, recall, lambda value: f"{value:.1%}", percent_delta(*recall))
    ax.grid(axis="y", alpha=0.25)

    ax = axes[0, 2]
    bars = ax.bar(labels, f1_score, color=bar_colors, alpha=0.85, edgecolor="black")
    ax.set_ylabel("F1-Score", fontweight="bold")
    ax.set_ylim(0, 1.05)
    ax.set_title("F1-Score (Harmonic Mean)", fontweight="bold")
    add_bar_labels(ax, bars, f1_score, lambda value: f"{value:.3f}", percent_delta(*f1_score))
    ax.grid(axis="y", alpha=0.25)

    ax = axes[1, 0]
    bars = ax.bar(labels, false_positives, color=bar_colors, alpha=0.85, edgecolor="black")
    ax.set_ylabel("Average Count", fontweight="bold")
    ax.set_title("False Positives per Model Evaluation", fontweight="bold")
    add_bar_labels(
        ax,
        bars,
        false_positives,
        lambda value: f"{value:.1f}",
        count_delta(*false_positives),
    )
    ax.grid(axis="y", alpha=0.25)

    ax = axes[1, 1]
    bars = ax.bar(labels, false_negatives, color=bar_colors, alpha=0.85, edgecolor="black")
    ax.set_ylabel("Average Count", fontweight="bold")
    ax.set_title("False Negatives per Model Evaluation", fontweight="bold")
    upper = max(5, max(false_negatives) * 1.4)
    ax.set_ylim(0, upper)
    add_bar_labels(
        ax,
        bars,
        false_negatives,
        lambda value: f"{value:.1f}",
        count_delta(*false_negatives),
    )
    ax.grid(axis="y", alpha=0.25)

    ax = axes[1, 2]
    ax.axis("off")
    summary_data = [
        ["Metric", "Default", "Tuned", "Change"],
        ["Precision", f"{precision[0]:.1%}", f"{precision[1]:.1%}", percent_delta(*precision)],
        ["Recall", f"{recall[0]:.1%}", f"{recall[1]:.1%}", percent_delta(*recall)],
        ["F1-Score", f"{f1_score[0]:.3f}", f"{f1_score[1]:.3f}", percent_delta(*f1_score)],
        ["False Pos.", f"{false_positives[0]:.1f}", f"{false_positives[1]:.1f}", count_delta(*false_positives)],
        ["False Neg.", f"{false_negatives[0]:.1f}", f"{false_negatives[1]:.1f}", count_delta(*false_negatives)],
    ]
    table = ax.table(
        cellText=summary_data,
        cellLoc="center",
        loc="center",
        colWidths=[0.25, 0.25, 0.25, 0.25],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 2.0)
    for col in range(4):
        table[(0, col)].set_facecolor("#333333")
        table[(0, col)].set_text_props(weight="bold", color="white")
    for row in range(1, len(summary_data)):
        for col in range(4):
            if row % 2 == 0:
                table[(row, col)].set_facecolor("#f0f0f0")
            if col == 3:
                table[(row, col)].set_text_props(weight="bold")

    plt.tight_layout()
    output_name = os.getenv("THRESHOLD_OUTPUT_NAME")
    if not output_name:
        output_name = (
            f"threshold_tuning_comparison_{model_name}.png"
            if os.getenv("THRESHOLD_MODEL")
            else "threshold_tuning_comparison.png"
        )
    output_path = output_dir / output_name
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    print(f"Saved: {output_path}")
    print(f"Model: {model_name}")
    print(f"F1: {f1_score[0]:.4f} -> {f1_score[1]:.4f}")
    print(f"False positives: {false_positives[0]:.1f} -> {false_positives[1]:.1f}")


if __name__ == "__main__":
    main()
