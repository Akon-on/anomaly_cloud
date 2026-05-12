import unittest
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from evaluate_models import (
    compute_metrics,
    compute_best_f1_threshold,
    format_metric,
)


class EvaluatorTests(unittest.TestCase):
    def test_compute_metrics_confusion_and_auc(self):
        y_true = pd.Series([0, 1, 0, 1])
        y_pred = pd.Series([0, 1, 1, 0])
        score = np.array([0.1, 0.9, 0.8, 0.2])

        metrics = compute_metrics(y_true, y_pred, score)

        # Basic confusion counts
        self.assertEqual(metrics["true_negatives"], 1)
        self.assertEqual(metrics["false_positives"], 1)
        self.assertEqual(metrics["false_negatives"], 1)
        self.assertEqual(metrics["true_positives"], 1)

        # AUCs should be numeric when both classes present
        self.assertIsNotNone(metrics.get("roc_auc"))
        self.assertIsNotNone(metrics.get("pr_auc"))
        self.assertGreaterEqual(metrics["roc_auc"], 0.0)
        self.assertLessEqual(metrics["roc_auc"], 1.0)

    def test_compute_best_f1_threshold_simple(self):
        y_true = pd.Series([0, 1, 0, 1, 1])
        score = np.array([0.1, 0.9, 0.2, 0.8, 0.7])

        res = compute_best_f1_threshold(y_true, score)
        self.assertIn("best_f1", res)
        self.assertGreaterEqual(res["best_f1"], 0.0)
        self.assertLessEqual(res["best_f1"], 1.0)

    def test_format_metric(self):
        self.assertEqual(format_metric(np.nan), "N/A")
        self.assertEqual(format_metric(0.123456), "0.1235")

    def test_csv_write_roundtrip(self):
        # Simulate one model row and ensure CSV roundtrip preserves columns
        row = {
            "model": "isolation_forest",
            "precision": 0.5,
            "recall": 0.4,
            "f1": 0.45,
            "accuracy": 0.6,
            "true_negatives": 1,
            "false_positives": 1,
            "false_negatives": 1,
            "true_positives": 1,
            "roc_auc": 0.75,
            "pr_auc": 0.7,
            "best_threshold": 0.5,
            "best_precision": 0.5,
            "best_recall": 0.4,
            "best_f1": 0.45,
            "label_source": "test",
            "evaluation_mode": "in_sample_unsupervised",
            "train_samples": 10,
        }

        df = pd.DataFrame([row])
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "model_comparison.csv"
            df.to_csv(p, index=False)
            read = pd.read_csv(p)
            self.assertIn("model", read.columns)
            self.assertEqual(len(read), 1)


if __name__ == "__main__":
    unittest.main()
