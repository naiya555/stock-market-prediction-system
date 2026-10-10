"""Market Data Pipeline Orchestration Layer.

Connects the historical market data provider, data cleaning layer,
returns/volatility feature engine, and technical indicator engine into a unified,
deterministic, and auditable end-to-end pipeline for Indian equities.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence

from app.core.logging_config import get_logger
from app.core.schemas import MarketOHLCV
from app.market.cleaner import CleaningSummary, clean_market_data
from app.market.indicators import MovingAverageFeatures, compute_moving_averages
from app.market.providers.base import BaseMarketDataProvider
from app.market.providers.yfinance_provider import YFinanceProvider
from app.market.returns import ReturnFeatures, compute_market_returns

logger = get_logger(__name__)


@dataclass(frozen=True)
class MarketDataPipelineResult:
    """Canonical output container holding all artifacts from the market data pipeline."""

    symbol: str
    raw_records: List[MarketOHLCV]
    cleaned_records: List[MarketOHLCV]
    cleaning_summary: CleaningSummary
    features: List[ReturnFeatures]
    indicators: List[MovingAverageFeatures] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        """Whether the pipeline produced any valid cleaned records."""
        return len(self.cleaned_records) == 0

    @property
    def record_count(self) -> int:
        """Number of validated records with features."""
        return len(self.features)

    def to_feature_dicts(self) -> List[Dict[str, Any]]:
        """Convert computed return and volatility features to flat dictionary list."""
        return [f.to_dict() for f in self.features]

    def to_indicator_dicts(self) -> List[Dict[str, Any]]:
        """Convert computed moving average features to flat dictionary list."""
        return [ind.to_dict() for ind in self.indicators]

    def to_dict(self) -> Dict[str, Any]:
        """Convert entire pipeline summary to dictionary for logging and audits."""
        return {
            "symbol": self.symbol,
            "raw_count": len(self.raw_records),
            "cleaned_count": len(self.cleaned_records),
            "feature_count": len(self.features),
            "indicator_count": len(self.indicators),
            "cleaning_summary": self.cleaning_summary.to_dict(),
        }


def process_market_data(
    raw_records: Sequence[MarketOHLCV],
    rolling_return_windows: Sequence[int] = (3, 5),
    volatility_windows: Sequence[int] = (5,),
    trading_days: int = 252,
    sma_windows: Sequence[int] = (5, 10),
    ema_windows: Sequence[int] = (5, 10),
    rsi_periods: Sequence[int] = (14,),
    macd_fast: Optional[int] = 12,
    macd_slow: Optional[int] = 26,
    macd_signal: Optional[int] = 9,
) -> MarketDataPipelineResult:
    """Process an existing sequence of raw MarketOHLCV records through cleaning, returns, and indicators.

    Offline operation: Does not perform any network calls. Safe for unit testing
    and deterministic replay.

    Args:
        raw_records: Raw canonical MarketOHLCV records from any provider adapter.
        rolling_return_windows: Multi-session windows for rolling returns (default (3, 5)).
        volatility_windows: Multi-session windows for rolling volatility (default (5,)).
        trading_days: Annual trading session count (default 252 for Indian equities).
        sma_windows: Multi-session windows for Simple Moving Average (default (5, 10)).
        ema_windows: Multi-session windows for Exponential Moving Average (default (5, 10)).
        rsi_periods: Multi-session windows for Relative Strength Index (default (14,)).
        macd_fast: Fast EMA period for MACD (default 12, or None to skip).
        macd_slow: Slow EMA period for MACD (default 26, or None to skip).
        macd_signal: Signal EMA period for MACD (default 9, or None to skip).

    Returns:
        MarketDataPipelineResult containing raw records, cleaned records, cleaning summary,
        computed return/volatility features, and technical indicators.
    """
    raw_list = list(raw_records)
    symbol = raw_list[0].symbol if raw_list else ""

    logger.info("Processing market data pipeline for %s (%d raw bars)", symbol or "EMPTY", len(raw_list))

    cleaning_res = clean_market_data(raw_list)
    cleaned_list = cleaning_res.records
    cleaning_sum = cleaning_res.summary

    features = compute_market_returns(
        cleaned_list,
        rolling_return_windows=rolling_return_windows,
        volatility_windows=volatility_windows,
        trading_days=trading_days,
    )

    indicators = compute_moving_averages(
        cleaned_list,
        sma_windows=sma_windows,
        ema_windows=ema_windows,
        rsi_periods=rsi_periods,
        macd_fast=macd_fast,
        macd_slow=macd_slow,
        macd_signal=macd_signal,
    )

    logger.info(
        "Pipeline completed for %s: %d raw -> %d clean -> %d feature records -> %d indicator records",
        symbol or "EMPTY",
        len(raw_list),
        len(cleaned_list),
        len(features),
        len(indicators),
    )

    return MarketDataPipelineResult(
        symbol=symbol,
        raw_records=raw_list,
        cleaned_records=cleaned_list,
        cleaning_summary=cleaning_sum,
        features=features,
        indicators=indicators,
    )


def run_market_data_pipeline(
    symbol: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    lookback_days: Optional[int] = None,
    provider: Optional[BaseMarketDataProvider] = None,
    interval: str = "1d",
    rolling_return_windows: Sequence[int] = (3, 5),
    volatility_windows: Sequence[int] = (5,),
    trading_days: int = 252,
    sma_windows: Sequence[int] = (5, 10),
    ema_windows: Sequence[int] = (5, 10),
    rsi_periods: Sequence[int] = (14,),
    macd_fast: Optional[int] = 12,
    macd_slow: Optional[int] = 26,
    macd_signal: Optional[int] = 9,
) -> MarketDataPipelineResult:
    """Execute end-to-end market data acquisition, cleaning, feature engineering, and indicator computation.

    Orchestrates:
    1. Historical data acquisition via BaseMarketDataProvider (defaults to YFinanceProvider)
    2. Data cleaning, duplicate resolution, and domain validation via clean_market_data
    3. Return and volatility feature computation via compute_market_returns
    4. Technical indicator computation (SMA, EMA, RSI, MACD) via compute_moving_averages

    Args:
        symbol: Market ticker symbol (e.g. 'BHARTIARTL').
        start_date: Inclusive start datetime for historical range (optional; defaults to end_date - lookback_days).
        end_date: Historical range end datetime (optional; defaults to now).
        lookback_days: Number of calendar days of historical lookback when start_date is omitted (default 180).
        provider: Provider instance implementing BaseMarketDataProvider.
        interval: Bar resolution (default '1d').
        rolling_return_windows: Multi-session windows for rolling returns (default (3, 5)).
        volatility_windows: Multi-session windows for rolling volatility (default (5,)).
        trading_days: Annual trading session count (default 252).
        sma_windows: Multi-session windows for Simple Moving Average (default (5, 10)).
        ema_windows: Multi-session windows for Exponential Moving Average (default (5, 10)).
        rsi_periods: Multi-session windows for Relative Strength Index (default (14,)).
        macd_fast: Fast EMA period for MACD (default 12, or None to skip).
        macd_slow: Slow EMA period for MACD (default 26, or None to skip).
        macd_signal: Signal EMA period for MACD (default 9, or None to skip).

    Returns:
        MarketDataPipelineResult with all pipeline stage artifacts.
    """
    active_provider = provider or YFinanceProvider()

    active_end = end_date or datetime.now()
    if start_date is not None:
        active_start = start_date
    else:
        days = lookback_days if lookback_days is not None else 180
        active_start = active_end - timedelta(days=days)

    logger.info(
        "Starting end-to-end pipeline: %s [%s to %s] via %s",
        symbol,
        active_start.date(),
        active_end.date(),
        active_provider.name,
    )

    raw_records = active_provider.fetch_historical_ohlcv(
        symbol=symbol,
        start_date=active_start,
        end_date=active_end,
        interval=interval,
    )

    return process_market_data(
        raw_records=raw_records,
        rolling_return_windows=rolling_return_windows,
        volatility_windows=volatility_windows,
        trading_days=trading_days,
        sma_windows=sma_windows,
        ema_windows=ema_windows,
        rsi_periods=rsi_periods,
        macd_fast=macd_fast,
        macd_slow=macd_slow,
        macd_signal=macd_signal,
    )
