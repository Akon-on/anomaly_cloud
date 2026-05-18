from pathlib import Path
import os
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


OUTPUT_DIR = Path("output")
ALL_RUNS = OUTPUT_DIR / "batch_all_runs.csv"
MAIN_ML_MODELS = [
    "isolation_forest",
    "lof",
    "ocsvm",
]
EXTRA_MODELS = [
    "rule_based_baseline",
    "isolation_forest_tuned",
    "ensemble_majority_vote",
]
INCLUDE_EXTRA_MODELS = os.getenv("BATCH_INCLUDE_EXTRA_MODELS", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
DISPLAY_MODELS = MAIN_ML_MODELS + (EXTRA_MODELS if INCLUDE_EXTRA_MODELS else [])
MODEL_LABELS = {
    "rule_based_baseline": "Rule",
    "lof": "LOF",
    "ocsvm": "OCSVM",
    "isolation_forest": "IF",
    "isolation_forest_tuned": "IF Tuned",
    "ensemble_majority_vote": "Ensemble",
}


def model_sort_key(model):
    if model in DISPLAY_MODELS:
        return DISPLAY_MODELS.index(model)
    return len(DISPLAY_MODELS)


def display_model(model):
    return MODEL_LABELS.get(str(model), str(model).replace("_", " "))


def display_scenario(scenario):
    value = str(scenario).replace("-", " ")
    return textwrap.fill(value, width=14)


def format_metric(value):
    if pd.isna(value):
        return "N/A"
    return f"{float(value):.4f}"


def write_markdown_table(rows, columns, path):
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(row[col]) for col in columns) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_runs():
    if not ALL_RUNS.exists():
        raise FileNotFoundError(f"Missing batch input: {ALL_RUNS}")

    df = pd.read_csv(ALL_RUNS)
    metric_columns = [
        "precision",
        "recall",
        "f1",
        "accuracy",
        "roc_auc",
        "pr_auc",
        "best_f1",
    ]
    for column in metric_columns:
        if column not in df.columns:
            df[column] = pd.NA
        df[column] = pd.to_numeric(df[column], errors="coerce")

    for column in ["true_negatives", "false_positives", "false_negatives", "true_positives"]:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)

    df = df[df["model"].isin(DISPLAY_MODELS)].copy()
    if df.empty:
        raise ValueError(
            "No rows found for the main ML models: " + ", ".join(MAIN_ML_MODELS)
        )

    return df


def summarize_overall(df):
    grouped = df.groupby("model", as_index=False).agg(
        runs=("run", "count"),
        f1_mean=("f1", "mean"),
        f1_std=("f1", "std"),
        roc_auc_mean=("roc_auc", "mean"),
        roc_auc_std=("roc_auc", "std"),
        pr_auc_mean=("pr_auc", "mean"),
        pr_auc_std=("pr_auc", "std"),
        best_f1_mean=("best_f1", "mean"),
        best_f1_std=("best_f1", "std"),
    )
    grouped = grouped.sort_values("f1_mean", ascending=False).reset_index(drop=True)
    grouped.insert(0, "rank", range(1, len(grouped) + 1))
    return grouped


def make_overall_outputs(overall):
    rows = []
    for _, row in overall.iterrows():
        rows.append(
            {
                "rank": int(row["rank"]),
                "model": row["model"],
                "runs": int(row["runs"]),
                "f1_score": f"{format_metric(row['f1_mean'])} +/- {format_metric(row['f1_std'])}",
                "roc_auc": f"{format_metric(row['roc_auc_mean'])} +/- {format_metric(row['roc_auc_std'])}",
                "pr_auc": f"{format_metric(row['pr_auc_mean'])} +/- {format_metric(row['pr_auc_std'])}",
                "best_f1_score": (
                    "N/A"
                    if pd.isna(row["best_f1_mean"])
                    else f"{format_metric(row['best_f1_mean'])} +/- {format_metric(row['best_f1_std'])}"
                ),
            }
        )

    columns = ["rank", "model", "runs", "f1_score", "best_f1_score", "roc_auc", "pr_auc"]
    pd.DataFrame(rows).to_csv(OUTPUT_DIR / "batch_overall_ranking.csv", index=False)
    (OUTPUT_DIR / "batch_overall_ranking.txt").write_text(
        pd.DataFrame(rows).to_string(index=False) + "\n",
        encoding="utf-8",
    )
    write_markdown_table(rows, columns, OUTPUT_DIR / "batch_overall_ranking.md")

    plot_table_image(
        rows,
        columns,
        "Overall Model Ranking",
        OUTPUT_DIR / "batch_overall_ranking_table.png",
    )


