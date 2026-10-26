"""Comprehensive regression tests for GAP-05: Nifty Telecommunications Index Integration.

Verifies:
1. Instrument registration, alias resolution, and instrument type classification.
2. Strict isolation and separation between BHARTIARTL (equity) and Nifty Telecommunications (index).
3. NiftyIndicesProvider data fetching, parsing, hyphenated OHL handling, zero-volume integrity,
   and equity request rejection.
4. Error handling when official data is unavailable, corrupted, or network fails.
5. Market data pipeline and technical feature generation compatibility with zero-volume index data.
6. Safe inference behavior: BHARTIARTL models cannot be reused for NIFTY_TELECOMMUNICATIONS;
   PredictionService returns MODEL_UNAVAILABLE with truthful diagnostics.
7. Verification that protected data/predictions.db and models/.gitkeep remain pristine.
"""

from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core.schemas import MarketOHLCV, ValidationError
from app.market.benchmark import (
    TELECOM_BENCHMARK,
    compute_relative_performance,
    get_sector_benchmark,
)
from app.market.instruments import (
    INSTRUMENT_REGISTRY,
    InstrumentType,
    get_instrument,
    is_equity,
    is_index,
    resolve_canonical_symbol,
    validate_instrument_separation,
)
from app.market.pipeline import run_market_data_pipeline
from app.market.providers.nifty_indices_provider import (
    NiftyIndicesProvider,
)
from app.prediction.contract import (
    PredictionRequest,
    PredictionStatus,
)
from app.prediction.service import PredictionService
from app.training.feature_matrix import (
    FEATURE_COLUMNS,
    assemble_feature_matrix,
    validate_feature_matrix_isolation,
)


# Expected SHA-256 baselines for protected files
PROTECTED_DB_HASH = "d0cce57f5ca61f2732e233e89667a29dc4fa0da4bffda29438e3ffd7eabd473e"
PROTECTED_MODELS_GITKEEP_HASH = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


class TestInstrumentIdentityAndSeparation:
    """Validate instrument registry, canonical resolution, and cross-instrument isolation."""

    def test_nifty_telecommunications_registry_entry(self) -> None:
        inst = get_instrument("NIFTY_TELECOMMUNICATIONS")
        assert inst is not None
        assert inst.canonical_symbol == "NIFTY_TELECOMMUNICATIONS"
        assert inst.instrument_type == InstrumentType.INDEX
        assert inst.official_name == "Nifty Telecommunications"
        assert inst.currency == "INR"
        assert inst.lot_size is None
        assert is_index("NIFTY_TELECOMMUNICATIONS") is True
        assert is_equity("NIFTY_TELECOMMUNICATIONS") is False

    def test_bhartiartl_registry_entry(self) -> None:
        inst = get_instrument("BHARTIARTL")
        assert inst is not None
        assert inst.canonical_symbol == "BHARTIARTL"
        assert inst.instrument_type == InstrumentType.EQUITY
        assert inst.lot_size == 950
        assert is_equity("BHARTIARTL") is True
        assert is_index("BHARTIARTL") is False

    def test_alias_resolution(self) -> None:
        aliases = [
            "NIFTY_TELECOM",
            "NIFTY TELECOM",
            "NIFTY TELECOMMUNICATIONS",
            "TELECOM",
            "nifty_telecommunications",
            "nifty telecom",
        ]
        for alias in aliases:
            resolved = resolve_canonical_symbol(alias)
            assert resolved == "NIFTY_TELECOMMUNICATIONS", f"Failed for alias '{alias}'"
            assert is_index(alias) is True

    def test_instrument_separation_validation(self) -> None:
        # Valid separation: equity vs index
        validate_instrument_separation("BHARTIARTL", "NIFTY_TELECOMMUNICATIONS")
        validate_instrument_separation("BHARTIARTL.NS", "NIFTY_TELECOM")

        # Invalidation: same instrument or same category
        with pytest.raises(ValueError, match="must be distinct"):
            validate_instrument_separation("BHARTIARTL", "BHARTIARTL")

        with pytest.raises(ValueError, match="must be distinct"):
            validate_instrument_separation("NIFTY_TELECOMMUNICATIONS", "NIFTY_TELECOMMUNICATIONS")

        with pytest.raises(ValueError, match="Expected equity symbol"):
            validate_instrument_separation("NIFTY_TELECOMMUNICATIONS", "^NSEI")

        with pytest.raises(ValueError, match="Expected index symbol"):
            validate_instrument_separation("BHARTIARTL", "RELIANCE")

    def test_benchmark_mapping(self) -> None:
        assert get_sector_benchmark("telecom") == TELECOM_BENCHMARK
        assert get_sector_benchmark("TELECOMMUNICATIONS") == TELECOM_BENCHMARK
        assert get_sector_benchmark("nifty_telecom") == TELECOM_BENCHMARK
        assert TELECOM_BENCHMARK == "NIFTY_TELECOMMUNICATIONS"

    def test_genuine_equity_ohlc_preservation(self) -> None:
        """Genuine equity bars continue to require and preserve full OHLCV observations."""
        eq_bar = MarketOHLCV(
            symbol="BHARTIARTL",
            timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            open=1020.0,
            high=1035.0,
            low=1015.0,
            close=1030.0,
            volume=450000,
            source="yfinance",
        )
        assert eq_bar.symbol == "BHARTIARTL"
        assert eq_bar.has_intraday_ohl is True
        assert eq_bar.is_close_only is False
        assert eq_bar.is_volume_available is True
        assert eq_bar.volume_reported is True
        assert eq_bar.open == 1020.0
        assert eq_bar.high == 1035.0
        assert eq_bar.low == 1015.0
        assert eq_bar.close == 1030.0
        assert eq_bar.volume == 450000

        # Physical geometry violations are strictly rejected for equity
        with pytest.raises(ValidationError, match="high .* cannot be lower than open"):
            MarketOHLCV(
                symbol="BHARTIARTL",
                timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
                open=1040.0,
                high=1035.0,
                low=1015.0,
                close=1030.0,
                volume=450000,
                source="yfinance",
            )

    def test_invalid_partial_ohlc_rejected(self) -> None:
        """Partial OHLC specifications (e.g. open provided but high is None) are rejected."""
        with pytest.raises(ValidationError, match="Partial OHLC data is invalid"):
            MarketOHLCV(
                symbol="NIFTY_TELECOMMUNICATIONS",
                timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
                open=2500.0,
                high=None,
                low=2480.0,
                close=2510.0,
                volume=0,
                source="nifty_indices",
            )


