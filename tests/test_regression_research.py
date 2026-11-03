import numpy as np
import pandas as pd

from app.training.regression_research import _metrics, _normalized_features


def test_regression_metrics_use_price_units_and_direction() -> None:
    actual = np.array([100.0, 110.0, 90.0])
    predicted = np.array([101.0, 108.0, 95.0])
    reference = np.array([100.0, 100.0, 100.0])

    metrics = _metrics(actual, predicted, reference)

    assert metrics.samples == 3
    assert metrics.mae == np.mean(np.abs(predicted - actual))
    assert metrics.directional_accuracy == 2 / 3


def test_price_features_are_normalized_to_current_close() -> None:
    frame = pd.DataFrame({
        "current_close": [100.0, 200.0],
        "close": [100.0, 220.0],
        "sma_10": [95.0, 210.0],
        "daily_return": [0.01, -0.02],
        "volume": [99.0, 399.0],
    })

    result = _normalized_features(frame, ["close", "sma_10", "daily_return", "volume"])

    assert np.allclose(result["close"], [0.0, 0.1])
    assert np.allclose(result["sma_10"], [-0.05, 0.05])
    assert np.allclose(result["daily_return"], [0.01, -0.02])
    assert np.isfinite(result.to_numpy()).all()
