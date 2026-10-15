"""Market Data Module.

Provides abstractions and adapters for market data acquisition, normalization, and validation.
"""

from app.core.schemas import DataSourceMetadata, MarketOHLCV, MarketQuote
from app.market.cleaner import CleaningResult, CleaningSummary, clean_market_data
from app.market.indicators import (
    BollingerBandsSeries,
    MACDSeries,
    MovingAverageFeatures,
    calculate_bollinger_bands,
    calculate_ema,
    calculate_macd,
    calculate_rsi,
    calculate_sma,
    calculate_true_range,
    calculate_atr,
    calculate_roc,
    compute_moving_averages,
    compute_technical_indicators,
)
from app.market.candlestick import (
    CandlestickFeatures,
    calculate_candlestick_features,
    calculate_single_candlestick,
    compute_candlestick_features,
)
from app.market.pipeline import (
    MarketDataPipelineResult,
    process_market_data,
    run_market_data_pipeline,
)
from app.market.trend import (
    SwingPoint,
    TrendAnalysisResult,
    TrendClassification,
    analyze_market_trend,
    classify_market_structure,
    compute_rolling_trends,
    identify_swings,
    label_market_structure,
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
from app.market.benchmark import (
    BROAD_MARKET_BENCHMARK,
    BANKING_BENCHMARK,
    IT_BENCHMARK,
    SECTOR_BENCHMARK_MAP,
    MarketBreadthObservation,
    RelativePerformanceFeature,
    align_benchmark_series,
    compute_covariance,
    compute_market_breadth,
    compute_multi_symbol_breadth_series,
    compute_relative_performance,
    get_sector_benchmark,
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
    "MovingAverageFeatures",
    "MACDSeries",
    "BollingerBandsSeries",
    "calculate_sma",
    "calculate_ema",
    "calculate_rsi",
    "calculate_macd",
    "calculate_bollinger_bands",
    "calculate_true_range",
    "calculate_atr",
    "calculate_roc",
    "CandlestickFeatures",
    "calculate_candlestick_features",
    "calculate_single_candlestick",
    "compute_candlestick_features",
    "compute_moving_averages",
    "compute_technical_indicators",
    "MarketDataPipelineResult",
    "process_market_data",
    "run_market_data_pipeline",
    "SwingPoint",
    "TrendAnalysisResult",
    "TrendClassification",
    "identify_swings",
    "label_market_structure",
    "classify_market_structure",
    "analyze_market_trend",
    "compute_rolling_trends",
    "plot_closing_prices",
    "plot_daily_returns",
    "generate_market_charts",
    "BROAD_MARKET_BENCHMARK",
    "BANKING_BENCHMARK",
    "IT_BENCHMARK",
    "SECTOR_BENCHMARK_MAP",
    "MarketBreadthObservation",
    "RelativePerformanceFeature",
    "align_benchmark_series",
    "compute_covariance",
    "compute_market_breadth",
    "compute_multi_symbol_breadth_series",
    "compute_relative_performance",
    "get_sector_benchmark",
]