def plot_table_image(rows, columns, title, path):
    display_df = pd.DataFrame(rows, columns=columns)
    if "model" in display_df.columns:
        display_df["model"] = display_df["model"].map(display_model)
    if "scenario" in display_df.columns:
        display_df["scenario"] = display_df["scenario"].map(display_scenario)

    fig_height = max(4.0, 0.42 * (len(display_df) + 3))
    fig_width = max(12.5, 1.75 * len(columns))
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.axis("off")
    ax.set_title(title, fontsize=15, pad=14)

    width_by_column = {
        "scenario": 0.20,
        "model": 0.13,
        "rank": 0.06,
        "runs": 0.07,
        "winner": 0.08,
        "f1": 0.14,
        "f1_score": 0.15,
        "best_f1": 0.15,
        "best_f1_score": 0.15,
        "f1_percent": 0.15,
        "roc_auc": 0.15,
        "pr_auc": 0.15,
    }
    raw_widths = [width_by_column.get(column, 0.12) for column in columns]
    width_total = sum(raw_widths)
    col_widths = [width / width_total for width in raw_widths]
    col_labels = [textwrap.fill(column.replace("_", " "), width=12) for column in columns]

    table = ax.table(
        cellText=display_df.values,
        colLabels=col_labels,
        cellLoc="center",
        loc="center",
        colWidths=col_widths,
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8.5 if len(display_df) <= 25 else 7.4)
    table.scale(1, 1.45)

    for (row, _), cell in table.get_celld().items():
        cell.PAD = 0.025
        if row == 0:
            cell.set_text_props(weight="bold", color="white")
            cell.set_facecolor("#2f4b7c")
        elif row % 2 == 0:
            cell.set_facecolor("#f3f6fb")

    fig.tight_layout()
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_grouped_metric(summary, metric, ylabel, path):
    scenarios = list(summary["scenario"].drop_duplicates())
    models = [model for model in DISPLAY_MODELS if model in set(summary["model"])]
    if not models:
        models = sorted(summary["model"].unique(), key=model_sort_key)

    group_gap = 0.8
    y_positions = {}
    scenario_centers = []
    current_y = 0.0
    for scenario in scenarios:
        start_y = current_y
        for model in models:
            y_positions[(scenario, model)] = current_y
            current_y += 1.0
        scenario_centers.append(start_y + (len(models) - 1) / 2)
        current_y += group_gap

    fig_height = max(7.0, 0.36 * current_y + 2.2)
    fig, ax = plt.subplots(figsize=(13.5, fig_height))
    color_cycle = plt.rcParams["axes.prop_cycle"].by_key()["color"]

    for model_index, model in enumerate(models):
        means = []
        errors = []
        positions = []
        for scenario in scenarios:
            row = summary[
                (summary["scenario"] == scenario) & (summary["model"] == model)
            ]
            if row.empty:
                continue

            mean_value = row.iloc[0][f"{metric}_mean"]
            if pd.isna(mean_value):
                continue

            std_value = row.iloc[0][f"{metric}_std"]
            means.append(float(mean_value))
            errors.append(0.0 if pd.isna(std_value) else float(std_value))
            positions.append(y_positions[(scenario, model)])

        bars = ax.barh(
            positions,
            means,
            height=0.72,
            xerr=errors,
            capsize=3,
            color=color_cycle[model_index % len(color_cycle)],
            ecolor="#555555",
            error_kw={"elinewidth": 1, "capthick": 1},
            label=display_model(model),
        )
        for bar, mean in zip(bars, means):
            if mean >= 0.96:
                label_x = mean - 0.015
                label_ha = "right"
            else:
                label_x = mean + 0.018
                label_ha = "left"
            ax.text(
                label_x,
                bar.get_y() + bar.get_height() / 2,
                f"{mean:.3f}",
                ha=label_ha,
                va="center",
                fontsize=8,
                fontweight="bold",
                color="#222222",
            )

    ax.set_yticks(scenario_centers)
    ax.set_yticklabels([display_scenario(scenario) for scenario in scenarios])
    ax.set_xlim(0, 1.12)
    ax.set_xlabel(ylabel)
    ax.set_title(f"{ylabel} by Scenario and Model")
    ax.grid(axis="x", alpha=0.3)
    ax.invert_yaxis()
    ax.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, 1.01),
        ncol=min(4, max(1, len(models))),
        frameon=True,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def plot_batch_charts(df):
    known_models = set(DISPLAY_MODELS)
    extra_models = sorted(set(df["model"]) - known_models)
    df = df[df["model"].isin(known_models | set(extra_models))].copy()
    df["model"] = pd.Categorical(
        df["model"],
        categories=DISPLAY_MODELS + extra_models,
        ordered=True,
    )
    summary = df.groupby(["scenario", "model"], as_index=False, observed=True).agg(
        f1_mean=("f1", "mean"),
        f1_std=("f1", "std"),
        best_f1_mean=("best_f1", "mean"),
        best_f1_std=("best_f1", "std"),
        roc_auc_mean=("roc_auc", "mean"),
        roc_auc_std=("roc_auc", "std"),
        pr_auc_mean=("pr_auc", "mean"),
        pr_auc_std=("pr_auc", "std"),
    )

    plot_grouped_metric(summary, "f1", "F1 Score", OUTPUT_DIR / "batch_f1_by_scenario.png")
    plot_grouped_metric(
        summary,
        "best_f1",
        "Best Tuned F1 Score",
        OUTPUT_DIR / "batch_best_f1_by_scenario.png",
    )
    plot_grouped_metric(
        summary,
        "roc_auc",
        "ROC-AUC",
        OUTPUT_DIR / "batch_roc_auc_by_scenario.png",
    )
    plot_grouped_metric(
        summary,
        "pr_auc",
        "PR-AUC",
        OUTPUT_DIR / "batch_pr_auc_by_scenario.png",
    )
    make_ranked_summary_image(summary)


