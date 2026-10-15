"""Canonical Macroeconomic, Regulatory, and External Events Schema Contracts.

Defines standardized, immutable data contracts for macroeconomic releases,
regulatory announcements, government fiscal notices, and external market observations.
Enforces point-in-time temporal integrity, provenance tracking, and explicit
separation between publication time, announcement time, effective time, and ingestion time.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

from app.core.schemas import ValidationError


class EventCategory(str, Enum):
    """Broad categories for macroeconomic and regulatory events."""

    MONETARY_POLICY = "monetary_policy"
    REGULATORY = "regulatory"
    GOVERNMENT = "government"
    MACRO_INDICATOR = "macro_indicator"
    EXTERNAL_MARKET = "external_market"
    OTHER = "other"


@dataclass(frozen=True)
class StructuredEventValue:
    """Quantitative measurement or policy rate associated with an event.

    Captures numeric changes (e.g. repo rate, inflation rate, crude settle price)
    with explicit units, reference periods, and previous values without fabricating metrics.
    """

    metric_name: str
    value: float
    unit: str
    prior_value: Optional[float] = None
    change: Optional[float] = None
    reference_period: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.metric_name or not self.metric_name.strip():
            raise ValidationError("metric_name cannot be empty")
        object.__setattr__(self, "metric_name", self.metric_name.strip().lower())

        if not isinstance(self.value, (int, float)) or isinstance(self.value, bool):
            raise ValidationError("value must be a numeric float or int")
        if not math.isfinite(self.value):
            raise ValidationError("value must be a finite number")
        object.__setattr__(self, "value", float(self.value))

        if not self.unit or not self.unit.strip():
            raise ValidationError("unit cannot be empty")
        object.__setattr__(self, "unit", self.unit.strip())

        if self.prior_value is not None:
            if not isinstance(self.prior_value, (int, float)) or isinstance(self.prior_value, bool):
                raise ValidationError("prior_value must be a numeric float or int")
            if not math.isfinite(self.prior_value):
                raise ValidationError("prior_value must be finite")
            object.__setattr__(self, "prior_value", float(self.prior_value))

        if self.change is not None:
            if not isinstance(self.change, (int, float)) or isinstance(self.change, bool):
                raise ValidationError("change must be a numeric float or int")
            if not math.isfinite(self.change):
                raise ValidationError("change must be finite")
            object.__setattr__(self, "change", float(self.change))
        elif self.prior_value is not None:
            # Safely compute change if prior value is present
            object.__setattr__(self, "change", round(self.value - self.prior_value, 6))

        if self.reference_period is not None:
            ref = self.reference_period.strip()
            object.__setattr__(self, "reference_period", ref if ref else None)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize structured value to dictionary."""
        return {
            "metric_name": self.metric_name,
            "value": self.value,
            "unit": self.unit,
            "prior_value": self.prior_value,
            "change": self.change,
            "reference_period": self.reference_period,
        }


