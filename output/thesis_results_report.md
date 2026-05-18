# Thesis Results Report

## Dataset

- Total model evaluations: 240
- Scenarios: aggressive, balanced, burst-traffic, credential-stuffing, endpoint-scanning, mixed-attacks, mostly-normal, slow-brute-force
- Main ML models: isolation_forest, lof, ocsvm

## Overall Result

The strongest overall model is `lof` with mean F1 0.6270 +/- 0.1296.
After threshold tuning, its mean F1 can reach 0.9523 +/- 0.0400.
The strongest calibrated model is `ocsvm` with tuned mean F1 0.9902 +/- 0.0137.

## Best Model Per Scenario

- `aggressive`: `lof` (F1 0.7600 +/- 0.0773)
- `balanced`: `lof` (F1 0.6010 +/- 0.0899)
- `burst-traffic`: `lof` (F1 0.4839 +/- 0.0805)
- `credential-stuffing`: `lof` (F1 0.8124 +/- 0.0626)
- `endpoint-scanning`: `lof` (F1 0.6188 +/- 0.0863)
- `mixed-attacks`: `lof` (F1 0.6107 +/- 0.0776)
- `mostly-normal`: `lof` (F1 0.5008 +/- 0.0478)
- `slow-brute-force`: `lof` (F1 0.6285 +/- 0.0878)

## Interpretation

The results compare the three main unsupervised ML anomaly detectors in a controlled cloud-style traffic simulation. Higher F1 indicates better agreement between detected anomalies and generated ground-truth attack labels.

ROC-AUC and PR-AUC should be interpreted together with F1 and the confusion matrix because ranking quality can be high even when a fixed anomaly threshold produces false positives or false negatives.

The tuned F1 values estimate how much performance could improve if the anomaly-score threshold is calibrated on validation data instead of using the default model decision boundary.

In this batch, `lof` is the best default detector, while `ocsvm` is the best threshold-calibrated detector.

## Limitations

- The dataset is synthetic and generated in a controlled lab.
- Results depend on scenario duration, traffic mix, and contamination settings.
- Optional rule-based and ensemble variants are excluded from the main ranking.
- Longer thesis-profile runs provide stronger evidence than short quick runs.

## Confusion Matrix Summary

Average TP/FP/TN/FN values are saved in `batch_confusion_matrix_summary.csv`.

## Generated Figures

- `batch_f1_by_scenario.png`
- `batch_best_f1_by_scenario.png`
- `batch_roc_auc_by_scenario.png`
- `batch_pr_auc_by_scenario.png`
- `batch_average_roc_curve.png`
- `batch_average_pr_curve.png`
- `threshold_tuning_comparison_lof.png`
- `threshold_tuning_comparison_ocsvm.png`
- `threshold_tuning_comparison_isolation_forest.png`