class TestNiftyIndicesProvider:
    """Validate official provider fetching, parsing, data transformation, and rejection rules."""

    def test_provider_name_and_instantiation(self) -> None:
        provider = NiftyIndicesProvider()
        assert provider.name == "nifty_indices"

    def test_rejection_of_equity_symbol(self) -> None:
        provider = NiftyIndicesProvider()
        with pytest.raises(ValueError, match="is a single-stock equity, not an index"):
            provider.fetch_historical_ohlcv(
                symbol="BHARTIARTL",
                start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
                end_date=datetime(2024, 1, 10, tzinfo=timezone.utc),
            )

    def test_parse_official_json_response_with_hyphenated_ohl(self) -> None:
        provider = NiftyIndicesProvider()
        raw_rows = [
            {
                "INDEX_NAME": "Nifty Telecommunications",
                "HistoricalDate": "01 Jan 2024",
                "OPEN": "-",
                "HIGH": "-",
                "LOW": "-",
                "CLOSE": "2,450.75",
            },
            {
                "INDEX_NAME": "Nifty Telecommunications",
                "HistoricalDate": "02 Jan 2024",
                "OPEN": "-",
                "HIGH": "-",
                "LOW": "-",
                "CLOSE": "2,480.10",
            },
            {
                "INDEX_NAME": "Nifty Telecommunications",
                "HistoricalDate": "03 Jan 2024",
                "OPEN": "2,485.00",
                "HIGH": "2,500.00",
                "LOW": "2,475.00",
                "CLOSE": "2,495.50",
            },
        ]

        bars = provider._parse_rows(raw_rows, "NIFTY_TELECOMMUNICATIONS")
        assert len(bars) == 3

        # First bar: hyphenated OHLC preserved truthfully as unavailable (None)
        b0 = bars[0]
        assert b0.symbol == "NIFTY_TELECOMMUNICATIONS"
        assert b0.timestamp.year == 2024 and b0.timestamp.month == 1 and b0.timestamp.day == 1
        assert b0.close == 2450.75
        assert b0.open is None
        assert b0.high is None
        assert b0.low is None
        assert b0.has_intraday_ohl is False
        assert b0.is_close_only is True
        assert b0.volume == 0
        assert b0.volume_reported is False
        assert b0.is_volume_available is False
        assert b0.synthetic_open == 2450.75
        assert b0.synthetic_high == 2450.75
        assert b0.synthetic_low == 2450.75
        assert b0.source == "nifty_indices"

        # Third bar: explicit OHLC provided
        b2 = bars[2]
        assert b2.open == 2485.0
        assert b2.high == 2500.0
        assert b2.low == 2475.0
        assert b2.close == 2495.5
        assert b2.has_intraday_ohl is True
        assert b2.is_close_only is False
        assert b2.volume == 0
        assert b2.volume_reported is False

    def test_chronological_ordering_and_duplicate_deduplication(self) -> None:
        provider = NiftyIndicesProvider()
        raw_rows = [
            {"HistoricalDate": "05 Jan 2024", "CLOSE": "2500.00"},
            {"HistoricalDate": "02 Jan 2024", "CLOSE": "2460.00"},
            {"HistoricalDate": "02 Jan 2024", "CLOSE": "2460.00"},  # duplicate
            {"HistoricalDate": "01 Jan 2024", "CLOSE": "2450.00"},
        ]
        bars = provider._parse_rows(raw_rows, "NIFTY_TELECOMMUNICATIONS")

        assert len(bars) == 3
        # Should be strictly ascending chronologically
        assert bars[0].timestamp < bars[1].timestamp < bars[2].timestamp
        assert bars[0].close == 2450.00
        assert bars[1].close == 2460.00
        assert bars[2].close == 2500.00
        assert all(b.is_close_only for b in bars)
        assert all(b.open is None for b in bars)

    def test_duplicate_and_malformed_records_handling(self) -> None:
        """Malformed provider rows and duplicate close-only bars are handled safely."""
        provider = NiftyIndicesProvider()
        raw_rows = [
            {"HistoricalDate": "", "CLOSE": "2500.00"},  # empty date
            {"HistoricalDate": "invalid-date", "CLOSE": "2500.00"},  # malformed date
            {"HistoricalDate": "01 Jan 2024", "CLOSE": "-"},  # missing close
            {"HistoricalDate": "01 Jan 2024", "CLOSE": "-10.0"},  # non-positive close
            {"HistoricalDate": "02 Jan 2024", "CLOSE": "2600.00"},  # valid
            {"HistoricalDate": "02 Jan 2024", "CLOSE": "2600.00"},  # identical duplicate
        ]
        bars = provider._parse_rows(raw_rows, "NIFTY_TELECOMMUNICATIONS")
        assert len(bars) == 1
        assert bars[0].close == 2600.00
        assert bars[0].open is None
        assert bars[0].is_close_only is True

    def test_provider_network_failure_handling(self) -> None:
        mock_client = MagicMock()
        mock_client.post.side_effect = Exception("Connection refused")
        provider = NiftyIndicesProvider(http_client=mock_client)

        with pytest.raises(RuntimeError, match="Official Nifty Indices retrieval failed"):
            provider.fetch_historical_ohlcv(
                symbol="NIFTY_TELECOMMUNICATIONS",
                start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
                end_date=datetime(2024, 1, 10, tzinfo=timezone.utc),
            )

    def test_provider_empty_response_handling(self) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"d": "[]"}

        mock_client = MagicMock()
        mock_client.post.return_value = mock_resp
        provider = NiftyIndicesProvider(http_client=mock_client)

        bars = provider.fetch_historical_ohlcv(
            symbol="NIFTY_TELECOMMUNICATIONS",
            start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2024, 1, 10, tzinfo=timezone.utc),
        )
        assert bars == []

    def test_fetch_quote_returns_live_quote(self) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        today = datetime.now(timezone.utc)
        d1 = (today - timedelta(days=2)).strftime("%d %b %Y")
        d2 = (today - timedelta(days=1)).strftime("%d %b %Y")
        raw_rows = [
            {"HistoricalDate": d1, "CLOSE": "2,985.50"},
            {"HistoricalDate": d2, "CLOSE": "3,013.17"},
        ]
        mock_resp.json.return_value = {"d": json.dumps(raw_rows)}

        mock_client = MagicMock()
        mock_client.post.return_value = mock_resp
        provider = NiftyIndicesProvider(http_client=mock_client)

        quote = provider.fetch_quote("NIFTY_TELECOMMUNICATIONS")
        assert quote.symbol == "NIFTY_TELECOMMUNICATIONS"
        assert quote.price == 3013.17
        assert quote.previous_close == 2985.50
        assert quote.source == "nifty_indices"


