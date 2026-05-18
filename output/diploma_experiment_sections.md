# Experimental Evaluation

## Experimental Setup

The experimental part of this project evaluates anomaly detection methods in a controlled cloud-style environment. The system consists of a vulnerable web service, a traffic generator, a machine learning evaluation module, a PostgreSQL database, and a dashboard for visualizing the results. All main components are containerized with Docker, which makes the experiments repeatable and easier to run under the same conditions.

The victim service records each HTTP request in JSON format. Each log entry includes the request time, client IP address, endpoint, HTTP method, user agent, request status, and status code. These logs are then transformed into time-window-based features and used for anomaly detection.

The experiments were performed using a 10-second aggregation window. For each IP address and time window, the system calculated behavior-based features such as request count, request rate, failed login count, login ratio, error request count, endpoint diversity, and user-agent diversity. The complete feature set used in the final evaluation was:

- `requests_per_window`
- `request_rate`
- `failed_logins`
- `successful_logins`
- `login_attempts`
- `login_ratio`
- `failed_login_ratio`
- `successful_requests`
- `error_requests`
- `error_ratio`
- `post_requests`
- `distinct_endpoints`
- `unique_user_agents`

## Traffic Scenarios

The dataset was generated using controlled synthetic traffic. This approach was chosen because it provides repeatable experiments and clear ground-truth labels for normal and attack traffic. Eight traffic scenarios were evaluated:

- `balanced`
- `aggressive`
- `mostly-normal`
- `credential-stuffing`
- `endpoint-scanning`
- `burst-traffic`
- `slow-brute-force`
- `mixed-attacks`

Each scenario was repeated ten times with different random seeds. In total, the main machine-learning batch experiment produced 240 model evaluations:

`8 scenarios x 10 runs x 3 models = 240 evaluations`

The traffic generator included both normal user behavior and attack behavior. Normal behavior included requests to common endpoints, search requests, health checks, and occasional login attempts. Attack behavior included brute-force login attempts, credential stuffing, endpoint scanning, burst traffic, slow brute-force traffic, and mixed attack patterns.

## Evaluated Models

The main diploma comparison evaluates three unsupervised machine learning anomaly detection methods:

- Isolation Forest
- Local Outlier Factor
- One-Class SVM

The rule-based baseline, tuned Isolation Forest variant, and majority-vote ensemble were excluded from the main ranking to keep the thesis focused on three core machine learning algorithms. They can still be discussed as optional extensions, but the main experimental conclusion is based on the three models above.

## Evaluation Metrics

The models were evaluated using the following metrics:

- Precision
- Recall
- F1-score
- Accuracy
- ROC-AUC
- PR-AUC
- Confusion matrix values: true positives, false positives, true negatives, and false negatives

The F1-score was used as the main ranking metric because it balances precision and recall. This is important for anomaly detection because a detector should identify attacks while avoiding excessive false alarms. ROC-AUC and PR-AUC were also analyzed because they show how well the model ranks normal and anomalous samples across different thresholds.

## Overall Results

Across all scenarios and runs, the strongest fixed-threshold result among the three main ML models was achieved by Local Outlier Factor. It reached an average F1-score of `0.6270 +/- 0.1296`.

One-Class SVM ranked second by fixed-threshold F1-score, while Isolation Forest ranked third. However, One-Class SVM had the strongest ROC-AUC and PR-AUC values, which shows that its anomaly scores separated normal and attack windows very well even when the default threshold produced many false positives.

The overall ranking was:

| Rank | Model | Runs | F1-score | Best tuned F1 | ROC-AUC | PR-AUC |
| --- | --- | ---: | --- | --- | --- | --- |
| 1 | Local Outlier Factor | 80 | 0.6270 +/- 0.1296 | 0.9523 +/- 0.0400 | 0.9806 +/- 0.0444 | 0.9748 +/- 0.0464 |
| 2 | One-Class SVM | 80 | 0.6020 +/- 0.1121 | 0.9902 +/- 0.0137 | 0.9970 +/- 0.0083 | 0.9954 +/- 0.0111 |
| 3 | Isolation Forest | 80 | 0.5529 +/- 0.1343 | 0.8982 +/- 0.1704 | 0.8973 +/- 0.2046 | 0.8083 +/- 0.3188 |

These results show that LOF gave the best default balance between precision and recall. One-Class SVM achieved ROC-AUC `0.9970 +/- 0.0083` and PR-AUC `0.9954 +/- 0.0111`, which indicates very strong ranking ability. This means that One-Class SVM can separate normal and anomalous windows well, but its default decision threshold needs calibration to reduce false positives.

## Results by Scenario

The best model differed depending on the traffic scenario. The following table shows the winner inside each individual scenario, not the overall winner across the full experiment:

