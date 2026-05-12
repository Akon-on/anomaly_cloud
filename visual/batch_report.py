from pathlib import Path
import textwrap

import matplotlib.pyplot as plt
import pandas as pd


OUTPUT_DIR = Path("output")
ALL_RUNS = OUTPUT_DIR / "batch_all_runs.csv"
DISPLAY_MODELS = ["lof", "ocsvm", "isolation_forest"]


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
        display_df["model"] = display_df["model"].map(
            lambda value: textwrap.fill(str(value), width=12) if isinstance(value, str) and len(value) > 12 else value
        )
    fig_height = max(3.4, 0.58 * (len(display_df) + 2))
    fig_width = max(10, 1.45 * len(columns))
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.axis("off")
    ax.set_title(title, fontsize=15, pad=14)

    table = ax.table(
        cellText=display_df.values,
        colLabels=display_df.columns,
        cellLoc="center",
        loc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.65)

    for (row, _), cell in table.get_celld().items():
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
    x = range(len(scenarios))
    width = 0.24
    offsets = {
        model: (index - (len(models) - 1) / 2) * width
        for index, model in enumerate(models)
    }

    fig, ax = plt.subplots(figsize=(10, 5.4))
    for model in models:
        means = []
        errors = []
        for scenario in scenarios:
            row = summary[
                (summary["scenario"] == scenario) & (summary["model"] == model)
            ]
            if row.empty:
                means.append(0)
                errors.append(0)
            else:
                means.append(float(row.iloc[0][f"{metric}_mean"]))
                errors.append(float(row.iloc[0][f"{metric}_std"]))

        positions = [value + offsets[model] for value in x]
        bars = ax.bar(
            positions,
            means,
            width=width,
            yerr=errors,
            capsize=3,
            ecolor="#555555",
            error_kw={"elinewidth": 1, "capthick": 1},
            label=model,
        )
        for bar, mean in zip(bars, means):
            if pd.isna(mean):
                continue
            label_y = mean - 0.055 if mean >= 0.88 else mean + 0.03
            label_va = "top" if mean >= 0.88 else "bottom"
            label_color = "#222222" if mean >= 0.88 else "#222222"
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                label_y,
                f"{mean:.3f}",
                ha="center",
                va=label_va,
                fontsize=8,
                color=label_color,
                fontweight="bold",
            )

    ax.set_xticks(list(x))
    ax.set_xticklabels(scenarios)
    ax.set_ylim(0, 1.10)
    ax.set_ylabel(ylabel)
    ax.set_title(f"{ylabel} by Scenario and Model")
    ax.grid(axis="y", alpha=0.3)
    ax.legend(loc="lower left", frameon=True)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_batch_charts(df):
    df = df[df["model"].isin(DISPLAY_MODELS)].copy()
    summary = df.groupby(["scenario", "model"], as_index=False).agg(
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


def make_ranked_summary_image(summary):
    rows = []
    for scenario, group in summary.groupby("scenario"):
        ranked = group[group["model"].isin(DISPLAY_MODELS)].sort_values("f1_mean", ascending=False).reset_index(drop=True)
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
        f"- Models: {', '.join(sorted(df['model'].unique()))}",
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
        "",
        "## Best Model Per Scenario",
        "",
    ]

    for _, row in scenario_best.iterrows():
        lines.append(
            f"- `{row['scenario']}`: `{row['model']}` "
            f"(F1 {format_metric(row['f1_mean'])} +/- {format_metric(row['f1_std'])})"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            (
                "The results compare unsupervised anomaly detectors in a controlled "
                "cloud-style traffic simulation. Higher F1 indicates better agreement "
                "between detected anomalies and generated ground-truth attack labels."
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
            "## Limitations",
            "",
            "- The dataset is synthetic and generated in a controlled lab.",
            "- Results depend on scenario duration, traffic mix, and contamination settings.",
            "- Longer thesis-profile runs provide stronger evidence than short quick runs.",
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
    print(f"- {OUTPUT_DIR / 'batch_ranked_summary_table.png'}")
    print(f"- {OUTPUT_DIR / 'thesis_results_report.md'}")


if __name__ == "__main__":
    main()
