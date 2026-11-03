import numpy as np
import pandas as pd

from app.training.regression_phase4 import _target_frame


def test_target_frame_uses_trading_row_horizon() -> None:
    frame = pd.DataFrame({
        "timestamp": pd.date_range("2026-01-01", periods=4),
        "current_close": [100.0, 101.0, 103.0, 102.0],
        "close": [100.0, 101.0, 103.0, 102.0],
        "open": [99.0, 100.0, 102.0, 101.0],
    })
    targets = _target_frame(frame, "close", 3)
    assert targets.loc[0, "target"] == 102.0
    assert np.isnan(targets.loc[1, "target"])
    assert targets.loc[0, "target_timestamp"] == frame.loc[3, "timestamp"]


def test_return_target_is_relative_to_current_close() -> None:
    frame = pd.DataFrame({
        "timestamp": pd.date_range("2026-01-01", periods=2),
        "current_close": [100.0, 110.0],
        "close": [100.0, 110.0],
    })
    targets = _target_frame(frame, "return", 1)
    assert np.isclose(targets.loc[0, "target"], 0.1)