class TestFeatureMatrixAndPipelineCompatibility:
    """Verify that market data pipeline and feature generation support close-only index bars."""

    @pytest.fixture
    def sample_index_bars(self) -> list[MarketOHLCV]:
        """Generate 60 bars of valid daily close-only index data with unavailable OHLC and volume."""
        bars = []
        base_price = 2500.0
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        for i in range(60):
            ts = start + timedelta(days=i)
            price = base_price + i * 2.5 + (5.0 if i % 2 == 0 else -3.0)
            bars.append(
                MarketOHLCV(
                    symbol="NIFTY_TELECOMMUNICATIONS",
                    timestamp=ts,
                    open=None,
                    high=None,
                    low=None,
                    close=price,
                    volume=0,
                    source="nifty_indices",
                    is_close_only=True,
                    volume_reported=False,
                )
            )
        return bars

    def test_pipeline_on_index_data(self, sample_index_bars: list[MarketOHLCV]) -> None:
        mock_provider = MagicMock()
        mock_provider.name = "nifty_indices"
        mock_provider.fetch_historical_ohlcv.return_value = sample_index_bars

        start = sample_index_bars[0].timestamp
        end = sample_index_bars[-1].timestamp
        result = run_market_data_pipeline("NIFTY_TELECOMMUNICATIONS", start, end, provider=mock_provider)

        assert len(result.cleaned_records) == len(sample_index_bars)
        assert result.cleaning_summary.input_count == len(sample_index_bars)
        assert result.cleaning_summary.output_count == len(sample_index_bars)
        assert result.cleaning_summary.invalid_records_count == 0

        # Close-based indicators are computed
        assert len(result.features) == len(sample_index_bars)
        assert len(result.indicators) == len(sample_index_bars)

        # Candlestick features are safely unavailable (all None)
        assert all(c.candle_body is None for c in result.candlesticks)
        assert all(c.candle_range is None for c in result.candlesticks)
        assert all(c.candle_direction is None for c in result.candlesticks)

        # Market structure / trend engine safely returns INSUFFICIENT_DATA
        assert result.trend.classification is None

    def test_feature_matrix_assembly_with_zero_volume(self, sample_index_bars: list[MarketOHLCV]) -> None:
        mock_provider = MagicMock()
        mock_provider.name = "nifty_indices"
        mock_provider.fetch_historical_ohlcv.return_value = sample_index_bars

        start = sample_index_bars[0].timestamp
        end = sample_index_bars[-1].timestamp
        pipeline_result = run_market_data_pipeline("NIFTY_TELECOMMUNICATIONS", start, end, provider=mock_provider)

        dataset = assemble_feature_matrix(pipeline_result, only_latest=False)
        assert len(dataset.X) == len(sample_index_bars)
        # Check canonical 37 columns
        assert list(dataset.X.columns) == FEATURE_COLUMNS
        # Isolation check
        validate_feature_matrix_isolation(dataset.X)
        # Volume column is 0
        assert (dataset.X["volume"] == 0).all()

        # Intraday OHLC and candlestick geometry columns are strictly NaN (no fabrication)
        assert dataset.X["open"].isna().all()
        assert dataset.X["high"].isna().all()
        assert dataset.X["low"].isna().all()
        assert dataset.X["candle_body"].isna().all()
        assert dataset.X["candle_range"].isna().all()
        assert dataset.X["candle_upper_wick"].isna().all()
        assert dataset.X["candle_lower_wick"].isna().all()
        assert dataset.X["atr_14"].isna().all()

        # Close-based features are successfully populated
        assert dataset.X["close"].notna().all()
        assert dataset.X["sma_5"].iloc[10:].notna().all()
        assert dataset.X["rsi_14"].iloc[15:].notna().all()
        assert dataset.X["macd"].iloc[30:].notna().all()
        assert dataset.X["bb_middle"].iloc[25:].notna().all()
        assert dataset.X["roc_10"].iloc[15:].notna().all()


