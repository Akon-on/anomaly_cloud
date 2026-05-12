import unittest

import pandas as pd

from drift import detect_concept_drift


class DriftTests(unittest.TestCase):
    def test_no_drift_when_distributions_are_similar(self):
        baseline = pd.DataFrame(
            {
                "requests_per_window": [10, 11, 9, 10],
                "failed_logins": [1, 0, 1, 0],
                "login_ratio": [0.2, 0.18, 0.22, 0.2],
            }
        )
        current = pd.DataFrame(
            {
                "requests_per_window": [10, 10, 11, 9],
                "failed_logins": [1, 0, 1, 0],
                "login_ratio": [0.2, 0.19, 0.21, 0.2],
            }
        )

        is_drift, global_score, _ = detect_concept_drift(
            baseline,
            current,
            ["requests_per_window", "failed_logins", "login_ratio"],
            threshold=0.8,
        )

        self.assertFalse(is_drift)
        self.assertLess(global_score, 0.8)

    def test_detect_drift_when_means_shift(self):
        baseline = pd.DataFrame(
            {
                "requests_per_window": [10, 11, 9, 10],
                "failed_logins": [1, 0, 1, 0],
                "login_ratio": [0.2, 0.18, 0.22, 0.2],
            }
        )
        current = pd.DataFrame(
            {
                "requests_per_window": [35, 34, 36, 37],
                "failed_logins": [5, 4, 6, 5],
                "login_ratio": [0.75, 0.72, 0.77, 0.74],
            }
        )

        is_drift, global_score, by_feature = detect_concept_drift(
            baseline,
            current,
            ["requests_per_window", "failed_logins", "login_ratio"],
            threshold=1.0,
        )

        self.assertTrue(is_drift)
        self.assertGreaterEqual(global_score, 1.0)
        self.assertEqual(set(by_feature.keys()), {"requests_per_window", "failed_logins", "login_ratio"})


if __name__ == "__main__":
    unittest.main()
