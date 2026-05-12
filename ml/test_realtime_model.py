import unittest

import numpy as np

from model import normalize_log_record, score_to_predictions, trim_history


class RealtimeModelTests(unittest.TestCase):
    def test_score_to_predictions_marks_high_scores_as_anomalies(self):
        scores = np.array([0.05, 0.2, 0.8])

        predictions = score_to_predictions(scores, threshold=0.2)

        self.assertEqual(predictions.tolist(), [1, -1, -1])

    def test_normalize_log_record_rejects_bad_records(self):
        self.assertIsNone(normalize_log_record({"time": "bad", "ip": "1.1.1.1"}))
        self.assertEqual(
            normalize_log_record(
                {
                    "time": "123.4",
                    "ip": "1.1.1.1",
                    "endpoint": "/login",
                    "status": "fail",
                }
            )["time"],
            123.4,
        )

    def test_trim_history_keeps_recent_records(self):
        records = [
            {"time": 0.9},
            {"time": 590.0},
            {"time": 601.0},
        ]

        trimmed = trim_history(records, newest_time=601.0)

        self.assertEqual([record["time"] for record in trimmed], [590.0, 601.0])


if __name__ == "__main__":
    unittest.main()
