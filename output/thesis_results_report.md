# Thesis Results Report

## Dataset

- Total model evaluations: 150
- Scenarios: aggressive, balanced, mostly-normal
- Models: ensemble_majority_vote, isolation_forest, isolation_forest_tuned, lof, ocsvm

## Overall Result

The strongest overall model is `lof` with mean F1 0.6038 +/- 0.1702.
After threshold tuning, its mean F1 can reach 0.9526 +/- 0.0412.

## Best Model Per Scenario

- `aggressive`: `lof` (F1 0.7611 +/- 0.0755)
- `balanced`: `lof` (F1 0.6208 +/- 0.0961)
- `mostly-normal`: `ensemble_majority_vote` (F1 0.4306 +/- 0.1224)

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
