# Thesis Workflow

## What was added

- Streaming detector supports model selection via `MODEL_TYPE`:
  - `isolation_forest`
  - `lof`
  - `ocsvm`
- Evaluation service `ml_eval` compares all three models and writes artifacts.
- Evaluation now trains on warmup normal windows when explicit labels are available.
- Evaluation uses IP-window ground truth when traffic labels include client IPs.
- Evaluation outputs confusion matrix counts for each model.
- Evaluation reports include the label source, evaluation mode, training sample count, and feature list.
- Batch automation creates ranked summaries, batch charts, an overall model ranking, and a thesis results report.
- Repeatable traffic scenarios are available via `run_experiment.ps1`.
- Batch experiment automation is available via `run_batch_experiments.ps1`.

## Quick run

1. Run one scenario:

```powershell
./run_experiment.ps1 -Scenario balanced
```

2. Artifacts will be generated in `output/`:

- `model_comparison.csv`
- `model_comparison.txt`
- `model_comparison.md`
- `model_report.txt`
- `model_report.md`
- `roc_curve.png`
- `pr_curve.png`

## Batch run (thesis-ready)

Run repeated experiments and aggregate statistics:

```powershell
./run_batch_experiments.ps1 -RunsPerScenario 10
```

Run longer thesis-profile experiments:

```powershell
./run_batch_experiments.ps1 -RunsPerScenario 10 -DurationProfile thesis
```

Batch artifacts in `output/`:

- `batch_all_runs.csv` (raw per-run metrics)
- `batch_summary_stats.csv` (mean/std summary)
- `batch_summary_stats.txt` (table view)
- `batch_summary_stats.md` (markdown table)
- `batch_ranked_summary.txt` (per-scenario ranking)
- `batch_overall_ranking.txt` (overall ranking)
- `batch_f1_by_scenario.png`
- `batch_best_f1_by_scenario.png`
- `batch_roc_auc_by_scenario.png`
- `batch_pr_auc_by_scenario.png`
- `batch_average_roc_curve.png`
- `batch_average_pr_curve.png`
- `thesis_results_report.md`

## Scenario options

- `balanced`
- `aggressive`
- `mostly-normal`
- `credential-stuffing`
- `endpoint-scanning`
- `burst-traffic`
- `slow-brute-force`
- `mixed-attacks`

The final thesis-profile batch uses the default scenario list:

```text
8 scenarios x 10 runs x 3 main ML models = 240 model evaluations
```

Use `output/batch_*` files for final conclusions. The `output/model_comparison.*`, `output/model_report.*`, `output/roc_curve.png`, and `output/pr_curve.png` files describe only the latest single run.

## Methodology note

`traffic/traffic.py` now writes explicit ground-truth events (`normal` and `attack`) into `/logs/traffic_labels.jsonl` using warmup/attack/cooldown phases. `ml/evaluate_models.py` uses this label file as the primary ground truth and only falls back to failed-login proxy labels when the label file is unavailable.

With explicit labels, the evaluator fits each anomaly model on known-normal warmup windows and then scores the full run. This is stronger than pure in-sample scoring because it better matches the practical anomaly-detection workflow: learn a baseline first, detect deviations later.
