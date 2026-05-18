# Threshold Tuning Deployment Guide

## Purpose

This guide explains how to use threshold tuning after the offline evaluator has produced anomaly scores and ground-truth metrics. Threshold tuning should be treated as a calibration step: it chooses a decision cutoff for a trained anomaly detector.

The final thesis batch should be interpreted like this:

- Best default model: LOF, F1 `0.6270 +/- 0.1296`.
- Best calibrated model: OCSVM, tuned F1 `0.9902 +/- 0.0137`.
- Main practical issue: default thresholds create many false positives.

## When to Use Threshold Tuning

Use threshold tuning when you have labeled validation data or controlled simulation labels. In this project, labels come from `traffic_labels.jsonl`, so the evaluator can compare anomaly scores against known normal/attack windows.

Do not describe tuned F1 as the default result. In the diploma, call it validation-calibrated or threshold-tuned performance.

## Finding Thresholds

Run one scenario or a batch experiment:

```powershell
./run_experiment.ps1 -Scenario balanced
```

or:

```powershell
./run_batch_experiments.ps1 -RunsPerScenario 10 -DurationProfile thesis
```

Then inspect:

```text
output/model_comparison.csv
output/batch_all_runs.csv
```

Useful columns:

- `best_threshold`
- `best_precision`
- `best_recall`
- `best_f1`
- `best_false_positives`
- `best_false_negatives`

## Current Batch Averages

| Model | Default F1 | Tuned F1 | Default FP | Tuned FP |
| --- | ---: | ---: | ---: | ---: |
| LOF | 0.6270 | 0.9523 | 277.2 | 13.9 |
| OCSVM | 0.6020 | 0.9902 | 308.6 | 1.5 |
| Isolation Forest | 0.5529 | 0.8982 | 341.2 | 73.4 |

The average best threshold values in the final batch were approximately:

| Model | Mean best threshold |
| --- | ---: |
| LOF | 2.0525 |
| OCSVM | 9.4857 |
| Isolation Forest | 0.1786 |

These values are useful for analysis, but a real deployment should validate the threshold on representative traffic before using it operationally.

## Generated Figures

The threshold-tuning comparison images are:

- `output/threshold_tuning_comparison_lof.png`
- `output/threshold_tuning_comparison_ocsvm.png`
- `output/threshold_tuning_comparison_isolation_forest.png`

Regenerate them after a new batch run with:

```powershell
docker compose run --rm --no-deps -e THRESHOLD_MODEL=lof visual python generate_threshold_comparison.py
docker compose run --rm --no-deps -e THRESHOLD_MODEL=ocsvm visual python generate_threshold_comparison.py
docker compose run --rm --no-deps -e THRESHOLD_MODEL=isolation_forest visual python generate_threshold_comparison.py
```

## Runtime Configuration

The streaming detector can be configured with environment variables:

| Variable | Meaning |
| --- | --- |
| `MODEL_TYPE` | Model used by the streaming detector, such as `lof`, `ocsvm`, or `isolation_forest` |
| `USE_THRESHOLD_TUNING` | Whether to apply a fixed anomaly-score threshold |
| `ANOMALY_THRESHOLD` | Threshold value to compare against the anomaly score |
| `MODEL_CONTAMINATION` | Contamination setting used by applicable models |

Example:

```yaml
ml:
  environment:
    MODEL_TYPE: lof
    USE_THRESHOLD_TUNING: "true"
    ANOMALY_THRESHOLD: "2.0525"
```

## Thesis Talking Point

The most important deployment conclusion is:

> The default detectors were very sensitive and detected most attack windows, but this caused many false positives. Threshold tuning reduced false positives substantially, especially for OCSVM, which achieved the strongest calibrated result across the final batch.