def load_curve_data(curve_name):
    runs_dir = OUTPUT_DIR / "runs"
    if not runs_dir.exists():
        return pd.DataFrame()

    frames = []
    for path in sorted(runs_dir.glob(f"*/*_{curve_name}_curve_data.csv")):
        try:
            frame = pd.read_csv(path)
        except Exception:
            continue

        if frame.empty or "model" not in frame.columns:
            continue

        frame["scenario"] = path.parent.name
        frame["source_file"] = str(path.relative_to(OUTPUT_DIR))
        frames.append(frame)

    if not frames:
        return pd.DataFrame()

    return pd.concat(frames, ignore_index=True)


def interpolate_curve(group, x_column, y_column, grid):
    curve = group[[x_column, y_column]].dropna()
    if curve.empty:
        return None

    curve = curve.groupby(x_column, as_index=False)[y_column].max()
    curve = curve.sort_values(x_column)
    x_values = curve[x_column].to_numpy(dtype=float)
    y_values = curve[y_column].to_numpy(dtype=float)

    if len(x_values) == 0:
        return None

    if x_values[0] > 0:
        x_values = np.insert(x_values, 0, 0.0)
        y_values = np.insert(y_values, 0, y_values[0])
    if x_values[-1] < 1:
        x_values = np.append(x_values, 1.0)
        y_values = np.append(y_values, y_values[-1])

    return np.interp(grid, x_values, y_values)


def plot_average_curve(
    curve_df,
    metric_df,
    x_column,
    y_column,
    auc_column,
    title,
    xlabel,
    ylabel,
    output_path,
    include_diagonal=False,
):
    if curve_df.empty:
        return False

    grid = np.linspace(0.0, 1.0, 201)
    models = [model for model in DISPLAY_MODELS if model in set(curve_df["model"])]
    if not models:
        models = sorted(curve_df["model"].unique(), key=model_sort_key)

    fig, ax = plt.subplots(figsize=(11.5, 6.8))
    color_cycle = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    plotted = False

    for model_index, model in enumerate(models):
        model_curve_df = curve_df[curve_df["model"] == model]
        interpolated = []

        for _, run_group in model_curve_df.groupby("source_file"):
            curve_values = interpolate_curve(run_group, x_column, y_column, grid)
            if curve_values is not None:
                interpolated.append(curve_values)

        if not interpolated:
            continue

        curve_stack = np.vstack(interpolated)
        mean_curve = curve_stack.mean(axis=0)
        std_curve = curve_stack.std(axis=0)

        auc_values = metric_df.loc[metric_df["model"] == model, auc_column]
        auc_mean = auc_values.mean() if not auc_values.empty else np.nan
        label = display_model(model)
        if not pd.isna(auc_mean):
            label = f"{label} (mean AUC={auc_mean:.3f})"

        color = color_cycle[model_index % len(color_cycle)]
        ax.plot(grid, mean_curve, linewidth=2.4, color=color, label=label)
        ax.fill_between(
            grid,
            np.clip(mean_curve - std_curve, 0.0, 1.0),
            np.clip(mean_curve + std_curve, 0.0, 1.0),
            color=color,
            alpha=0.14,
            linewidth=0,
        )
        plotted = True

    if not plotted:
        plt.close(fig)
        return False

    if include_diagonal:
        ax.plot([0, 1], [0, 1], linestyle="--", linewidth=1, color="#d62728")

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.05)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(alpha=0.25)
    ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return True


