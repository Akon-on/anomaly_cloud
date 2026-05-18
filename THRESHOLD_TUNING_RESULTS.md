# Threshold Tuning Results

## Executive Summary

The final thesis-profile batch evaluated 3 main unsupervised ML models across 8 scenarios and 10 runs per scenario:

```text
8 scenarios x 10 runs x 3 models = 240 model evaluations
```

The default detector ranking is led by LOF, while the calibrated threshold-tuned ranking is led by OCSVM.

## Final Batch Result

| Model | Default F1 | Tuned F1 | ROC-AUC | PR-AUC |
| --- | ---: | ---: | ---: | ---: |
| LOF | 0.6270 +/- 0.1296 | 0.9523 +/- 0.0400 | 0.9806 | 0.9748 |
| OCSVM | 0.6020 +/- 0.1121 | 0.9902 +/- 0.0137 | 0.9970 | 0.9954 |
| Isolation Forest | 0.5529 +/- 0.1343 | 0.8982 +/- 0.1704 | 0.8973 | 0.8083 |

Interpretation:

- LOF is the best default detector because it has the highest average fixed-threshold F1.
- OCSVM is the best calibrated detector because it has the highest tuned F1, ROC-AUC, and PR-AUC.
- Isolation Forest is weaker overall, especially in endpoint-scanning and burst-traffic scenarios.

## False Positive Reduction

The default thresholds detected most attacks but produced many false positives. Threshold tuning greatly reduced false positives by choosing a better anomaly-score cutoff.

| Model | Default precision | Tuned precision | Default recall | Tuned recall | Default FP | Tuned FP | Default FN | Tuned FN |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| LOF | 0.4734 | 0.9643 | 0.9916 | 0.9448 | 277.2 | 13.9 | 2.4 | 18.0 |
| OCSVM | 0.4401 | 0.9946 | 0.9982 | 0.9861 | 308.6 | 1.5 | 0.3 | 3.0 |
| Isolation Forest | 0.3976 | 0.8584 | 0.9552 | 0.9894 | 341.2 | 73.4 | 11.4 | 2.7 |

This shows the practical trade-off:

- OCSVM gives the strongest calibrated result, reducing average false positives from `308.6` to `1.5`.
- LOF remains the strongest default model and still improves strongly after tuning.
- Isolation Forest improves, but its tuned result remains below LOF and OCSVM.

## Generated Figures

Use these figures for the threshold-tuning discussion:

- `output/threshold_tuning_comparison_lof.png`
- `output/threshold_tuning_comparison_ocsvm.png`
- `output/threshold_tuning_comparison_isolation_forest.png`

Use these figures for overall model separation:

- `output/batch_average_roc_curve.png`
- `output/batch_average_pr_curve.png`

## Methodology

Threshold tuning was computed after model scoring by using the precision-recall curve to select the threshold with the best F1-score. This is a validation-calibrated performance estimate, not the raw default detector output.

In the diploma text, describe it as:

> The default unsupervised models were sensitive and detected most attacks, but generated many false alarms. After threshold calibration, false positives decreased significantly while high recall was mostly preserved. This indicates that the anomaly scores contain useful separation information, but the operational decision threshold must be calibrated before deployment.

## Thesis Conclusion

The threshold-tuning experiment supports a strong final conclusion:

- LOF should be presented as the best default model.
- OCSVM should be presented as the best calibrated model.
- The system benefits from threshold calibration because raw anomaly scores are more informative than the default binary decision boundary.
