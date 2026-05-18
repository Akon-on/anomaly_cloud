# anomaly_cloud

Cloud anomaly detection lab for diploma/thesis work.

This project simulates web traffic (normal + attack), collects logs, builds windowed features, and compares three main machine learning models for anomaly detection:

- Isolation Forest
- Local Outlier Factor
- One-Class Support Vector Machine

Optional rule-based, tuned Isolation Forest, and ensemble variants can be enabled for secondary analysis, but the main diploma comparison focuses on these three ML algorithms.

It is designed for reproducible experiments with scenario-based traffic generation and batch statistics.

## Project goals

- Build a practical, containerized mini cloud lab
- Detect anomalous behavior from real generated logs
- Compare multiple anomaly detection models on identical data
- Evaluate with reproducible metrics and repeated runs

## Architecture

Services are orchestrated with Docker Compose:

- victim: Flask target web application
- traffic: traffic generator (normal + multiple attack styles)
- ml: streaming anomaly detector writing anomalies to PostgreSQL
- ml_eval: offline evaluator that compares the main ML models and creates reports/plots
- db: PostgreSQL storage for anomaly records
- visual: anomaly visualization script
- dashboard: web UI to browse latest metrics and generated charts

Data flow:

1. traffic generates phased traffic (warmup, attack, cooldown)
2. victim writes access logs
3. traffic writes explicit ground-truth labels with client IP and endpoint
4. ml_eval aggregates logs into time windows and builds features
5. models are trained on warmup normal behavior when labels are available
6. models score all observed windows and are evaluated against ground truth
7. reports and charts are saved to output

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
- Optional: set `LOG_LEVEL=INFO` to control service verbosity in `ml`, `ml_eval`, and `visual`

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

- balanced: brute-force attack with moderate normal traffic
- aggressive: brute-force attack with high attack pressure
- mostly-normal: brute-force attack with mostly normal background traffic
- credential-stuffing: leaked-credential login attack
- endpoint-scanning: probing many valid and invalid endpoints
- burst-traffic: short high-volume traffic spikes
- slow-brute-force: lower-rate brute-force activity spread over time
- mixed-attacks: rotating combination of supported attack styles

Important: warmup and cooldown phases are 100 percent normal traffic. The ratio above applies to the attack phase.

## Batch experiments (thesis-ready)

Run repeated experiments across scenarios:

```powershell
./run_batch_experiments.ps1 -RunsPerScenario 10
```

For stronger final thesis evidence, use longer warmup/attack/cooldown phases:

```powershell
./run_batch_experiments.ps1 -RunsPerScenario 10 -DurationProfile thesis
```

With the default scenario list this produces:

```text
8 scenarios x 10 runs x 3 main ML models = 240 model evaluations
```

Main batch outputs:

- output/batch_all_runs.csv: per-run raw metrics
- output/batch_summary_stats.csv: scenario/model mean and standard deviation
- output/batch_summary_stats.md: markdown table summary
- output/batch_summary_stats.txt: text table summary
- output/batch_ranked_summary.txt: readable per-scenario ranking
- output/batch_overall_ranking.txt: readable overall model ranking
- output/thesis_results_report.md: generated thesis-style interpretation
- output/batch_f1_by_scenario.png: batch F1 chart with standard deviation
- output/batch_best_f1_by_scenario.png: estimated F1 after threshold tuning
- output/batch_roc_auc_by_scenario.png: batch ROC-AUC chart with standard deviation
- output/batch_pr_auc_by_scenario.png: batch PR-AUC chart with standard deviation
- output/batch_average_roc_curve.png: averaged ROC curves from saved per-run curve points
- output/batch_average_pr_curve.png: averaged precision-recall curves from saved per-run curve points

## Evaluation outputs

Single-run evaluation produces:

- output/model_comparison.csv
- output/model_comparison.md
- output/model_comparison.txt
- output/model_report.md
- output/model_report.txt
- output/feature_importance.csv
- output/feature_importance.md
- output/roc_curve.png
- output/pr_curve.png
- output/roc_curve_data.csv
- output/pr_curve_data.csv

Visualization outputs:

- output/anomalies.png

