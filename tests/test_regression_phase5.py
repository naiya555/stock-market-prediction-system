import numpy as np
import pandas as pd

from app.training.regression_phase5 import _regimes, uncertainty_audit


def test_regime_labels_are_reproducible() -> None:
    frame = pd.DataFrame({"close": np.linspace(100.0, 130.0, 80)})
    result = _regimes(frame)
    assert set(result["volatility_regime"].dropna()).issubset(
        {"low_volatility", "normal_volatility", "high_volatility"}
    )
    assert result["trend_regime"].iloc[-1] == "trending_up"


def test_uncertainty_requires_enough_residuals() -> None:
    frame = pd.DataFrame({"close": np.arange(10, dtype=float)})
    assert uncertainty_audit(frame)["status"] == "UNAVAILABLE"
