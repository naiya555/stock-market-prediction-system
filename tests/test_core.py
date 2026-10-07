"""Unit tests for core application configuration, logging, and schemas."""

from datetime import datetime, timezone
import logging
import os
import re
import pytest

from app.core.config import Settings, get_settings
from app.core.logging_config import get_logger, setup_logging
from app.core.schemas import DataSourceMetadata, MarketOHLCV, MarketQuote, ValidationError


# ==============================================================================
# Configuration Tests
# ==============================================================================

def test_default_settings_load():
    """Verify default application settings initialize with expected safe defaults."""
    settings = Settings()
    assert settings.app_name == "Indian Stock Market Prediction System"
    assert settings.environment == "development"
    assert settings.debug is False
    assert settings.log_level == "INFO"
    assert settings.timezone == "Asia/Kolkata"
    assert settings.data_dir.name == "data"
    assert settings.model_dir.name == "models"
    assert settings.is_production() is False


def test_settings_environment_override(monkeypatch):
    """Verify settings pick up environment variable overrides correctly."""
    monkeypatch.setenv("APP_NAME", "Test Prediction System")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("APP_DEBUG", "true")
    monkeypatch.setenv("APP_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("APP_TIMEZONE", "UTC")

    settings = Settings.from_env()
    assert settings.app_name == "Test Prediction System"
    assert settings.environment == "production"
    assert settings.debug is True
    assert settings.log_level == "DEBUG"
    assert settings.timezone == "UTC"
    assert settings.is_production() is True


def test_get_settings_cached_singleton():
    """Verify get_settings returns consistent cached settings instance."""
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2


# ==============================================================================
# Logging Tests
# ==============================================================================

def test_logging_setup_and_logger():
    """Verify logging setup initializes cleanly and configures root logger."""
    setup_logging("DEBUG")
    root_logger = logging.getLogger()
    assert root_logger.level == logging.DEBUG

    logger = get_logger("app.core.test")
    assert logger.name == "app.core.test"


# ==============================================================================
# Canonical Schema Contracts Tests
# ==============================================================================

def test_valid_market_ohlcv_creation():
    """Verify valid MarketOHLCV bar is created and retains explicit point-in-time."""
    dt = datetime(2026, 10, 7, 9, 15, tzinfo=timezone.utc)
    bar = MarketOHLCV(
        symbol="RELIANCE",
        timestamp=dt,
        open=2500.0,
        high=2550.0,
        low=2490.0,
        close=2540.0,
        volume=150000,
        source="test_adapter",
    )

    assert bar.symbol == "RELIANCE"
    assert bar.timestamp == dt
    assert bar.open == 2500.0
    assert bar.high == 2550.0
    assert bar.low == 2490.0
    assert bar.close == 2540.0
    assert bar.volume == 150000
    assert bar.source == "test_adapter"

    # Verify serialization
    data = bar.to_dict()
    assert data["symbol"] == "RELIANCE"
    assert data["timestamp"] == dt.isoformat()
    assert data["volume"] == 150000


@pytest.mark.parametrize(
    "symbol,o,h,l,c,v,source,expected_err",
    [
        ("", 100.0, 110.0, 95.0, 105.0, 100, "src", "symbol cannot be empty"),
        ("TCS", 0.0, 110.0, 95.0, 105.0, 100, "src", "open must be strictly positive"),
        ("TCS", 100.0, 90.0, 95.0, 105.0, 100, "src", "high (90.0) cannot be less than low (95.0)"),
        ("TCS", 100.0, 104.0, 95.0, 105.0, 100, "src", "high (104.0) cannot be lower than open (100.0) or close (105.0)"),
        ("TCS", 100.0, 110.0, 102.0, 105.0, 100, "src", "low (102.0) cannot be greater than open (100.0) or close (105.0)"),
        ("TCS", 100.0, 110.0, 95.0, 105.0, -1, "src", "volume cannot be negative"),
        ("TCS", 100.0, 110.0, 95.0, 105.0, 100, "", "source cannot be empty"),
    ],
)
def test_invalid_market_ohlcv_rejected(symbol, o, h, l, c, v, source, expected_err):
    dt = datetime(2026, 10, 7, 10, 0, tzinfo=timezone.utc)
    with pytest.raises(ValidationError, match=re.escape(expected_err)):
        MarketOHLCV(
            symbol=symbol,
            timestamp=dt,
            open=o,
            high=h,
            low=l,
            close=c,
            volume=v,
            source=source,
        )


def test_market_ohlcv_invalid_timestamp():
    """Verify non-datetime timestamp is rejected."""
    with pytest.raises(ValidationError, match="timestamp must be a valid datetime"):
        MarketOHLCV(
            symbol="INFY",
            timestamp="2026-10-07T10:00:00",  # type: ignore
            open=1500.0,
            high=1520.0,
            low=1490.0,
            close=1510.0,
            volume=50000,
            source="test_src",
        )


def test_valid_market_quote_creation():
    """Verify valid current market quote creation and serialization."""
    dt = datetime(2026, 10, 7, 15, 30, tzinfo=timezone.utc)
    quote = MarketQuote(
        symbol="infy",
        timestamp=dt,
        price=1525.50,
        previous_close=1500.00,
        volume=250000,
        source="live_feed",
    )

    # Symbol should be automatically normalized to uppercase
    assert quote.symbol == "INFY"
    assert quote.price == 1525.50
    assert quote.previous_close == 1500.00
    assert quote.volume == 250000

    data = quote.to_dict()
    assert data["symbol"] == "INFY"
    assert data["timestamp"] == dt.isoformat()


def test_invalid_market_quote_rejected():
    """Verify invalid quotes are rejected."""
    dt = datetime.now(timezone.utc)
    with pytest.raises(ValidationError, match="price must be strictly positive"):
        MarketQuote(symbol="TCS", timestamp=dt, price=0.0, source="test")

    with pytest.raises(ValidationError, match="symbol cannot be empty"):
        MarketQuote(symbol="", timestamp=dt, price=100.0, source="test")


def test_data_source_metadata():
    """Verify DataSourceMetadata validation and serialization."""
    dt = datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)
    meta = DataSourceMetadata(
        source_name="bhavcopy_daily",
        retrieved_at=dt,
        source_url="https://example.com/bhavcopy",
        details={"format": "csv"},
    )
    assert meta.source_name == "bhavcopy_daily"
    assert meta.retrieved_at == dt

    data = meta.to_dict()
    assert data["source_name"] == "bhavcopy_daily"
    assert data["retrieved_at"] == dt.isoformat()
    assert data["source_url"] == "https://example.com/bhavcopy"

    with pytest.raises(ValidationError, match="source_name cannot be empty"):
        DataSourceMetadata(source_name="   ", retrieved_at=dt)
