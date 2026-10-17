"""Live and Near-Real-Time Market Quote Contracts.

Defines canonical data contracts for near-real-time equity quotes with explicit
freshness metadata, session state alignment, and provider delay disclosures.
"""

from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from app.core.schemas import MarketQuote, ValidationError
from app.market.session import MarketSessionState


class DataFreshnessStatus(str, Enum):
    """Categorical freshness assessment of incoming market data."""

    FRESH = "FRESH"      # Quote timestamp matches current session activity
    DELAYED = "DELAYED"  # Quote is subject to standard provider delay (~15m for free tiers)
    STALE = "STALE"      # Quote is older than active session tolerance
    UNKNOWN = "UNKNOWN"  # Insufficient metadata to evaluate freshness


DEFAULT_DELAY_DISCLAIMER = (
    "Near-real-time quotes provided via Yahoo Finance are typically delayed by ~15 minutes "
    "during active market sessions. These quotes are intended for analytical and decision support, "
    "not high-frequency or algorithmic order execution."
)


@dataclass(frozen=True)
class LiveQuote:
    """Canonical near-real-time price quote with operational metadata."""

    symbol: str
    price: float
    timestamp: datetime
    retrieved_at: datetime
    source: str
    session_state: MarketSessionState
    freshness_status: DataFreshnessStatus
    open_price: Optional[float] = None
    day_high: Optional[float] = None
    day_low: Optional[float] = None
    previous_close: Optional[float] = None
    change: Optional[float] = None
    change_percent: Optional[float] = None
    volume: Optional[int] = None
    currency: str = "INR"
    is_delayed: bool = True
    delay_minutes: int = 15
    disclaimer: str = DEFAULT_DELAY_DISCLAIMER

    def __post_init__(self) -> None:
        """Validate fields and enforce invariant bounds."""
        if not self.symbol or not self.symbol.strip():
            raise ValidationError("symbol cannot be empty")
        object.__setattr__(self, "symbol", self.symbol.strip().upper())

        if not isinstance(self.price, (int, float)) or isinstance(self.price, bool):
            raise ValidationError("price must be numeric")
        if self.price <= 0:
            raise ValidationError(f"price must be strictly positive (got {self.price})")

        if not isinstance(self.timestamp, datetime):
            raise ValidationError("timestamp must be a valid datetime instance")

        if not isinstance(self.retrieved_at, datetime):
            raise ValidationError("retrieved_at must be a valid datetime instance")

        if not self.source or not self.source.strip():
            raise ValidationError("source cannot be empty")
        object.__setattr__(self, "source", self.source.strip())

        if not isinstance(self.session_state, MarketSessionState):
            raise ValidationError(f"session_state must be a MarketSessionState instance, got {type(self.session_state)}")

        if not isinstance(self.freshness_status, DataFreshnessStatus):
            raise ValidationError(f"freshness_status must be a DataFreshnessStatus instance, got {type(self.freshness_status)}")

        # Optional price bounds
        for price_field in ("open_price", "day_high", "day_low", "previous_close"):
            val = getattr(self, price_field)
            if val is not None:
                if not isinstance(val, (int, float)) or isinstance(val, bool):
                    raise ValidationError(f"{price_field} must be numeric")
                if val <= 0:
                    raise ValidationError(f"{price_field} must be strictly positive (got {val})")

        if self.volume is not None:
            if not isinstance(self.volume, int) or isinstance(self.volume, bool):
                raise ValidationError("volume must be an integer")
            if self.volume < 0:
                raise ValidationError("volume cannot be negative")

    def to_market_quote(self) -> MarketQuote:
        """Downcast to core MarketQuote contract for backward compatibility."""
        return MarketQuote(
            symbol=self.symbol,
            timestamp=self.timestamp,
            price=self.price,
            source=self.source,
            previous_close=self.previous_close,
            volume=self.volume,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize quote to dictionary with ISO formatted timestamps and enum values."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        data["retrieved_at"] = self.retrieved_at.isoformat()
        data["session_state"] = self.session_state.value
        data["freshness_status"] = self.freshness_status.value
        return data
