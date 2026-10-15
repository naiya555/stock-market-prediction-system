"""Unit and regression tests for Day 26: NIFTY benchmark and sector context engine."""

from datetime import datetime, timedelta
import math
import pytest

from app.core.schemas import MarketOHLCV
from app.market.benchmark import (
    BROAD_MARKET_BENCHMARK,
    BANKING_BENCHMARK,
    IT_BENCHMARK,
    MarketBreadthObservation,
    RelativePerformanceFeature,
    align_benchmark_series,
    compute_covariance,
    compute_market_breadth,
    compute_multi_symbol_breadth_series,
    compute_relative_performance,
    get_sector_benchmark,
)
from app.market.providers.yfinance_provider import YFinanceProvider


def _make_bar(symbol: str, date_str: str, close: float, source: str = "mock") -> MarketOHLCV:
    """Helper to generate valid MarketOHLCV fixture."""
    ts = datetime.fromisoformat(date_str)
    return MarketOHLCV(
        symbol=symbol,
        timestamp=ts,
        open=close,
        high=close * 1.01,
        low=close * 0.99,
        close=close,
        volume=100000,
        source=source,
    )


class TestBenchmarkSymbolsAndProvider:
    """Test symbol resolution and sector mapping."""

    def test_provider_resolves_index_tickers(self) -> None:
        provider = YFinanceProvider()

        # Pure index tickers starting with ^
        base, query = provider._resolve_symbols("^NSEI")
        assert base == "^NSEI"
        assert query == "^NSEI"

        base, query = provider._resolve_symbols("^NSEBANK")
        assert base == "^NSEBANK"
        assert query == "^NSEBANK"

        # Index aliases
        base, query = provider._resolve_symbols("NIFTY")
        assert base == "NIFTY"
        assert query == "^NSEI"

        base, query = provider._resolve_symbols("NIFTY50")
        assert base == "NIFTY50"
        assert query == "^NSEI"

        base, query = provider._resolve_symbols("BANKNIFTY")
        assert base == "BANKNIFTY"
        assert query == "^NSEBANK"

        base, query = provider._resolve_symbols("NIFTYIT")
        assert base == "NIFTYIT"
        assert query == "^CNXIT"

    def test_provider_preserves_equity_symbols(self) -> None:
        provider = YFinanceProvider()

        base, query = provider._resolve_symbols("BHARTIARTL")
        assert base == "BHARTIARTL"
        assert query == "BHARTIARTL.NS"

        base, query = provider._resolve_symbols("RELIANCE.NS")
        assert base == "RELIANCE"
        assert query == "RELIANCE.NS"

    def test_sector_benchmark_resolution(self) -> None:
        assert get_sector_benchmark("banking") == BANKING_BENCHMARK
        assert get_sector_benchmark("FINANCIAL_SERVICES") == BANKING_BENCHMARK
        assert get_sector_benchmark("it") == IT_BENCHMARK
        assert get_sector_benchmark("tech") == IT_BENCHMARK
        assert get_sector_benchmark("broad") == BROAD_MARKET_BENCHMARK
        assert get_sector_benchmark("unknown_sector") == BROAD_MARKET_BENCHMARK


