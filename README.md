# anomaly_cloud

Cloud anomaly detection lab for diploma/thesis work.

This project simulates web traffic (normal + attack), collects logs, builds windowed features, and compares multiple machine learning models for anomaly detection:

- Isolation Forest
- Local Outlier Factor
- One-Class Support Vector Machine

It is designed for reproducible experiments with scenario-based traffic generation and batch statistics.

## Project goals

- Build a practical, containerized mini cloud lab
- Detect anomalous behavior from real generated logs
- Compare multiple anomaly detection models on identical data
- Evaluate with reproducible metrics and repeated runs

## Architecture

Services are orchestrated with Docker Compose:

- victim: Flask target web application
- traffic: traffic generator (normal + brute-force style attack)
- ml: streaming anomaly detector writing anomalies to PostgreSQL
- ml_eval: offline evaluator that compares all models and creates reports/plots
- db: PostgreSQL storage for anomaly records
- visual: anomaly visualization script

Data flow:

1. traffic generates phased traffic (warmup, attack, cooldown)
2. victim writes access logs
3. traffic writes explicit ground-truth labels (normal or attack)
4. ml_eval aggregates logs into time windows and builds features
5. models are evaluated and compared
6. reports and charts are saved to output

## Repository structure

- docker-compose.yml
- run_experiment.ps1
- run_batch_experiments.ps1
- victim/
- traffic/
- ml/
- visual/
- db/
- output/

## Requirements

- Docker Desktop (with docker compose)
- Windows PowerShell (for .ps1 scripts)

## Quick start

From repository root:

```powershell
./run_experiment.ps1 -Scenario balanced
```

This will:

- reset volumes and containers for a clean run
- start base services
- generate traffic for the selected scenario
- run multi-model evaluation
- write artifacts to output

## Traffic scenarios

Configured in run_experiment.ps1:

- balanced: normal_traffic_ratio = 0.30 (30 percent normal, 70 percent attack)
- aggressive: normal_traffic_ratio = 0.10 (10 percent normal, 90 percent attack)
- mostly-normal: normal_traffic_ratio = 0.70 (70 percent normal, 30 percent attack)

Important: warmup and cooldown phases are 100 percent normal traffic. The ratio above applies to the attack phase.

## Batch experiments (thesis-ready)

Run repeated experiments across scenarios:

```powershell
./run_batch_experiments.ps1 -RunsPerScenario 10 -Scenarios balanced,aggressive,mostly-normal
```

Main batch outputs:

- output/batch_all_runs.csv: per-run raw metrics
- output/batch_summary_stats.csv: scenario/model mean and standard deviation
- output/batch_summary_stats.md: markdown table summary
- output/batch_summary_stats.txt: text table summary

## Evaluation outputs

Single-run evaluation produces:

- output/model_comparison.csv
- output/model_comparison.md
- output/model_comparison.txt
- output/model_report.md
- output/model_report.txt
- output/roc_curve.png
- output/pr_curve.png

Visualization outputs:

- output/anomalies.png

If database anomaly rows are empty, visualize script generates a fallback metrics chart so anomalies.png is always refreshed.

## Ground truth and fairness

Ground truth labels are written by traffic generator into:

- /logs/traffic_labels.jsonl

Evaluator uses this label file first. If unavailable, it falls back to failed-login proxy labeling for backward compatibility.

## Reproducibility

Reproducibility is supported by:

- deterministic random seed control (RANDOM_SEED and SeedOverride)
- scripted scenario parameters
- batch automation with repeated runs
- standardized outputs (CSV, TXT, MD, PNG)

## Useful commands

Run one scenario quickly without rebuilding images:

```powershell
./run_experiment.ps1 -Scenario balanced -SkipBuild
```

Run long batch and keep timestamped copies (example pattern):

```powershell
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
./run_batch_experiments.ps1 -RunsPerScenario 10 -Scenarios balanced,aggressive,mostly-normal -BaseSeed 12000
Copy-Item ./output/batch_summary_stats.csv ./output/batch_summary_stats_long_$ts.csv -Force
Copy-Item ./output/batch_summary_stats.md ./output/batch_summary_stats_long_$ts.md -Force
Copy-Item ./output/batch_all_runs.csv ./output/batch_all_runs_long_$ts.csv -Force
```

Rebuild visual service after changing visual/visualize.py:

```powershell
docker compose build visual
docker compose run --rm visual python visualize.py
```

## Thesis framing (short)

Main idea:

Combining cloud simulation with machine learning enables automated detection of anomalous behavior in cloud-like environments.

Contribution in this repository:

- scenario-based cloud traffic simulation
- explicit per-event ground truth labeling
- multi-model anomaly detector comparison
- repeatable batch evaluation with statistical summaries

## Notes

- This project is intended for research and educational use in controlled environments.
- Do not run attack-style traffic against systems you do not own or have permission to test.