@dataclass(frozen=True)
class MacroEvent:
    """Canonical representation of an ingested macroeconomic, regulatory, or policy event."""

    title: str
    category: EventCategory
    event_type: str
    source_org: str
    ingested_at: datetime
    published_at: Optional[datetime] = None
    announced_at: Optional[datetime] = None
    effective_at: Optional[datetime] = None
    url: Optional[str] = None
    affected_sectors: Tuple[str, ...] = field(default_factory=tuple)
    affected_symbols: Tuple[str, ...] = field(default_factory=tuple)
    structured_value: Optional[StructuredEventValue] = None
    summary: Optional[str] = None
    provider: str = "generic"
    is_verified: bool = True
    event_id: str = ""
    raw_metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Validate title
        if not self.title or not self.title.strip():
            raise ValidationError("title cannot be empty")
        object.__setattr__(self, "title", self.title.strip())

        # Validate category
        if isinstance(self.category, str):
            try:
                object.__setattr__(self, "category", EventCategory(self.category.lower()))
            except ValueError:
                raise ValidationError(f"Invalid event category: '{self.category}'")
        elif not isinstance(self.category, EventCategory):
            raise ValidationError("category must be an EventCategory instance")

        # Validate event_type
        if not self.event_type or not self.event_type.strip():
            raise ValidationError("event_type cannot be empty")
        object.__setattr__(self, "event_type", self.event_type.strip().lower())

        # Validate source_org
        if not self.source_org or not self.source_org.strip():
            raise ValidationError("source_org cannot be empty")
        object.__setattr__(self, "source_org", self.source_org.strip())

        # Validate provider
        if not self.provider or not self.provider.strip():
            raise ValidationError("provider cannot be empty")
        object.__setattr__(self, "provider", self.provider.strip())

        # Validate ingestion timestamp (mandatory, timezone-aware)
        if not isinstance(self.ingested_at, datetime):
            raise ValidationError("ingested_at must be a valid datetime instance")
        if self.ingested_at.tzinfo is None:
            raise ValidationError("ingested_at must be timezone-aware")

        # Validate publication timestamp (optional, timezone-aware if present)
        if self.published_at is not None:
            if not isinstance(self.published_at, datetime):
                raise ValidationError("published_at must be a valid datetime instance")
            if self.published_at.tzinfo is None:
                raise ValidationError("published_at must be timezone-aware")

        # Validate announcement timestamp (optional, timezone-aware if present)
        if self.announced_at is not None:
            if not isinstance(self.announced_at, datetime):
                raise ValidationError("announced_at must be a valid datetime instance")
            if self.announced_at.tzinfo is None:
                raise ValidationError("announced_at must be timezone-aware")

        # Validate effective timestamp (optional, timezone-aware if present)
        if self.effective_at is not None:
            if not isinstance(self.effective_at, datetime):
                raise ValidationError("effective_at must be a valid datetime instance")
            if self.effective_at.tzinfo is None:
                raise ValidationError("effective_at must be timezone-aware")

        # At least one temporal anchor must be present
        if self.published_at is None and self.announced_at is None and self.effective_at is None:
            raise ValidationError(
                "Event must have at least one temporal anchor: published_at, announced_at, or effective_at"
            )

        # Validate URL format if present
        if self.url is not None:
            url_str = self.url.strip()
            if not url_str:
                object.__setattr__(self, "url", None)
            else:
                parsed = urlparse(url_str)
                if not (parsed.scheme in ("http", "https") and parsed.netloc):
                    raise ValidationError(f"Invalid URL format: '{self.url}'")
                object.__setattr__(self, "url", url_str)

        # Normalize affected_sectors tuple
        if not isinstance(self.affected_sectors, tuple):
            if isinstance(self.affected_sectors, (list, set)):
                object.__setattr__(
                    self,
                    "affected_sectors",
                    tuple(s.strip().upper() for s in self.affected_sectors if s and s.strip()),
                )
            else:
                raise ValidationError("affected_sectors must be a sequence of strings")
        else:
            object.__setattr__(
                self,
                "affected_sectors",
                tuple(s.strip().upper() for s in self.affected_sectors if s and s.strip()),
            )

        # Normalize affected_symbols tuple
        def _norm_sym(s: str) -> str:
            clean = s.strip().upper()
            if clean.endswith(".NS") or clean.endswith(".BO"):
                return clean.rsplit(".", 1)[0]
            return clean

        if not isinstance(self.affected_symbols, tuple):
            if isinstance(self.affected_symbols, (list, set)):
                object.__setattr__(
                    self,
                    "affected_symbols",
                    tuple(_norm_sym(s) for s in self.affected_symbols if s and s.strip()),
                )
            else:
                raise ValidationError("affected_symbols must be a sequence of ticker strings")
        else:
            object.__setattr__(
                self,
                "affected_symbols",
                tuple(_norm_sym(s) for s in self.affected_symbols if s and s.strip()),
            )

        # Validate structured_value type if present
        if self.structured_value is not None:
            if not isinstance(self.structured_value, StructuredEventValue):
                raise ValidationError("structured_value must be a StructuredEventValue instance")

        # Generate deterministic event_id if not supplied
        if not self.event_id or not self.event_id.strip():
            # Use most specific anchor date available
            anchor_dt = self.published_at or self.announced_at or self.effective_at
            anchor_str = anchor_dt.isoformat() if anchor_dt else ""
            hash_input = (
                f"{self.category.value}|{self.event_type}|{self.source_org.lower()}|"
                f"{self.title.lower()}|{anchor_str}"
            )
            computed_id = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()[:16]
            object.__setattr__(self, "event_id", computed_id)
        else:
            object.__setattr__(self, "event_id", self.event_id.strip())

    @property
    def primary_timestamp(self) -> datetime:
        """Return the primary information availability timestamp for point-in-time checks.

        Precedence:
        1. published_at: When the notification became publicly readable.
        2. announced_at: When the official oral or broadcast announcement was made.
        3. effective_at: When the regulation took effect.
        """
        if self.published_at is not None:
            return self.published_at
        if self.announced_at is not None:
            return self.announced_at
        if self.effective_at is not None:
            return self.effective_at
        return self.ingested_at

    def to_dict(self) -> Dict[str, Any]:
        """Serialize event to flat dictionary for storage, logging, and downstream processing."""
        return {
            "event_id": self.event_id,
            "title": self.title,
            "category": self.category.value,
            "event_type": self.event_type,
            "source_org": self.source_org,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "announced_at": self.announced_at.isoformat() if self.announced_at else None,
            "effective_at": self.effective_at.isoformat() if self.effective_at else None,
            "ingested_at": self.ingested_at.isoformat(),
            "url": self.url,
            "affected_sectors": list(self.affected_sectors),
            "affected_symbols": list(self.affected_symbols),
            "structured_value": self.structured_value.to_dict() if self.structured_value else None,
            "summary": self.summary,
            "provider": self.provider,
            "is_verified": self.is_verified,
            "raw_metadata": dict(self.raw_metadata),
        }


