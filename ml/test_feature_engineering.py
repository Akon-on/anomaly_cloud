import unittest

import pandas as pd

from feature_engineering import FEATURE_COLUMNS, build_feature_frame


class FeatureEngineeringTests(unittest.TestCase):
    def test_build_feature_frame_uses_expected_columns(self):
        raw_df = pd.DataFrame(
            [
                {
                    "time": 1,
                    "ip": "10.0.0.1",
                    "endpoint": "/login",
                    "status": "OK",
                    "user_agent": "AgentA",
                },
                {
                    "time": 2,
                    "ip": "10.0.0.1",
                    "endpoint": "/login",
                    "status": "fail",
                    "user_agent": "AgentA",
                },
                {
                    "time": 3,
                    "ip": "10.0.0.1",
                    "endpoint": "/dashboard",
                    "status": "ok",
                    "user_agent": "AgentB",
                },
                {
                    "time": 4,
                    "ip": "10.0.0.1",
                    "endpoint": "/admin",
                    "status": "error_404",
                    "status_code": 404,
                    "method": "GET",
                    "user_agent": "AgentB",
                },
            ]
        )

        features = build_feature_frame(raw_df, window_size=10)

        self.assertEqual(len(features), 1)
        self.assertTrue(all(column in features.columns for column in FEATURE_COLUMNS))
        row = features.iloc[0]
        self.assertEqual(row["requests_per_window"], 4)
        self.assertEqual(row["login_attempts"], 2)
        self.assertAlmostEqual(row["login_ratio"], 2 / 4)
        self.assertAlmostEqual(row["failed_login_ratio"], 1 / 2)
        self.assertEqual(row["unique_user_agents"], 2)
        self.assertEqual(row["successful_requests"], 2)
        self.assertEqual(row["error_requests"], 1)
        self.assertAlmostEqual(row["error_ratio"], 1 / 4)

    def test_missing_required_columns_raise_clear_error(self):
        raw_df = pd.DataFrame(
            [
                {
                    "time": 1,
                    "ip": "10.0.0.1",
                    "endpoint": "/login",
                }
            ]
        )

        with self.assertRaises(ValueError) as context:
            build_feature_frame(raw_df, window_size=10)

        self.assertIn("status", str(context.exception))


if __name__ == "__main__":
    unittest.main()
