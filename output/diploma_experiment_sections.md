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

Each scenario was repeated five times with different random seeds. In total, the batch experiment produced 240 model evaluations:

`8 scenarios x 5 runs x 6 models = 240 evaluations`

The traffic generator included both normal user behavior and attack behavior. Normal behavior included requests to common endpoints, search requests, health checks, and occasional login attempts. Attack behavior included brute-force login attempts, credential stuffing, endpoint scanning, burst traffic, slow brute-force traffic, and mixed attack patterns.

## Evaluated Models

The following anomaly detection methods were evaluated:

- Isolation Forest
- Tuned Isolation Forest
- Local Outlier Factor
- One-Class SVM
- Majority-vote ensemble
- Rule-based baseline

The rule-based baseline was added as a simple comparison point. It detects suspicious traffic using direct thresholds, such as high request count, high failed login count, high failed login ratio, or many error responses. This baseline is important because it shows whether machine learning provides an advantage over simple handcrafted detection rules.

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

Across all scenarios and runs, the strongest fixed-threshold result was achieved by the rule-based baseline. It reached an average F1-score of `0.7106 +/- 0.1264`. Therefore, when the dashboard shows the rule-based baseline as the best overall model, it is using the aggregate ranking across all scenarios.

Local Outlier Factor was the strongest unsupervised machine learning model by fixed-threshold F1-score, with an average F1-score of `0.6651 +/- 0.1525`. In other words, the rule-based baseline is the overall winner, while LOF is the best machine learning anomaly detector among the unsupervised models.

The overall ranking was:

| Rank | Model | Runs | F1-score | Best tuned F1 | ROC-AUC | PR-AUC |
| --- | --- | ---: | --- | --- | --- | --- |
| 1 | Rule-based baseline | 40 | 0.7106 +/- 0.1264 | 0.9187 +/- 0.0584 | 0.9619 +/- 0.0352 | 0.9437 +/- 0.0617 |
| 2 | Local Outlier Factor | 40 | 0.6651 +/- 0.1525 | 0.9167 +/- 0.0829 | 0.9628 +/- 0.0523 | 0.9512 +/- 0.0660 |
| 3 | Majority-vote ensemble | 40 | 0.6461 +/- 0.1333 | 0.9812 +/- 0.0249 | 0.9930 +/- 0.0185 | 0.9897 +/- 0.0227 |
| 4 | One-Class SVM | 40 | 0.6293 +/- 0.1258 | 0.9800 +/- 0.0289 | 0.9935 +/- 0.0195 | 0.9899 +/- 0.0231 |
| 5 | Isolation Forest | 40 | 0.6148 +/- 0.1435 | 0.8863 +/- 0.1514 | 0.8689 +/- 0.2052 | 0.7672 +/- 0.2935 |
| 6 | Tuned Isolation Forest | 40 | 0.6003 +/- 0.1543 | 0.8635 +/- 0.1674 | 0.8645 +/- 0.2102 | 0.7646 +/- 0.3073 |

These results show that the simple rule-based baseline performed strongly under the simulated attack conditions. This is expected because several scenarios, especially credential stuffing and brute-force traffic, produce direct indicators such as failed login attempts and high request counts.

However, the ROC-AUC and PR-AUC results show that the ensemble and One-Class SVM had very strong ranking ability. The majority-vote ensemble achieved ROC-AUC `0.9930 +/- 0.0185` and PR-AUC `0.9897 +/- 0.0227`, while One-Class SVM achieved ROC-AUC `0.9935 +/- 0.0195` and PR-AUC `0.9899 +/- 0.0231`. This means that these models can separate normal and anomalous windows well, but their default decision thresholds generate too many false positives.

## Results by Scenario

The best model differed depending on the traffic scenario. The following table shows the winner inside each individual scenario, not the overall winner across the full experiment:

| Scenario | Best model | F1-score |
| --- | --- | --- |
| Aggressive | Local Outlier Factor | 0.8626 +/- 0.0917 |
| Balanced | Local Outlier Factor | 0.5936 +/- 0.1081 |
| Burst traffic | Tuned Isolation Forest | 0.5200 +/- 0.1013 |
| Credential stuffing | Rule-based baseline | 0.8776 +/- 0.0255 |
| Endpoint scanning | Local Outlier Factor | 0.6391 +/- 0.0635 |
| Mixed attacks | Rule-based baseline | 0.6930 +/- 0.0056 |
| Mostly normal | Rule-based baseline | 0.8061 +/- 0.0232 |
| Slow brute force | Rule-based baseline | 0.7985 +/- 0.0250 |

