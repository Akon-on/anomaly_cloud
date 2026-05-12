import numpy as np
import pandas as pd


def compute_feature_drift_scores(
    baseline_df: pd.DataFrame,
    current_df: pd.DataFrame,
    feature_columns: list[str],
) -> dict[str, float]:
    scores = {}
    for col in feature_columns:
        base = baseline_df[col].to_numpy(dtype=float)
        cur = current_df[col].to_numpy(dtype=float)

        base_mean = float(np.mean(base))
        base_std = float(np.std(base))
        cur_mean = float(np.mean(cur))

        if base_std == 0:
            scores[col] = 0.0 if cur_mean == base_mean else abs(cur_mean - base_mean)
        else:
            scores[col] = abs(cur_mean - base_mean) / base_std

    return scores


def compute_global_drift_score(
    baseline_df: pd.DataFrame,
    current_df: pd.DataFrame,
    feature_columns: list[str],
) -> float:
    feature_scores = compute_feature_drift_scores(baseline_df, current_df, feature_columns)
    if not feature_scores:
        return 0.0
    return float(np.mean(list(feature_scores.values())))


def detect_concept_drift(
    baseline_df: pd.DataFrame,
    current_df: pd.DataFrame,
    feature_columns: list[str],
    threshold: float = 1.0,
) -> tuple[bool, float, dict[str, float]]:
    score_by_feature = compute_feature_drift_scores(
        baseline_df,
        current_df,
        feature_columns,
    )
    global_score = float(np.mean(list(score_by_feature.values()))) if score_by_feature else 0.0
    is_drift = global_score >= threshold
    return is_drift, global_score, score_by_feature
