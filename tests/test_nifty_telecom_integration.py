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

from app.core.schemas import MarketOHLCV
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

        # First bar: hyphenated OHLC set to close
        b0 = bars[0]
        assert b0.symbol == "NIFTY_TELECOMMUNICATIONS"
        assert b0.timestamp.year == 2024 and b0.timestamp.month == 1 and b0.timestamp.day == 1
        assert b0.close == 2450.75
        assert b0.open == 2450.75
        assert b0.high == 2450.75
        assert b0.low == 2450.75
        assert b0.volume == 0  # Zero volume strictly preserved, no fabrication
        assert b0.source == "nifty_indices"

        # Third bar: explicit OHLC
        b2 = bars[2]
        assert b2.open == 2485.0
        assert b2.high == 2500.0
        assert b2.low == 2475.0
        assert b2.close == 2495.5
        assert b2.volume == 0

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
    """Verify that market data pipeline and feature generation support index bars with zero volume."""

    @pytest.fixture
    def sample_index_bars(self) -> list[MarketOHLCV]:
        """Generate 60 bars of valid daily index data with zero volume."""
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
                    open=price,
                    high=price + 5.0,
                    low=price - 5.0,
                    close=price,
                    volume=0,  # Zero volume
                    source="nifty_indices",
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
        # Zero volume integrity check (no volume fabrication)
        assert (dataset.X["volume"] == 0).all()


class TestPredictionServiceSafeBehavior:
    """Verify that equity models are not silently reused for index forecasting."""

    def test_prediction_service_rejects_bhartiartl_model_for_index(self) -> None:
        service = PredictionService()
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
                open=2500.0,
                high=2500.0,
                low=2500.0,
                close=2500.0,
                volume=0,
                source="nifty_indices",
            ),
            MarketOHLCV(
                symbol="NIFTY_TELECOMMUNICATIONS",
                timestamp=datetime(2024, 1, 2, tzinfo=timezone.utc),
                open=2500.0,
                high=2550.0,
                low=2500.0,
                close=2550.0,  # +2%
                volume=0,
                source="nifty_indices",
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
            h_db = hashlib.sha256(db_path.read_bytes()).hexdigest().lower()
            assert h_db == PROTECTED_DB_HASH, f"data/predictions.db was unexpectedly modified: {h_db}"

        gitkeep_path = Path("models/.gitkeep")
        if gitkeep_path.exists():
            h_gk = hashlib.sha256(gitkeep_path.read_bytes()).hexdigest().lower()
            assert h_gk == PROTECTED_MODELS_GITKEEP_HASH, f"models/.gitkeep was unexpectedly modified: {h_gk}"