class TestCovarianceAndAlignment:
    """Test sample covariance and temporal session alignment."""

    def test_compute_covariance_synthetic(self) -> None:
        # Perfectly correlated sequences with slope = 2: y = 2x
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [2.0, 4.0, 6.0, 8.0, 10.0]
        cov = compute_covariance(x, y, ddof=1)
        # Var(x) = 2.5, Cov(x, y) = 2 * Var(x) = 5.0
        assert cov is not None
        assert pytest.approx(cov, rel=1e-5) == 5.0

    def test_compute_covariance_guards(self) -> None:
        # Insufficient observations
        assert compute_covariance([1.0], [2.0], ddof=1) is None
        # Mismatched lengths
        assert compute_covariance([1.0, 2.0], [1.0], ddof=1) is None
        # NaN handling
        assert compute_covariance([1.0, float("nan")], [2.0, 3.0], ddof=1) is None

    def test_align_benchmark_series_matching_dates(self) -> None:
        dates = ["2026-01-01T09:15:00", "2026-01-02T09:15:00", "2026-01-05T09:15:00"]
        stock_bars = [_make_bar("STOCK", d, 100.0) for d in dates]
        bench_bars = [_make_bar("^NSEI", d, 20000.0) for d in dates]

        aligned = align_benchmark_series(stock_bars, bench_bars)
        assert len(aligned) == 3
        for s, b in aligned:
            assert s is not None
            assert b is not None
            assert s.timestamp.date() == b.timestamp.date()

    def test_align_benchmark_series_handles_calendar_gaps(self) -> None:
        # Stock traded on Jan 1, Jan 2, Jan 3; Benchmark traded on Jan 1, Jan 3 (Jan 2 missing)
        stock_bars = [
            _make_bar("STOCK", "2026-01-01T09:15:00", 100.0),
            _make_bar("STOCK", "2026-01-02T09:15:00", 102.0),
            _make_bar("STOCK", "2026-01-03T09:15:00", 105.0),
        ]
        bench_bars = [
            _make_bar("^NSEI", "2026-01-01T09:15:00", 20000.0),
            _make_bar("^NSEI", "2026-01-03T09:15:00", 20100.0),
        ]

        aligned = align_benchmark_series(stock_bars, bench_bars)
        assert len(aligned) == 3
        assert aligned[0][1] is not None
        assert aligned[1][1] is None  # Jan 2 has no benchmark
        assert aligned[2][1] is not None


class TestRelativePerformance:
    """Test relative return, relative strength, rolling beta, and correlation."""

    def test_compute_relative_performance_empty(self) -> None:
        assert compute_relative_performance([], []) == []

    def test_compute_relative_performance_synthetic_beta_and_alpha(self) -> None:
        # 30 daily sessions. Benchmark starts at 20000 and grows +1% each day.
        # Stock starts at 100 and grows +2% each day.
        # Expected:
        # Stock return = 0.02, Bench return = 0.01
        # Alpha (rel return) = 0.01
        # Relative strength = Close_s / Close_b
        # 5d RS mom = (1.02/1.01)^5 - 1 ≈ 0.0504
        # Since returns are identical every day, Var(R_b) = 0, so beta guard triggers!
        # To get non-zero variance, let's create alternating returns:
        start_date = datetime(2026, 1, 1, 9, 15)
        stock_bars: list[MarketOHLCV] = []
        bench_bars: list[MarketOHLCV] = []

        curr_s = 100.0
        curr_b = 20000.0
        stock_bars.append(_make_bar("STOCK", start_date.isoformat(), curr_s))
        bench_bars.append(_make_bar("^NSEI", start_date.isoformat(), curr_b))

        # 25 sessions of fluctuating returns where R_stock = 2.0 * R_bench exactly:
        bench_ret_series = [0.01, -0.01, 0.02, -0.015, 0.005, -0.02, 0.015, 0.01, -0.005, 0.02] * 3
        for i, r_b in enumerate(bench_ret_series[:25]):
            r_s = 2.0 * r_b
            curr_b *= (1.0 + r_b)
            curr_s *= (1.0 + r_s)
            d = (start_date + timedelta(days=i + 1)).isoformat()
            stock_bars.append(_make_bar("STOCK", d, curr_s))
            bench_bars.append(_make_bar("^NSEI", d, curr_b))

        features = compute_relative_performance(stock_bars, bench_bars, beta_window=20, min_periods=10)
        assert len(features) == len(stock_bars)

        # Check early session (session 1)
        f1 = features[1]
        assert f1.stock_daily_return is not None
        assert f1.benchmark_daily_return is not None
        assert pytest.approx(f1.stock_daily_return, rel=1e-4) == 0.02
        assert pytest.approx(f1.benchmark_daily_return, rel=1e-4) == 0.01
        assert pytest.approx(f1.relative_return, rel=1e-4) == 0.01
        assert f1.relative_strength == pytest.approx(stock_bars[1].close / bench_bars[1].close, rel=1e-5)

        # Check session with sufficient history (t = 25)
        f_mature = features[-1]
        assert f_mature.rolling_beta_20d is not None
        # Because R_stock = 2 * R_bench exactly, theoretical beta = 2.0 and correlation = 1.0
        assert pytest.approx(f_mature.rolling_beta_20d, rel=1e-3) == 2.0
        assert f_mature.rolling_correlation_20d is not None
        assert pytest.approx(f_mature.rolling_correlation_20d, rel=1e-3) == 1.0

        # Check to_dict serialization
        d_dict = f_mature.to_dict()
        assert d_dict["symbol"] == "STOCK"
        assert d_dict["benchmark_symbol"] == "^NSEI"
        assert d_dict["rolling_beta_20d"] == pytest.approx(2.0, rel=1e-3)
        assert d_dict["rolling_correlation_20d"] == pytest.approx(1.0, rel=1e-3)

    def test_zero_variance_guard(self) -> None:
        # Constant prices mean returns are 0.0 every day -> Var(R_b) == 0.0
        start = datetime(2026, 1, 1, 9, 15)
        stock_bars = [_make_bar("STOCK", (start + timedelta(days=i)).isoformat(), 100.0) for i in range(25)]
        bench_bars = [_make_bar("^NSEI", (start + timedelta(days=i)).isoformat(), 20000.0) for i in range(25)]

        features = compute_relative_performance(stock_bars, bench_bars, beta_window=20, min_periods=10)
        # Beta and correlation should safely be None without crashing with ZeroDivisionError
        for f in features:
            assert f.rolling_beta_20d is None
            assert f.rolling_correlation_20d is None