def plot_average_curves(df):
    roc_df = load_curve_data("roc")
    pr_df = load_curve_data("pr")

    made_roc = plot_average_curve(
        roc_df,
        df,
        "fpr",
        "tpr",
        "roc_auc",
        "Average Batch ROC Curve Comparison (Main ML Models)",
        "False Positive Rate",
        "True Positive Rate",
        OUTPUT_DIR / "batch_average_roc_curve.png",
        include_diagonal=True,
    )
    made_pr = plot_average_curve(
        pr_df,
        df,
        "recall",
        "precision",
        "pr_auc",
        "Average Batch Precision-Recall Curve Comparison (Main ML Models)",
        "Recall",
        "Precision",
        OUTPUT_DIR / "batch_average_pr_curve.png",
    )

    return made_roc, made_pr


def make_ranked_summary_image(summary):
    rows = []
    for scenario, group in summary.groupby("scenario"):
        ranked = group.sort_values("f1_mean", ascending=False).reset_index(drop=True)
        for index, row in ranked.iterrows():
            rows.append(
                {
                    "scenario": scenario,
                    "rank": index + 1,
                    "model": row["model"],
                    "f1": f"{format_metric(row['f1_mean'])} +/- {format_metric(row['f1_std'])}",
                    "roc_auc": f"{format_metric(row['roc_auc_mean'])} +/- {format_metric(row['roc_auc_std'])}",
                    "pr_auc": f"{format_metric(row['pr_auc_mean'])} +/- {format_metric(row['pr_auc_std'])}",
                    "best_f1": (
                        "N/A"
                        if pd.isna(row["best_f1_mean"])
                        else f"{format_metric(row['best_f1_mean'])} +/- {format_metric(row['best_f1_std'])}"
                    ),
                }
            )

    columns = ["scenario", "rank", "model", "f1", "best_f1", "roc_auc", "pr_auc"]
    plot_table_image(
        rows,
        columns,
        "Scenario Ranking Summary",
        OUTPUT_DIR / "batch_ranked_summary_table.png",
    )


def confusion_summary(df):
    columns = ["true_negatives", "false_positives", "false_negatives", "true_positives"]
    if not all(column in df.columns for column in columns):
        return None

    summary = df.groupby(["scenario", "model"], as_index=False)[columns].mean()
    summary.to_csv(OUTPUT_DIR / "batch_confusion_matrix_summary.csv", index=False)

    tuned_columns = [
        "best_true_negatives",
        "best_false_positives",
        "best_false_negatives",
        "best_true_positives",
    ]
    if all(column in df.columns for column in tuned_columns):
        tuned = df.groupby(["scenario", "model"], as_index=False)[tuned_columns].mean()
        tuned.to_csv(OUTPUT_DIR / "batch_tuned_confusion_matrix_summary.csv", index=False)

    return summary


