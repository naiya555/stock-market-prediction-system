"""Canonical Financial News Schema Contracts.

Defines standardized, immutable data contracts for financial news items.
Enforces point-in-time integrity, provenance tracking, and isolation between
publication time and system ingestion time.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

from app.core.schemas import ValidationError


@dataclass(frozen=True)
class NewsArticle:
    """Canonical representation of an ingested financial news article."""

    headline: str
    source: str
    published_at: datetime
    ingested_at: datetime
    symbols: Tuple[str, ...]
    url: Optional[str] = None
    summary: Optional[str] = None
    provider: str = "generic"
    article_id: str = ""

    def __post_init__(self) -> None:
        # Validate headline
        if not self.headline or not self.headline.strip():
            raise ValidationError("headline cannot be empty")
        object.__setattr__(self, "headline", self.headline.strip())

        # Validate source publisher
        if not self.source or not self.source.strip():
            raise ValidationError("source cannot be empty")
        object.__setattr__(self, "source", self.source.strip())

        # Validate publication timestamp
        if not isinstance(self.published_at, datetime):
            raise ValidationError("published_at must be a valid datetime instance")
        if self.published_at.tzinfo is None:
            raise ValidationError("published_at must be timezone-aware")

        # Validate ingestion timestamp
        if not isinstance(self.ingested_at, datetime):
            raise ValidationError("ingested_at must be a valid datetime instance")
        if self.ingested_at.tzinfo is None:
            raise ValidationError("ingested_at must be timezone-aware")

        # Normalize symbols tuple
        def _norm_sym(s: str) -> str:
            clean = s.strip().upper()
            if clean.endswith(".NS") or clean.endswith(".BO"):
                return clean.rsplit(".", 1)[0]
            return clean

        if not isinstance(self.symbols, tuple):
            if isinstance(self.symbols, (list, set)):
                object.__setattr__(self, "symbols", tuple(_norm_sym(s) for s in self.symbols if s and s.strip()))
            else:
                raise ValidationError("symbols must be a sequence of ticker strings")
        else:
            object.__setattr__(self, "symbols", tuple(_norm_sym(s) for s in self.symbols if s and s.strip()))

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

        # Validate provider
        if not self.provider or not self.provider.strip():
            raise ValidationError("provider cannot be empty")
        object.__setattr__(self, "provider", self.provider.strip())

        # Generate deterministic article_id if not supplied
        if not self.article_id or not self.article_id.strip():
            hash_input = f"{self.headline.lower()}|{self.source.lower()}|{self.published_at.isoformat()}"
            computed_id = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()[:16]
            object.__setattr__(self, "article_id", computed_id)
        else:
            object.__setattr__(self, "article_id", self.article_id.strip())

    def to_dict(self) -> Dict[str, Any]:
        """Serialize article to flat dictionary for logging, JSON APIs, and downstream NLP."""
        return {
            "article_id": self.article_id,
            "headline": self.headline,
            "source": self.source,
            "published_at": self.published_at.isoformat(),
            "ingested_at": self.ingested_at.isoformat(),
            "symbols": list(self.symbols),
            "url": self.url,
            "summary": self.summary,
            "provider": self.provider,
        }