class TestMarketBreadth:
    """Test cross-sectional market breadth calculation."""

    def test_compute_market_breadth_snapshot(self) -> None:
        ts = datetime(2026, 1, 10, 15, 30)
        returns = {
            "RELIANCE": 0.02,
            "TCS": 0.01,
            "HDFCBANK": -0.015,
            "INFY": 0.0,
            "ICICIBANK": None,  # Missing
        }
        sma_status = {
            "RELIANCE": True,
            "TCS": True,
            "HDFCBANK": False,
            "INFY": True,
            "ICICIBANK": None,
        }

        obs = compute_market_breadth(ts, returns, sma_status)
        assert obs.total_stocks == 4  # 2 advances + 1 decline + 1 unchanged
        assert obs.advances == 2
        assert obs.declines == 1
        assert obs.unchanged == 1
        assert obs.net_advances == 1
        assert obs.advance_decline_ratio == 2.0  # 2 / 1
        assert obs.breadth_thrust == 0.5  # 2 / 4
        # 3 True out of 4 valid in sma_status
        assert obs.pct_above_sma20 == 0.75

        # Serialization test
        obs_dict = obs.to_dict()
        assert obs_dict["total_stocks"] == 4
        assert obs_dict["advance_decline_ratio"] == 2.0
        assert obs_dict["pct_above_sma20"] == 0.75

    def test_compute_market_breadth_zero_declines_guard(self) -> None:
        ts = datetime(2026, 1, 10, 15, 30)
        returns = {"RELIANCE": 0.02, "TCS": 0.01}
        obs = compute_market_breadth(ts, returns)
        assert obs.advances == 2
        assert obs.declines == 0
        assert obs.advance_decline_ratio is None  # Prevents ZeroDivisionError
        assert obs.breadth_thrust == 1.0

    def test_compute_multi_symbol_breadth_series(self) -> None:
        # Create 3 stocks over 25 sessions
        start = datetime(2026, 1, 1, 9, 15)
        multi_data: dict[str, list[MarketOHLCV]] = {"STOCK_A": [], "STOCK_B": [], "STOCK_C": []}

        for i in range(25):
            d = (start + timedelta(days=i)).isoformat()
            # Stock A trend up
            multi_data["STOCK_A"].append(_make_bar("STOCK_A", d, 100.0 + i * 2.0))
            # Stock B trend down
            multi_data["STOCK_B"].append(_make_bar("STOCK_B", d, 200.0 - i * 1.5))
            # Stock C flat
            multi_data["STOCK_C"].append(_make_bar("STOCK_C", d, 50.0))

        series = compute_multi_symbol_breadth_series(multi_data, sma_window=20)
        assert len(series) == 25
        # Early bar t=0 has no daily return, so total_stocks == 0
        assert series[0].total_stocks == 0
        # Subsequent sessions have 1 advance (A), 1 decline (B), 1 unchanged (C)
        for s in series[1:]:
            assert s.advances == 1
            assert s.declines == 1
            assert s.unchanged == 1
            assert s.total_stocks == 3
            assert s.net_advances == 0
            assert s.advance_decline_ratio == 1.0