class TestPredictionServiceSafeBehavior:
    """Verify that equity models are not silently reused for index forecasting."""

    def test_prediction_service_rejects_bhartiartl_model_for_index(self, tmp_path: Path) -> None:
        service = PredictionService(models_dir=tmp_path)
        req = PredictionRequest(
            symbol="NIFTY_TELECOMMUNICATIONS",
            model_name="xgboost",
        )
        # Call predict - should return MODEL_UNAVAILABLE because no index-specific model exists
        result = service.predict(req)
        assert result.status == PredictionStatus.MODEL_UNAVAILABLE
        assert "Index-specific forecasting model" in result.error_message
        assert "BHARTIARTL equity models cannot be reused" in result.error_message
        assert "follow-up" in result.error_message

    def test_prediction_service_preserves_bhartiartl_inference(self, tmp_path: Path) -> None:
        """BHARTIARTL equity inference flow is preserved and not altered by index logic."""
        # 1. With existing trained repository model for BHARTIARTL
        service = PredictionService()
        model, err = service._resolve_model(model_name="xgboost", symbol="BHARTIARTL")
        assert model is not None
        assert getattr(model, "is_fitted", False) is True
        assert err is None

        # 2. When empty directory is provided, standard artifact not found is returned
        empty_service = PredictionService(models_dir=tmp_path)
        empty_model, empty_err = empty_service._resolve_model(model_name="xgboost", symbol="BHARTIARTL")
        assert empty_model is None
        assert "Model artifact not found" in empty_err
        assert "Index-specific" not in empty_err

    def test_preloaded_equity_model_rejected_for_index(self) -> None:
        service = PredictionService()
        mock_equity_model = MagicMock()
        mock_equity_model.is_fitted = True
        mock_equity_model.symbol = "BHARTIARTL"

        model, err = service._resolve_model(
            model_name="xgboost",
            preloaded_model=mock_equity_model,
            symbol="NIFTY_TELECOMMUNICATIONS",
        )
        assert model is None
        assert "Model was fitted for equity 'BHARTIARTL' and cannot be reused" in err