def write_thesis_report(df, overall, confusion):
    best = overall.iloc[0]
    calibrated_best = overall.sort_values("best_f1_mean", ascending=False).iloc[0]
    model_list_label = "Models" if INCLUDE_EXTRA_MODELS else "Main ML models"
    scenario_best = (
        df.groupby(["scenario", "model"], as_index=False)
        .agg(f1_mean=("f1", "mean"), f1_std=("f1", "std"))
        .sort_values(["scenario", "f1_mean"], ascending=[True, False])
        .groupby("scenario")
        .head(1)
    )

    lines = [
        "# Thesis Results Report",
        "",
        "## Dataset",
        "",
        f"- Total model evaluations: {len(df)}",
        f"- Scenarios: {', '.join(sorted(df['scenario'].unique()))}",
        f"- {model_list_label}: {', '.join(sorted(df['model'].unique()))}",
        "",
        "## Overall Result",
        "",
        (
            f"The strongest overall model is `{best['model']}` with mean F1 "
            f"{format_metric(best['f1_mean'])} +/- {format_metric(best['f1_std'])}."
        ),
        (
            f"After threshold tuning, its mean F1 can reach "
            f"{format_metric(best['best_f1_mean'])} +/- {format_metric(best['best_f1_std'])}."
            if not pd.isna(best["best_f1_mean"])
            else "Tuned F1 is unavailable for this batch because the CSV was generated before threshold-tuning columns were added."
        ),
        (
            f"The strongest calibrated model is `{calibrated_best['model']}` with tuned mean F1 "
            f"{format_metric(calibrated_best['best_f1_mean'])} +/- "
            f"{format_metric(calibrated_best['best_f1_std'])}."
            if not pd.isna(calibrated_best["best_f1_mean"])
            else ""
        ),
        "",
        "## Best Model Per Scenario",
        "",
    ]

    for _, row in scenario_best.iterrows():
        lines.append(
            f"- `{row['scenario']}`: `{row['model']}` "
            f"(F1 {format_metric(row['f1_mean'])} +/- {format_metric(row['f1_std'])})"
        )

    limitation_lines = [
        "- The dataset is synthetic and generated in a controlled lab.",
        "- Results depend on scenario duration, traffic mix, and contamination settings.",
        "- Longer thesis-profile runs provide stronger evidence than short quick runs.",
    ]
    if not INCLUDE_EXTRA_MODELS:
        limitation_lines.insert(
            2,
            "- Optional rule-based and ensemble variants are excluded from the main ranking.",
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            (
                "The results compare the three main unsupervised ML anomaly detectors "
                "in a controlled cloud-style traffic simulation. Higher F1 indicates "
                "better agreement between detected anomalies and generated ground-truth "
                "attack labels."
            ),
            "",
            (
                "ROC-AUC and PR-AUC should be interpreted together with F1 and the "
                "confusion matrix because ranking quality can be high even when a fixed "
                "anomaly threshold produces false positives or false negatives."
            ),
            "",
            (
                "The tuned F1 values estimate how much performance could improve if the "
                "anomaly-score threshold is calibrated on validation data instead of using "
                "the default model decision boundary."
            ),
            "",
            (
                f"In this batch, `{best['model']}` is the best default detector, while "
                f"`{calibrated_best['model']}` is the best threshold-calibrated detector."
            ),
            "",
            "## Limitations",
            "",
            *limitation_lines,
        ]
    )

    if confusion is not None:
        lines.extend(
            [
                "",
                "## Confusion Matrix Summary",
                "",
                (
                    "Average TP/FP/TN/FN values are saved in "
                    "`batch_confusion_matrix_summary.csv`."
                ),
            ]
        )

    lines.extend(
        [
            "",
            "## Generated Figures",
            "",
            "- `batch_f1_by_scenario.png`",
            "- `batch_best_f1_by_scenario.png`",
            "- `batch_roc_auc_by_scenario.png`",
            "- `batch_pr_auc_by_scenario.png`",
        ]
    )
    if (OUTPUT_DIR / "batch_average_roc_curve.png").exists():
        lines.append("- `batch_average_roc_curve.png`")
    if (OUTPUT_DIR / "batch_average_pr_curve.png").exists():
        lines.append("- `batch_average_pr_curve.png`")
    for image_name in [
        "threshold_tuning_comparison_lof.png",
        "threshold_tuning_comparison_ocsvm.png",
        "threshold_tuning_comparison_isolation_forest.png",
    ]:
        if (OUTPUT_DIR / image_name).exists():
            lines.append(f"- `{image_name}`")

    (OUTPUT_DIR / "thesis_results_report.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df = load_runs()
    overall = summarize_overall(df)
    make_overall_outputs(overall)
    plot_batch_charts(df)
    made_average_roc, made_average_pr = plot_average_curves(df)
    confusion = confusion_summary(df)
    write_thesis_report(df, overall, confusion)

    print("Saved batch report artifacts:")
    print(f"- {OUTPUT_DIR / 'batch_overall_ranking.csv'}")
    print(f"- {OUTPUT_DIR / 'batch_overall_ranking.txt'}")
    print(f"- {OUTPUT_DIR / 'batch_overall_ranking.md'}")
    print(f"- {OUTPUT_DIR / 'batch_overall_ranking_table.png'}")
    print(f"- {OUTPUT_DIR / 'batch_f1_by_scenario.png'}")
    print(f"- {OUTPUT_DIR / 'batch_best_f1_by_scenario.png'}")
    print(f"- {OUTPUT_DIR / 'batch_roc_auc_by_scenario.png'}")
    print(f"- {OUTPUT_DIR / 'batch_pr_auc_by_scenario.png'}")
    if made_average_roc:
        print(f"- {OUTPUT_DIR / 'batch_average_roc_curve.png'}")
    if made_average_pr:
        print(f"- {OUTPUT_DIR / 'batch_average_pr_curve.png'}")
    print(f"- {OUTPUT_DIR / 'batch_ranked_summary_table.png'}")
    print(f"- {OUTPUT_DIR / 'thesis_results_report.md'}")


if __name__ == "__main__":
    main()
