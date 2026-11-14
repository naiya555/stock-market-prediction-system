import numpy as np
import pandas as pd

from app.training.regression_phase6 import _intervals, evaluate_walk_forward


def test_walk_forward_uses_prior_close_and_oos_rows() -> None:
    frame = pd.DataFrame({
        "timestamp": pd.date_range("2020-01-01", periods=160),
        "close": np.linspace(100.0, 180.0, 160),
    })
    result = evaluate_walk_forward(frame, n_splits=4)
    assert result["total_out_of_sample_samples"] > 0
    assert result["folds"][0]["overall"]["samples"] > 0


def test_intervals_require_prior_residual_history() -> None:
    actual = np.array([1.0, 2.0])
    predicted = np.array([1.0, 1.0])
    result = _intervals(actual, predicted, np.array([0.0] * 10))
    assert all(value["status"] == "UNAVAILABLE" for value in result.values())
