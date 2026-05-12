# Ranked Long-Run Summary

Ranking rule: F1 mean desc, then PR-AUC mean desc, then ROC-AUC mean desc.

| Scenario      | Rank | Model            | Runs | F1 (mean ± std) | ROC-AUC (mean ± std) | PR-AUC (mean ± std) |
|---------------|------|------------------|------|-----------------|----------------------|---------------------|
| aggressive    | 1    | lof              | 10   | 0.4200 ± 0.0632 | 0.5357 ± 0.0974      | 0.7809 ± 0.0538     |
| aggressive    | 2    | ocsvm            | 10   | 0.2666 ± 0.1654 | 0.2095 ± 0.1234      | 0.6063 ± 0.1026     |
| aggressive    | 3    | isolation_forest | 10   | 0.2600 ± 0.0966 | 0.1286 ± 0.0779      | 0.5251 ± 0.0648     |
| balanced      | 1    | lof              | 10   | 0.4044 ± 0.1725 | 0.5013 ± 0.1056      | 0.6813 ± 0.0835     |
| balanced      | 2    | isolation_forest | 10   | 0.2528 ± 0.1252 | 0.4142 ± 0.1640      | 0.4914 ± 0.0692     |
| balanced      | 3    | ocsvm            | 10   | 0.2007 ± 0.1980 | 0.3408 ± 0.2031      | 0.5268 ± 0.1358     |
| mostly-normal | 1    | ocsvm            | 10   | 0.3940 ± 0.2139 | 0.3902 ± 0.1290      | 0.6014 ± 0.1231     |
| mostly-normal | 2    | isolation_forest | 10   | 0.2861 ± 0.1134 | 0.4813 ± 0.1043      | 0.5191 ± 0.0664     |
| mostly-normal | 3    | lof              | 10   | 0.2111 ± 0.0755 | 0.3247 ± 0.1033      | 0.4836 ± 0.0889     |
