# Thesis Workflow

## What was added

- Streaming detector supports model selection via `MODEL_TYPE`:
  - `isolation_forest`
  - `lof`
  - `ocsvm`
- Evaluation service `ml_eval` compares all three models and writes artifacts.
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

Batch artifacts in `output/`:

- `batch_all_runs.csv` (raw per-run metrics)
- `batch_summary_stats.csv` (mean/std summary)
- `batch_summary_stats.txt` (table view)
- `batch_summary_stats.md` (markdown table)

## Scenario options

- `balanced`
- `aggressive`
- `mostly-normal`

## Methodology note

`traffic/traffic.py` now writes explicit ground-truth events (`normal` and `attack`) into `/logs/traffic_labels.jsonl` using warmup/attack/cooldown phases. `ml/evaluate_models.py` uses this label file as the primary ground truth and only falls back to failed-login proxy labels when the label file is unavailable.