| Scenario | Best model | F1-score |
| --- | --- | --- |
| Aggressive | Local Outlier Factor | 0.7600 +/- 0.0773 |
| Balanced | Local Outlier Factor | 0.6010 +/- 0.0899 |
| Burst traffic | Local Outlier Factor | 0.4839 +/- 0.0805 |
| Credential stuffing | Local Outlier Factor | 0.8124 +/- 0.0626 |
| Endpoint scanning | Local Outlier Factor | 0.6188 +/- 0.0863 |
| Mixed attacks | Local Outlier Factor | 0.6107 +/- 0.0776 |
| Mostly normal | Local Outlier Factor | 0.5008 +/- 0.0478 |
| Slow brute force | Local Outlier Factor | 0.6285 +/- 0.0878 |

Local Outlier Factor performed best by default F1 in all eight scenarios. This suggests that LOF is the most reliable fixed-threshold detector in this experiment when anomalous windows differ locally from nearby normal behavior.

The burst-traffic scenario was the most difficult. The best fixed-threshold F1-score among the three main ML models in this scenario was only `0.4839 +/- 0.0805`, achieved by LOF. This indicates that burst traffic can be harder to distinguish from legitimate temporary traffic spikes.

## Threshold Tuning

Threshold tuning significantly improved many model results. For example, One-Class SVM improved from an average F1-score of `0.6020 +/- 0.1121` to a tuned F1-score of `0.9902 +/- 0.0137`. Local Outlier Factor improved from `0.6270 +/- 0.1296` to `0.9523 +/- 0.0400`.

This shows that the anomaly scores produced by the models contain useful information, even when the default threshold is not optimal. The main issue is not always the model's ability to rank anomalies, but the decision boundary used to convert anomaly scores into final normal/anomalous labels.

For this reason, threshold calibration is an important part of applying anomaly detection in practice. A model with high ROC-AUC or PR-AUC may still perform poorly at a fixed threshold if the threshold is not adapted to the target environment.

## Confusion Matrix Interpretation

The confusion matrix results show that many unsupervised models detected most attack windows but also produced many false positives. For example, in the aggressive scenario, One-Class SVM detected all attacks on average, with `387.9` true positives and `0.0` false negatives, but it also produced `301.2` false positives. Similarly, Isolation Forest detected all attacks in that scenario but produced `329.8` false positives.

In the mostly-normal scenario, LOF produced `204.3` false positives on average, compared with `239.4` for Isolation Forest and `225.0` for One-Class SVM. In endpoint scanning, LOF detected most attacks with only `1.4` false negatives on average, while Isolation Forest missed many more attack windows with `87.8` false negatives. This confirms that the main challenge is reducing false alarms without losing attack coverage.

These results show the trade-off between sensitivity and false alarms. Some models maximize recall by detecting nearly all attacks, but this often increases the number of normal windows incorrectly classified as anomalous.

## Discussion

The experimental results show that anomaly detection performance depends strongly on the type of attack and the traffic distribution. LOF achieved the best fixed-threshold performance in every scenario, while One-Class SVM achieved the strongest calibrated performance after threshold tuning.

One-Class SVM achieved very high ROC-AUC and PR-AUC, which indicates strong ranking quality. With threshold tuning, it reached the highest tuned F1-score among the three main ML models.

The main practical conclusion is that anomaly detection should not rely only on a default model threshold. A calibrated threshold can greatly reduce false positives while preserving high attack detection. In a real deployment, this threshold should be selected using validation data that represents the target environment.

The results also show why threshold calibration is important for unsupervised anomaly detection. The raw anomaly scores often contain useful information, but a fixed default threshold may create too many false alarms.

## Limitations

The experiments were performed in a controlled Docker-based environment using synthetic traffic. This makes the experiments repeatable and safe, but it does not fully represent all behavior found in real production cloud systems.

The ground-truth labels were generated by the traffic simulator. This is useful for evaluation, but real systems may contain ambiguous behavior where the boundary between normal and malicious activity is less clear.

The model performance also depends on scenario configuration, including attack duration, request rate, number of IP addresses, normal traffic ratio, and contamination settings. Therefore, the reported results should be interpreted as performance under the designed experimental conditions, not as universal real-world accuracy.

## Future Work

Future improvements could include testing the system with real public intrusion detection datasets, adding more attack categories, and deploying the detector in a real cloud environment. The system could also be extended with adaptive threshold selection, online model updating, and explainability methods for showing why a traffic window was classified as anomalous.

Another direction is to compare the three main ML models with rule-based and ensemble extensions in a separate secondary experiment. This would allow the main thesis to remain focused while still showing how hybrid detection could improve practical deployment.

## Recommended Figures for Diploma

The following figures are the most useful for the diploma results section:

- `batch_f1_by_scenario.png`
- `batch_best_f1_by_scenario.png`
- `batch_ranked_summary_table.png`
- `batch_overall_ranking_table.png`
- `batch_roc_auc_by_scenario.png`
- `batch_pr_auc_by_scenario.png`
- `batch_average_roc_curve.png`
- `batch_average_pr_curve.png`
- `threshold_tuning_comparison_lof.png`
- `threshold_tuning_comparison_ocsvm.png`
- `threshold_tuning_comparison_isolation_forest.png`
