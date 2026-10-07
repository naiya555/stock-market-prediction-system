"""Canonical Data Schema Contracts.

Defines standardized, immutable data contracts for market information.
Prevents provider-specific representations from leaking into downstream pipelines.
Preserves explicit point-in-time timestamps and data provenance.
"""

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, Optional


class ValidationError(ValueError):
    """Raised when canonical schema validation fails."""
    pass


@dataclass(frozen=True)
class DataSourceMetadata:
    """Provenance metadata tracking external source origin and retrieval time."""

    source_name: str
    retrieved_at: datetime
    source_url: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        if not self.source_name or not self.source_name.strip():
            raise ValidationError("source_name cannot be empty")
        if not isinstance(self.retrieved_at, datetime):
            raise ValidationError("retrieved_at must be a valid datetime instance")

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary representation."""
        data = asdict(self)
        data["retrieved_at"] = self.retrieved_at.isoformat()
        return data


@dataclass(frozen=True)
class MarketOHLCV:
    """Canonical point-in-time OHLCV bar for an individual equity or index."""

    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    source: str

    def __post_init__(self) -> None:
        # Validate symbol
        if not self.symbol or not self.symbol.strip():
            raise ValidationError("symbol cannot be empty")
        object.__setattr__(self, "symbol", self.symbol.strip().upper())

        # Validate timestamp
        if not isinstance(self.timestamp, datetime):
            raise ValidationError("timestamp must be a valid datetime instance")

        # Validate numeric types & bounds
        for price_field in ("open", "high", "low", "close"):
            val = getattr(self, price_field)
            if not isinstance(val, (int, float)) or isinstance(val, bool):
                raise ValidationError(f"{price_field} must be a numeric value")
            if val <= 0:
                raise ValidationError(f"{price_field} must be strictly positive (got {val})")

        if not isinstance(self.volume, int) or isinstance(self.volume, bool):
            raise ValidationError(f"volume must be an integer (got {self.volume})")
        if self.volume < 0:
            raise ValidationError(f"volume cannot be negative (got {self.volume})")

        # Validate source
        if not self.source or not self.source.strip():
            raise ValidationError("source cannot be empty")
        object.__setattr__(self, "source", self.source.strip())

        # Physical OHLC boundary checks
        if self.high < self.low:
            raise ValidationError(f"high ({self.high}) cannot be less than low ({self.low})")
        if self.high < max(self.open, self.close):
            raise ValidationError(
                f"high ({self.high}) cannot be lower than open ({self.open}) or close ({self.close})"
            )
        if self.low > min(self.open, self.close):
            raise ValidationError(
                f"low ({self.low}) cannot be greater than open ({self.open}) or close ({self.close})"
            )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize record to dictionary with ISO formatted timestamp."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


@dataclass(frozen=True)
class MarketQuote:
    """Canonical current price quote for an individual equity or index."""

    symbol: str
    timestamp: datetime
    price: float
    source: str
    previous_close: Optional[float] = None
    volume: Optional[int] = None

    def __post_init__(self) -> None:
        if not self.symbol or not self.symbol.strip():
            raise ValidationError("symbol cannot be empty")
        object.__setattr__(self, "symbol", self.symbol.strip().upper())

        if not isinstance(self.timestamp, datetime):
            raise ValidationError("timestamp must be a valid datetime instance")

        if not isinstance(self.price, (int, float)) or isinstance(self.price, bool):
            raise ValidationError("price must be a numeric value")
        if self.price <= 0:
            raise ValidationError(f"price must be strictly positive (got {self.price})")

        if self.previous_close is not None:
            if not isinstance(self.previous_close, (int, float)) or isinstance(self.previous_close, bool):
                raise ValidationError("previous_close must be numeric")
            if self.previous_close <= 0:
                raise ValidationError("previous_close must be strictly positive")

        if self.volume is not None:
            if not isinstance(self.volume, int) or isinstance(self.volume, bool):
                raise ValidationError("volume must be an integer")
            if self.volume < 0:
                raise ValidationError("volume cannot be negative")

        if not self.source or not self.source.strip():
            raise ValidationError("source cannot be empty")
        object.__setattr__(self, "source", self.source.strip())

    def to_dict(self) -> Dict[str, Any]:
        """Serialize quote to dictionary with ISO formatted timestamp."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data