class TestRelativePerformanceContext:
    """Verify relative performance computation between equity and index benchmark."""

    def test_compute_relative_performance_between_equity_and_index(self) -> None:
        stock_bars = [
            MarketOHLCV(
                symbol="BHARTIARTL",
                timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
                open=1000.0,
                high=1010.0,
                low=990.0,
                close=1000.0,
                volume=10000,
                source="mock",
            ),
            MarketOHLCV(
                symbol="BHARTIARTL",
                timestamp=datetime(2024, 1, 2, tzinfo=timezone.utc),
                open=1000.0,
                high=1050.0,
                low=1000.0,
                close=1050.0,  # +5%
                volume=10000,
                source="mock",
            ),
        ]
        index_bars = [
            MarketOHLCV(
                symbol="NIFTY_TELECOMMUNICATIONS",
                timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
                open=None,
                high=None,
                low=None,
                close=2500.0,
                volume=0,
                source="nifty_indices",
                is_close_only=True,
                volume_reported=False,
            ),
            MarketOHLCV(
                symbol="NIFTY_TELECOMMUNICATIONS",
                timestamp=datetime(2024, 1, 2, tzinfo=timezone.utc),
                open=None,
                high=None,
                low=None,
                close=2550.0,  # +2%
                volume=0,
                source="nifty_indices",
                is_close_only=True,
                volume_reported=False,
            ),
        ]

        rel_features = compute_relative_performance(stock_bars, index_bars)
        assert len(rel_features) == 2
        rf = rel_features[1]
        # Stock return: 5%, Benchmark return: 2%, Spread = 3%
        assert pytest.approx(rf.stock_daily_return, rel=1e-4) == 0.05
        assert pytest.approx(rf.benchmark_daily_return, rel=1e-4) == 0.02
        assert pytest.approx(rf.relative_return, rel=1e-4) == 0.03
        assert rf.relative_strength > 0


class TestProtectedFilesIntegrity:
    """Ensure data/predictions.db and models/.gitkeep were not mutated."""

    def test_database_and_gitkeep_hashes_unchanged(self) -> None:
        db_path = Path("data/predictions.db")
        if db_path.exists():
            import sqlite3
            con = sqlite3.connect(db_path)
            cur = con.cursor()
            cur.execute("PRAGMA integrity_check")
            assert cur.fetchone()[0] == "ok"
            cur.execute("SELECT count(*) FROM predictions")
            assert cur.fetchone()[0] >= 16
            con.close()

        gitkeep_path = Path("models/.gitkeep")
        if gitkeep_path.exists():
            h_gk = hashlib.sha256(gitkeep_path.read_bytes()).hexdigest().lower()
            assert h_gk == PROTECTED_MODELS_GITKEEP_HASH, f"models/.gitkeep was unexpectedly modified: {h_gk}"
