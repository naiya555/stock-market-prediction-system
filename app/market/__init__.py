"""Market Data Module.

Provides abstractions and adapters for market data acquisition, normalization, and validation.
"""

from app.core.schemas import DataSourceMetadata, MarketOHLCV, MarketQuote
from app.market.cleaner import CleaningResult, CleaningSummary, clean_market_data
from app.market.pipeline import (
    MarketDataPipelineResult,
    process_market_data,
    run_market_data_pipeline,
)
from app.market.providers.base import BaseMarketDataProvider
from app.market.providers.yfinance_provider import YFinanceProvider
from app.market.returns import (
    ReturnFeatures,
    calculate_daily_returns,
    calculate_rolling_returns,
    calculate_rolling_volatility,
    calculate_standard_deviation,
    compute_market_returns,
)
from app.market.visualizer import (
    generate_market_charts,
    plot_closing_prices,
    plot_daily_returns,
)

__all__ = [
    "BaseMarketDataProvider",
    "YFinanceProvider",
    "MarketOHLCV",
    "MarketQuote",
    "DataSourceMetadata",
    "clean_market_data",
    "CleaningResult",
    "CleaningSummary",
    "ReturnFeatures",
    "calculate_daily_returns",
    "calculate_rolling_returns",
    "calculate_standard_deviation",
    "calculate_rolling_volatility",
    "compute_market_returns",
    "MarketDataPipelineResult",
    "process_market_data",
    "run_market_data_pipeline",
    "plot_closing_prices",
    "plot_daily_returns",
    "generate_market_charts",
]


