# Thesis Results Report

## Dataset

- Total model evaluations: 240
- Scenarios: aggressive, balanced, burst-traffic, credential-stuffing, endpoint-scanning, mixed-attacks, mostly-normal, slow-brute-force
- Models: ensemble_majority_vote, isolation_forest, isolation_forest_tuned, lof, ocsvm, rule_based_baseline

## Overall Result

The strongest overall model is `rule_based_baseline` with mean F1 0.7106 +/- 0.1264.
After threshold tuning, its mean F1 can reach 0.9187 +/- 0.0584.

## Best Model Per Scenario

- `aggressive`: `lof` (F1 0.8626 +/- 0.0917)
- `balanced`: `lof` (F1 0.5936 +/- 0.1081)
- `burst-traffic`: `isolation_forest_tuned` (F1 0.5200 +/- 0.1013)
- `credential-stuffing`: `rule_based_baseline` (F1 0.8776 +/- 0.0255)
- `endpoint-scanning`: `lof` (F1 0.6391 +/- 0.0635)
- `mixed-attacks`: `rule_based_baseline` (F1 0.6930 +/- 0.0056)
- `mostly-normal`: `rule_based_baseline` (F1 0.8061 +/- 0.0232)
- `slow-brute-force`: `rule_based_baseline` (F1 0.7985 +/- 0.0250)

## Interpretation

The results compare unsupervised anomaly detectors in a controlled cloud-style traffic simulation. Higher F1 indicates better agreement between detected anomalies and generated ground-truth attack labels.

ROC-AUC and PR-AUC should be interpreted together with F1 and the confusion matrix because ranking quality can be high even when a fixed anomaly threshold produces false positives or false negatives.

The tuned F1 values estimate how much performance could improve if the anomaly-score threshold is calibrated on validation data instead of using the default model decision boundary.

## Limitations

- The dataset is synthetic and generated in a controlled lab.
- Results depend on scenario duration, traffic mix, and contamination settings.
- Longer thesis-profile runs provide stronger evidence than short quick runs.

## Confusion Matrix Summary

Average TP/FP/TN/FN values are saved in `batch_confusion_matrix_summary.csv`.

## Generated Figures

- `batch_f1_by_scenario.png`
- `batch_best_f1_by_scenario.png`
- `batch_roc_auc_by_scenario.png`
- `batch_pr_auc_by_scenario.png`