Local Outlier Factor performed best in the balanced, aggressive, and endpoint-scanning scenarios. This suggests that LOF is effective when anomalous windows differ locally from nearby normal behavior. The rule-based baseline performed best in credential-stuffing, mostly-normal, slow-brute-force, and mixed-attack scenarios. These scenarios contain clear threshold-based indicators, such as repeated failed logins or abnormal request patterns.

The burst-traffic scenario was the most difficult. The best fixed-threshold F1-score in this scenario was only `0.5200 +/- 0.1013`, achieved by Tuned Isolation Forest. This indicates that burst traffic can be harder to distinguish from legitimate temporary traffic spikes.

## Threshold Tuning

Threshold tuning significantly improved many model results. For example, the majority-vote ensemble improved from an average F1-score of `0.6461 +/- 0.1333` to a tuned F1-score of `0.9812 +/- 0.0249`. One-Class SVM improved from `0.6293 +/- 0.1258` to `0.9800 +/- 0.0289`.

This shows that the anomaly scores produced by the models contain useful information, even when the default threshold is not optimal. The main issue is not always the model's ability to rank anomalies, but the decision boundary used to convert anomaly scores into final normal/anomalous labels.

For this reason, threshold calibration is an important part of applying anomaly detection in practice. A model with high ROC-AUC or PR-AUC may still perform poorly at a fixed threshold if the threshold is not adapted to the target environment.

## Confusion Matrix Interpretation

The confusion matrix results show that many unsupervised models detected most attack windows but also produced many false positives. For example, in the aggressive scenario, One-Class SVM detected all attacks on average, with `203.8` true positives and `0.0` false negatives, but it also produced `133.6` false positives. Similarly, Isolation Forest detected all attacks in that scenario but produced `135.6` false positives.

The rule-based baseline reduced false positives in several scenarios. In the mostly-normal scenario, it produced only `20.0` false positives on average, compared with `73.8` for LOF, `87.8` for Isolation Forest, and `90.8` for One-Class SVM. This explains why the rule-based baseline achieved the best F1-score in mostly-normal traffic.

In endpoint scanning, LOF and One-Class SVM detected all attacks on average, but both produced more than `160` false positives. The rule-based baseline had slightly fewer false positives, with `154.8`, but also missed a small number of attacks, with `1.6` false negatives.

These results show the trade-off between sensitivity and false alarms. Some models maximize recall by detecting nearly all attacks, but this often increases the number of normal windows incorrectly classified as anomalous.

## Discussion

The experimental results show that anomaly detection performance depends strongly on the type of attack and the traffic distribution. No single model was best in every scenario. The rule-based baseline performed strongly overall because the generated attacks often produced clear indicators, such as failed logins, endpoint errors, and high request rates.

At the same time, machine learning models remained valuable. LOF achieved the best fixed-threshold performance in several scenarios, including aggressive traffic, balanced traffic, and endpoint scanning. One-Class SVM and the ensemble model achieved very high ROC-AUC and PR-AUC, which indicates strong ranking quality. With threshold tuning, these models reached very high F1-scores.

The main practical conclusion is that anomaly detection should not rely only on a default model threshold. A calibrated threshold can greatly reduce false positives while preserving high attack detection. In a real deployment, this threshold should be selected using validation data that represents the target environment.

The results also show the value of comparing machine learning models against a simple baseline. If a rule-based method performs well, then machine learning must provide additional value through better generalization, adaptation to unknown patterns, or improved performance on complex scenarios.

## Limitations

The experiments were performed in a controlled Docker-based environment using synthetic traffic. This makes the experiments repeatable and safe, but it does not fully represent all behavior found in real production cloud systems.

The ground-truth labels were generated by the traffic simulator. This is useful for evaluation, but real systems may contain ambiguous behavior where the boundary between normal and malicious activity is less clear.

The model performance also depends on scenario configuration, including attack duration, request rate, number of IP addresses, normal traffic ratio, and contamination settings. Therefore, the reported results should be interpreted as performance under the designed experimental conditions, not as universal real-world accuracy.

## Future Work

Future improvements could include testing the system with real public intrusion detection datasets, adding more attack categories, and deploying the detector in a real cloud environment. The system could also be extended with adaptive threshold selection, online model updating, and explainability methods for showing why a traffic window was classified as anomalous.

Another direction is to combine rule-based detection with machine learning. Since the rule-based baseline performed well in clear attack scenarios and the machine learning models showed strong ranking ability, a hybrid system could use rules for obvious attacks and anomaly scores for less predictable behavior.

## Recommended Figures for Diploma

The following figures are the most useful for the diploma results section:

- `batch_f1_by_scenario.png`
- `batch_best_f1_by_scenario.png`
- `batch_ranked_summary_table.png`
- `batch_overall_ranking_table.png`
- `batch_roc_auc_by_scenario.png`
- `batch_pr_auc_by_scenario.png`
