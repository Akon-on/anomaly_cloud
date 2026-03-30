# Model Report

- Label source: traffic_ground_truth
- Samples: 9
- Window size: 10
- Contamination: 0.3

## Model Comparison (Sorted by F1)

| model             | precision | recall | f1     | accuracy | roc_auc | pr_auc | label_source         |
| ---               | ---       | ---    | ---    | ---      | ---     | ---    | ---                  |
| lof               | 1.0000    | 0.6000 | 0.7500 | 0.7778   | 0.8000  | 0.9056 | traffic_ground_truth |
| ocsvm             | 1.0000    | 0.6000 | 0.7500 | 0.7778   | 0.8000  | 0.8648 | traffic_ground_truth |
| isolation_forest  | 0.0000    | 0.0000 | 0.0000 | 0.1111   | 0.0500  | 0.3529 | traffic_ground_truth |