If database anomaly rows are empty, visualize script generates a fallback metrics chart so anomalies.png is always refreshed.

## Dashboard UI

Run dashboard profile:

```powershell
docker compose --profile dashboard up -d dashboard
```

Open:

- http://localhost:8080/
- http://localhost:8080/api/latest

Stop:

```powershell
docker compose --profile dashboard down
```

## Ground truth and fairness

Ground truth labels are written by traffic generator into:

- /logs/traffic_labels.jsonl

Evaluator uses this label file first. If unavailable, it falls back to failed-login proxy labeling for backward compatibility.

When explicit labels are available, evaluation uses warmup windows as a known-normal baseline. The models are fit on that baseline and then score all windows from warmup, attack, and cooldown. Labels are matched by client IP and time window when the label file contains client IP data. If there are not enough baseline windows, the evaluator falls back to in-sample unsupervised scoring and records that mode in the reports.

Window features include:

- requests_per_window
- request_rate
- failed_logins
- successful_logins
- login_attempts
- login_ratio
- failed_login_ratio
- successful_requests
- distinct_endpoints
- unique_user_agents

Single-run ROC and PR curves are saved as `roc_curve.png` and `pr_curve.png`. Batch-level charts should be used for thesis-wide conclusions.

The evaluator also records an estimated best F1 threshold from the precision-recall curve. This is useful for studying false-positive reduction, but it should be described as threshold tuning or validation-calibrated performance, not as the default detector output.

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

Run the shared feature-engineering smoke test inside the ML container:

```powershell
docker compose run --rm --build --no-deps ml python test_feature_engineering.py
```

Run evaluator unit tests:

```powershell
docker compose run --rm --build --no-deps ml python test_evaluator.py
```

Run drift unit tests:

```powershell
docker compose run --rm --build --no-deps ml python test_drift.py
```

Run `ml_eval` integration artifact test:

```powershell
./tests/test_ml_eval_integration.ps1
```

Run scalability smoke profiling:

```powershell
./tests/test_scalability_smoke.ps1
```

Run long batch and keep timestamped copies (example pattern):

```powershell
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
./run_batch_experiments.ps1 -RunsPerScenario 10 -DurationProfile thesis -BaseSeed 12000
Copy-Item ./output/batch_summary_stats.csv ./output/batch_summary_stats_final_$ts.csv -Force
Copy-Item ./output/batch_summary_stats.md ./output/batch_summary_stats_final_$ts.md -Force
Copy-Item ./output/batch_all_runs.csv ./output/batch_all_runs_final_$ts.csv -Force
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

## Limitations and future work

- Current attacks include brute-force, credential-stuffing, slow brute-force, endpoint scanning, burst traffic, and mixed attack scenarios.
- Results are scenario-driven and may not transfer directly to unrelated production traffic.
- Explainability currently uses feature-importance and correlation-based proxy scores; SHAP-style local explanations can be added later.
- Future iterations can include deep autoencoder baselines, online drift adaptation, and larger distributed load tests.

## Threshold Tuning for False Positive Reduction

By default, the unsupervised models use their built-in decision boundary. Post-hoc **threshold tuning** uses the precision-recall curve to select an anomaly-score cutoff that maximizes F1 on labeled validation data.

The final thesis-profile batch shows two complementary conclusions:

- LOF is the best default detector: F1 `0.6270 +/- 0.1296`.
- OCSVM is the best calibrated detector: tuned F1 `0.9902 +/- 0.0137`.

Average false positives per model evaluation decreased strongly after threshold tuning:

| Model | Default F1 | Tuned F1 | Default FP | Tuned FP |
| --- | ---: | ---: | ---: | ---: |
| LOF | 0.6270 | 0.9523 | 277.2 | 13.9 |
| OCSVM | 0.6020 | 0.9902 | 308.6 | 1.5 |
| Isolation Forest | 0.5529 | 0.8982 | 341.2 | 73.4 |

Generated threshold-tuning figures:

- `output/threshold_tuning_comparison_lof.png`
- `output/threshold_tuning_comparison_ocsvm.png`
- `output/threshold_tuning_comparison_isolation_forest.png`

For thesis writing, describe tuned F1 as validation-calibrated performance, not as the raw default detector output.
