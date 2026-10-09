"""Market Data Pipeline Orchestration Layer.

Connects the historical market data provider, data cleaning layer, and
returns/volatility feature engine into a unified, deterministic, and
auditable end-to-end pipeline for Indian equities.
"""

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from app.core.logging_config import get_logger
from app.core.schemas import MarketOHLCV
from app.market.cleaner import CleaningSummary, clean_market_data
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

    def to_dict(self) -> Dict[str, Any]:
        """Convert entire pipeline summary to dictionary for logging and audits."""
        return {
            "symbol": self.symbol,
            "raw_count": len(self.raw_records),
            "cleaned_count": len(self.cleaned_records),
            "feature_count": len(self.features),
            "cleaning_summary": self.cleaning_summary.to_dict(),
        }


def process_market_data(
    raw_records: Sequence[MarketOHLCV],
    rolling_return_windows: Sequence[int] = (3, 5),
    volatility_windows: Sequence[int] = (5,),
    trading_days: int = 252,
) -> MarketDataPipelineResult:
    """Process an existing sequence of raw MarketOHLCV records through cleaning and feature generation.

    Offline operation: Does not perform any network calls. Safe for unit testing
    and deterministic replay.

    Args:
        raw_records: Raw canonical MarketOHLCV records from any provider adapter.
        rolling_return_windows: Multi-session windows for rolling returns (default (3, 5)).
        volatility_windows: Multi-session windows for rolling volatility (default (5,)).
        trading_days: Annual trading session count (default 252 for Indian equities).

    Returns:
        MarketDataPipelineResult containing raw records, cleaned records, cleaning summary,
        and computed return/volatility features.
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

    logger.info(
        "Pipeline completed for %s: %d raw -> %d clean -> %d feature records",
        symbol or "EMPTY",
        len(raw_list),
        len(cleaned_list),
        len(features),
    )

    return MarketDataPipelineResult(
        symbol=symbol,
        raw_records=raw_list,
        cleaned_records=cleaned_list,
        cleaning_summary=cleaning_sum,
        features=features,
    )


def run_market_data_pipeline(
    symbol: str,
    start_date: datetime,
    end_date: datetime,
    provider: Optional[BaseMarketDataProvider] = None,
    interval: str = "1d",
    rolling_return_windows: Sequence[int] = (3, 5),
    volatility_windows: Sequence[int] = (5,),
    trading_days: int = 252,
) -> MarketDataPipelineResult:
    """Execute end-to-end market data acquisition, cleaning, and feature engineering.

    Orchestrates:
    1. Historical data acquisition via BaseMarketDataProvider (defaults to YFinanceProvider)
    2. Data cleaning, duplicate resolution, and domain validation via clean_market_data
    3. Return and volatility feature computation via compute_market_returns

    Args:
        symbol: Market ticker symbol (e.g. 'BHARTIARTL').
        start_date: Inclusive start datetime for historical range.
        end_date: Historical range end datetime.
        provider: Provider instance implementing BaseMarketDataProvider.
        interval: Bar resolution (default '1d').
        rolling_return_windows: Multi-session windows for rolling returns (default (3, 5)).
        volatility_windows: Multi-session windows for rolling volatility (default (5,)).
        trading_days: Annual trading session count (default 252).

    Returns:
        MarketDataPipelineResult with all pipeline stage artifacts.
    """
    active_provider = provider or YFinanceProvider()

    logger.info(
        "Starting end-to-end pipeline: %s [%s to %s] via %s",
        symbol,
        start_date.date(),
        end_date.date(),
        active_provider.name,
    )

    raw_records = active_provider.fetch_historical_ohlcv(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        interval=interval,
    )

    return process_market_data(
        raw_records=raw_records,
        rolling_return_windows=rolling_return_windows,
        volatility_windows=volatility_windows,
        trading_days=trading_days,
    )
