"""Historical Market Data Visualization Layer.

Generates publication-quality, deterministic charts for historical market data:
1. Closing price time-series charts with clean date formatting and gridlines.
2. Daily percentage return charts highlighting positive/negative returns.

Uses the headless Agg backend of Matplotlib to operate reliably in server and
CLI environments without requiring an active display.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Union

import matplotlib
matplotlib.use("Agg")  # Enforce headless rendering
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

from app.core.logging_config import get_logger
from app.core.schemas import MarketOHLCV
from app.market.returns import ReturnFeatures

logger = get_logger(__name__)


def plot_closing_prices(
    records_or_features: Sequence[Union[MarketOHLCV, ReturnFeatures]],
    output_path: Union[str, Path],
    title: Optional[str] = None,
) -> Path:
    """Generate a clean historical closing price chart.

    Args:
        records_or_features: Chronological sequence of MarketOHLCV or ReturnFeatures.
        output_path: Destination path for the saved image file (e.g. .png).
        title: Optional custom chart title.

    Returns:
        Path object pointing to the written chart image.

    Raises:
        ValueError: If input sequence is empty.
    """
    if not records_or_features:
        raise ValueError("Cannot generate closing price chart: input data sequence is empty")

    # Enforce chronological ascending sort
    sorted_items = sorted(records_or_features, key=lambda x: x.timestamp)
    symbol = sorted_items[0].symbol
    dates = [item.timestamp for item in sorted_items]
    prices = [item.close for item in sorted_items]

    dest = Path(output_path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 5), dpi=150)

    # Plot price series with clean styling
    ax.plot(
        dates,
        prices,
        marker="o",
        color="#1f77b4",
        linewidth=2.0,
        markersize=5,
        label=f"{symbol} Close",
    )

    # Format Date X-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    if len(dates) <= 15:
        ax.xaxis.set_major_locator(mdates.DayLocator())
    fig.autofmt_xdate(rotation=30, ha="right")

    # Format Y-axis
    ax.yaxis.set_major_formatter(mtick.StrMethodFormatter("₹{x:,.2f}"))
    ax.set_ylabel("Closing Price (INR)", fontsize=11, fontweight="bold")
    ax.set_xlabel("Trading Session Date", fontsize=11, fontweight="bold")

    chart_title = title or f"{symbol} — Historical Daily Closing Price"
    ax.set_title(chart_title, fontsize=13, fontweight="bold", pad=12)

    ax.grid(True, linestyle="--", alpha=0.5, color="#cccccc")
    ax.legend(loc="upper left", framealpha=0.9)

    fig.tight_layout()
    fig.savefig(dest, bbox_inches="tight")
    plt.close(fig)

    logger.info("Saved closing price chart to %s (%d sessions)", dest, len(prices))
    return dest


def plot_daily_returns(
    features: Sequence[ReturnFeatures],
    output_path: Union[str, Path],
    title: Optional[str] = None,
) -> Path:
    """Generate a clean daily percentage returns chart with positive/negative color coding.

    Args:
        features: Sequence of ReturnFeatures records.
        output_path: Destination path for the saved image file.
        title: Optional custom chart title.

    Returns:
        Path object pointing to the written chart image.

    Raises:
        ValueError: If features sequence is empty or contains no valid daily returns.
    """
    if not features:
        raise ValueError("Cannot generate daily returns chart: features sequence is empty")

    sorted_features = sorted(features, key=lambda f: f.timestamp)
    symbol = sorted_features[0].symbol

    # Filter observations with valid daily returns (skipping first session where return is None)
    valid_points = [f for f in sorted_features if f.daily_return is not None]
    if not valid_points:
        raise ValueError("Cannot generate daily returns chart: no valid daily return observations exist")

    dest = Path(output_path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    dates = [p.timestamp for p in valid_points]
    rets = [p.daily_return * 100.0 for p in valid_points]  # Convert to percentage
    colors = ["#2ca02c" if r >= 0 else "#d62728" for r in rets]

    fig, ax = plt.subplots(figsize=(10, 4.5), dpi=150)

    # Plot return bars
    bars = ax.bar(dates, rets, color=colors, width=0.6, alpha=0.85, edgecolor="#333333", linewidth=0.5)

    # Zero reference line
    ax.axhline(0, color="#333333", linestyle="--", linewidth=0.8, alpha=0.7)

    # Format Date X-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    if len(dates) <= 15:
        ax.xaxis.set_major_locator(mdates.DayLocator())
    fig.autofmt_xdate(rotation=30, ha="right")

    # Format Y-axis with percentage symbol
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=2))
    ax.set_ylabel("Daily Return (%)", fontsize=11, fontweight="bold")
    ax.set_xlabel("Trading Session Date", fontsize=11, fontweight="bold")

    chart_title = title or f"{symbol} — Daily Percentage Returns"
    ax.set_title(chart_title, fontsize=13, fontweight="bold", pad=12)

    ax.grid(True, linestyle="--", alpha=0.5, color="#cccccc", axis="y")

    fig.tight_layout()
    fig.savefig(dest, bbox_inches="tight")
    plt.close(fig)

    logger.info("Saved daily returns chart to %s (%d sessions)", dest, len(rets))
    return dest


def generate_market_charts(
    features: Sequence[ReturnFeatures],
    output_dir: Union[str, Path] = "data/processed/charts",
    symbol: Optional[str] = None,
) -> Dict[str, Path]:
    """Generate both closing price and daily return charts into the target directory.

    Args:
        features: Sequence of ReturnFeatures records.
        output_dir: Target directory where chart PNGs will be saved.
        symbol: Optional symbol override.

    Returns:
        Dictionary mapping chart keys ('price_chart', 'returns_chart') to generated file Paths.
    """
    if not features:
        raise ValueError("Cannot generate charts: features sequence is empty")

    sym = symbol or features[0].symbol
    slug = sym.lower().replace(".", "_")
    target_dir = Path(output_dir)

    price_path = target_dir / f"{slug}_close_price.png"
    returns_path = target_dir / f"{slug}_daily_returns.png"

    plot_closing_prices(features, price_path, title=f"{sym} — Historical Daily Closing Price")
    plot_daily_returns(features, returns_path, title=f"{sym} — Daily Percentage Returns")

    return {
        "price_chart": price_path,
        "returns_chart": returns_path,
    }
