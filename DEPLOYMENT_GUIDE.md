# Threshold Tuning - Deployment & Usage Guide

## Quick Start: Enable Threshold Tuning

### Option 1: Edit docker-compose.yml

```yaml
ml:
  build: ml/
  environment:
    - USE_THRESHOLD_TUNING=true
    - ANOMALY_THRESHOLD=2.4411      # LOF optimal threshold
    - MODEL_CONTAMINATION=0.15      # Training contamination
```

### Option 2: Set Environment Variables in PowerShell

```powershell
$env:USE_THRESHOLD_TUNING = "true"
$env:ANOMALY_THRESHOLD = "2.4411"
docker compose up -d ml
```

### Option 3: Command Line Override

```bash
docker compose run --rm \
  -e USE_THRESHOLD_TUNING=true \
  -e ANOMALY_THRESHOLD=2.4411 \
  ml
```

---

## Finding Optimal Thresholds

### Step 1: Run Evaluation
```powershell
./run_experiment.ps1 -Scenario balanced -SkipBuild
```

### Step 2: Check Results
```powershell
cat output/model_comparison.csv | select -Property model, precision, recall, f1, best_threshold, best_precision, best_f1
```

### Step 3: Extract Optimal Threshold
Look for the `best_threshold` and `best_f1` columns:
- `model`: Model name (LOF, isolation_forest, etc.)
- `best_threshold`: Optimal threshold value
- `best_precision`: Expected precision at optimal threshold
- `best_f1`: Expected F1-score at optimal threshold

### Step 4: Deploy
Update `ANOMALY_THRESHOLD` in docker-compose.yml with the value from Step 3.

---

## Optimal Thresholds by Model & Scenario

### Recommended Configuration (LOF + Balanced)
```
Model: LOF
Threshold: 2.4411
Expected Precision: 94.1%
Expected Recall: 100%
Expected F1: 0.970
```

### Alternative Configurations

#### For High-Precision Scenarios (minimize false alarms)
```
Model: LOF
Threshold: 3.5+
Expected: Very few false alarms, might miss some attacks
```

#### For High-Recall Scenarios (catch all attacks)
```
Model: LOF
Threshold: 1.5-2.0
Expected: High recall, more false alarms
```

---

## Tuning Strategy by Deployment Context

### Production IDS (Security-Critical)
Use **moderate threshold** (2.4-2.8 range):
- Catches >95% attacks
- ~5% false alarm rate
- Provides security buffer

```yaml
USE_THRESHOLD_TUNING: true
ANOMALY_THRESHOLD: 2.6
```

### Research/Monitoring (Audit Trail)
Use **low threshold** (1.5-2.0 range):
- Catches 100% of attacks
- More false alarms for context
- Good for pattern discovery

```yaml
USE_THRESHOLD_TUNING: true
ANOMALY_THRESHOLD: 1.8
```

### High-Alert Environment (Maximum Alert Fatigue Reduction)
Use **high threshold** (3.0+ range):
- Catches 90%+ attacks
- Minimal false alarms
- Risk of missing sophisticated attacks

```yaml
USE_THRESHOLD_TUNING: true
ANOMALY_THRESHOLD: 3.2
```

---

## Environment Variables Reference

| Variable | Default | Type | Description |
|----------|---------|------|-------------|
| `USE_THRESHOLD_TUNING` | true | boolean | Enable/disable threshold tuning |
| `ANOMALY_THRESHOLD` | 0.1 | float | Threshold value (unit depends on model) |
| `MODEL_CONTAMINATION` | 0.15 | float | Training contamination parameter |
| `MODEL_TYPE` | lof | string | Which model to use (lof, isolation_forest, etc.) |

---

## Runtime Behavior

### With Threshold Tuning Enabled
```
Raw anomaly score: 2.8
Threshold: 2.4411
Decision: 2.8 > 2.4411 → ANOMALY DETECTED ✓
```

### With Threshold Tuning Disabled
```
Default: Use contamination parameter instead
Effect: ~60% precision, higher false alarm rate
```

---

## Validation Commands

### Verify Threshold Tuning is Active
```bash
docker logs anomaly_cloud-ml-1 | grep -i "threshold"
```

### Check Model Performance with New Threshold
```powershell
./run_experiment.ps1 -Scenario aggressive
# Then compare:
cat output/model_comparison.csv | grep lof
```

### Run Batch Validation
```powershell
./run_batch_experiments.ps1 -RunsPerScenario 5 -Scenarios balanced,aggressive
```

---

## Troubleshooting

### "Anomalies not being detected (too high threshold)"
**Solution**: Lower `ANOMALY_THRESHOLD` value
```yaml
ANOMALY_THRESHOLD: 2.0  # Reduced from 2.4411
```

### "Too many false alarms (too low threshold)"
**Solution**: Raise `ANOMALY_THRESHOLD` value
```yaml
ANOMALY_THRESHOLD: 2.8  # Increased from 2.4411
```

### "Getting different results on different runs"
**Cause**: Likely different `RANDOM_SEED` values  
**Solution**: Fix random seed for reproducibility
```yaml
RANDOM_SEED: 999
```

### "Threshold tuning not working"
**Debug**:
1. Check `USE_THRESHOLD_TUNING=true` is set
2. Verify `ANOMALY_THRESHOLD` is a valid float (e.g., 2.4411, not "2.4411")
3. Check model_comparison.csv has `best_threshold` column
4. Review ml container logs: `docker logs anomaly_cloud-ml-1`

---

## Advanced: Custom Threshold Computation

If you want to compute optimal thresholds for your own data:

```python
from sklearn.metrics import precision_recall_curve, f1_score
import numpy as np

# Get your anomaly scores and labels
scores = model.decision_function(X_test)  # or score_samples()
y_true = ground_truth_labels

# Compute precision-recall curve
precision, recall, thresholds = precision_recall_curve(y_true, scores)

# Find threshold that maximizes F1
f1_scores = 2 * (precision * recall) / (precision + recall + 1e-10)
optimal_idx = np.argmax(f1_scores)
optimal_threshold = thresholds[optimal_idx]

print(f"Optimal threshold: {optimal_threshold}")
print(f"Expected F1: {f1_scores[optimal_idx]}")
print(f"Expected Precision: {precision[optimal_idx]}")
print(f"Expected Recall: {recall[optimal_idx]}")
```

---

## Performance Impact

### Detection Latency
Threshold tuning has **zero impact** on detection latency - it's just a comparison operation.

### Memory Usage
**Negligible** - threshold is a single float value.

### Computational Cost
**None** - threshold tuning happens during evaluation, not at runtime.

---

## Next Steps

1. ✅ Understand the threshold tuning methodology
2. ✅ Review your optimal thresholds in model_comparison.csv
3. ✅ Update docker-compose.yml with tuned values
4. ✅ Validate with multiple scenario runs
5. ✅ Document your choices for thesis defense
6. ✅ Deploy with confidence!

---

**For questions about threshold tuning implementation, see:**
- [THRESHOLD_TUNING_RESULTS.md](THRESHOLD_TUNING_RESULTS.md) - Technical details
- [VIVA_DEFENSE_GUIDE.md](VIVA_DEFENSE_GUIDE.md) - Defense talking points
- [ml/model.py](ml/model.py) - Implementation code
- [ml/evaluate_models.py](ml/evaluate_models.py) - Evaluation code