@dataclass(frozen=True)
class ExternalMarketObservation:
    """Canonical representation of an external market time-series measurement.

    Captures continuous macro variables (e.g. Brent crude oil, USD/INR, S&P 500)
    as explicit time-series observations, cleanly distinguished from discrete
    regulatory/policy announcements.
    """

    series_id: str
    timestamp: datetime
    ingested_at: datetime
    close: float
    unit: str
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    daily_return: Optional[float] = None
    source: str = "yfinance"
    observation_id: str = ""

    def __post_init__(self) -> None:
        if not self.series_id or not self.series_id.strip():
            raise ValidationError("series_id cannot be empty")
        object.__setattr__(self, "series_id", self.series_id.strip().upper())

        if not isinstance(self.timestamp, datetime):
            raise ValidationError("timestamp must be a valid datetime instance")
        if self.timestamp.tzinfo is None:
            raise ValidationError("timestamp must be timezone-aware")

        if not isinstance(self.ingested_at, datetime):
            raise ValidationError("ingested_at must be a valid datetime instance")
        if self.ingested_at.tzinfo is None:
            raise ValidationError("ingested_at must be timezone-aware")

        if not isinstance(self.close, (int, float)) or isinstance(self.close, bool):
            raise ValidationError("close must be a numeric float or int")
        if not math.isfinite(self.close) or self.close <= 0.0:
            raise ValidationError("close must be a positive finite number")
        object.__setattr__(self, "close", float(self.close))

        if not self.unit or not self.unit.strip():
            raise ValidationError("unit cannot be empty")
        object.__setattr__(self, "unit", self.unit.strip())

        # Optional prices validation
        for attr in ("open", "high", "low"):
            val = getattr(self, attr)
            if val is not None:
                if not isinstance(val, (int, float)) or isinstance(val, bool) or not math.isfinite(val) or val <= 0.0:
                    raise ValidationError(f"{attr} must be a positive finite number")
                object.__setattr__(self, attr, float(val))

        if self.daily_return is not None:
            if not isinstance(self.daily_return, (int, float)) or isinstance(self.daily_return, bool) or not math.isfinite(self.daily_return):
                raise ValidationError("daily_return must be a finite float")
            object.__setattr__(self, "daily_return", float(self.daily_return))

        # Generate deterministic observation_id if not given
        if not self.observation_id or not self.observation_id.strip():
            hash_input = f"{self.series_id}|{self.timestamp.isoformat()}|{self.source.lower()}"
            computed_id = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()[:16]
            object.__setattr__(self, "observation_id", computed_id)
        else:
            object.__setattr__(self, "observation_id", self.observation_id.strip())

    def to_event(self) -> MacroEvent:
        """Convert time-series observation into canonical MacroEvent for unified event pipelines."""
        return MacroEvent(
            title=f"{self.series_id} Settle Price: {self.close:.2f} {self.unit}",
            category=EventCategory.EXTERNAL_MARKET,
            event_type=f"{self.series_id.lower()}_observation",
            source_org=self.source,
            published_at=self.timestamp,
            ingested_at=self.ingested_at,
            structured_value=StructuredEventValue(
                metric_name=self.series_id.lower(),
                value=self.close,
                unit=self.unit,
                change=self.daily_return,
                reference_period=self.timestamp.strftime("%Y-%m-%d"),
            ),
            summary=f"Daily settlement for {self.series_id} at {self.close} {self.unit} on {self.timestamp.strftime('%Y-%m-%d')}.",
            provider="external_market_provider",
            event_id=self.observation_id,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize observation to flat dictionary."""
        return {
            "observation_id": self.observation_id,
            "series_id": self.series_id,
            "timestamp": self.timestamp.isoformat(),
            "ingested_at": self.ingested_at.isoformat(),
            "close": self.close,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "daily_return": self.daily_return,
            "unit": self.unit,
            "source": self.source,
        }
