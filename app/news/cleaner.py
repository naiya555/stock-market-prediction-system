"""Financial News Cleaning, Deduplication, and Point-in-Time Filtering.

Provides deterministic deduplication of syndicated news across multiple media outlets
and strict point-in-time session filtering to prevent temporal look-ahead leakage.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
import re
from typing import Any, Dict, List, Optional, Sequence, Set

from app.core.logging_config import get_logger
from app.news.schemas import NewsArticle

logger = get_logger(__name__)


@dataclass(frozen=True)
class NewsDeduplicationSummary:
    """Audit summary metrics for a news deduplication execution."""

    total_input: int
    unique_count: int
    duplicates_removed: int
    removed_ids: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert summary to dictionary representation."""
        return asdict(self)


@dataclass(frozen=True)
class NewsCleaningResult:
    """Container holding deduplicated NewsArticle records and audit summary."""

    articles: List[NewsArticle]
    summary: NewsDeduplicationSummary

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary representation."""
        return {
            "articles": [a.to_dict() for a in self.articles],
            "summary": self.summary.to_dict(),
        }


def _normalize_headline_text(text: str) -> str:
    """Normalize headline string for fuzzy duplicate detection.

    Converts to lowercase, removes punctuation, and collapses consecutive whitespace.
    """
    clean = text.lower()
    clean = re.sub(r"[^\w\s]", " ", clean)
    return " ".join(clean.split())


def deduplicate_news(
    articles: Sequence[NewsArticle],
    dedup_window_hours: int = 48,
) -> NewsCleaningResult:
    """Deduplicate news articles across identical IDs, URLs, and syndicated headlines.

    Deduplication Rules:
    1. Exact Article ID: If two articles produce identical deterministic hashes, duplicate is discarded.
    2. Exact URL: If two articles have identical non-empty URLs, duplicate is discarded.
    3. Syndicated Headline Match: If two articles share the exact normalized headline text
       within `dedup_window_hours`, the later publication is considered a syndicate duplicate.
    4. Ordering: Preserves descending chronological order (most recent first).

    Args:
        articles: Input sequence of NewsArticle records.
        dedup_window_hours: Maximum hours between matching headlines to consider them duplicates (default 48h).

    Returns:
        NewsCleaningResult containing deduplicated articles and comprehensive audit summary.
    """
    if not articles:
        summary = NewsDeduplicationSummary(
            total_input=0,
            unique_count=0,
            duplicates_removed=0,
            removed_ids=[],
        )
        return NewsCleaningResult(articles=[], summary=summary)

    # Sort input by published_at ascending so earliest publication is treated as canonical origin
    sorted_inputs = sorted(articles, key=lambda a: a.published_at)

    seen_ids: Set[str] = set()
    seen_urls: Set[str] = set()
    # Map of normalized_headline -> list of (published_at, article_id)
    seen_headlines: Dict[str, List[datetime]] = {}

    unique_articles: List[NewsArticle] = []
    removed_ids: List[str] = []

    for art in sorted_inputs:
        is_duplicate = False

        # Rule 1: Exact ID
        if art.article_id in seen_ids:
            is_duplicate = True
            removed_ids.append(art.article_id)

        # Rule 2: Exact URL
        elif art.url and art.url in seen_urls:
            is_duplicate = True
            removed_ids.append(art.article_id)

        # Rule 3: Syndicated / Normalized headline within window
        else:
            norm_title = _normalize_headline_text(art.headline)
            if norm_title in seen_headlines:
                prior_dates = seen_headlines[norm_title]
                for p_date in prior_dates:
                    diff = abs((art.published_at - p_date).total_seconds())
                    if diff <= dedup_window_hours * 3600:
                        is_duplicate = True
                        removed_ids.append(art.article_id)
                        break

        if not is_duplicate:
            unique_articles.append(art)
            seen_ids.add(art.article_id)
            if art.url:
                seen_urls.add(art.url)
            norm_title = _normalize_headline_text(art.headline)
            if norm_title not in seen_headlines:
                seen_headlines[norm_title] = []
            seen_headlines[norm_title].append(art.published_at)

    # Sort output descending by published_at (most recent first)
    unique_articles.sort(key=lambda a: a.published_at, reverse=True)

    summary = NewsDeduplicationSummary(
        total_input=len(articles),
        unique_count=len(unique_articles),
        duplicates_removed=len(removed_ids),
        removed_ids=removed_ids,
    )

    logger.info(
        "News deduplication complete: %d input -> %d unique (%d duplicates removed)",
        summary.total_input,
        summary.unique_count,
        summary.duplicates_removed,
    )

    return NewsCleaningResult(articles=unique_articles, summary=summary)


def filter_news_point_in_time(
    articles: Sequence[NewsArticle],
    as_of_time: datetime,
    lookback_window: Optional[timedelta] = None,
) -> List[NewsArticle]:
    """Strictly filter news articles to prevent look-ahead bias before a given decision cutoff.

    Invariants:
    1. Temporal Isolation: Only articles with `published_at <= as_of_time` and
       `ingested_at <= as_of_time` are eligible. Any article published or ingested
       after `as_of_time` is strictly excluded.
    2. Optional Lookback Window: If `lookback_window` is specified, only articles
       with `published_at >= as_of_time - lookback_window` are retained.

    Args:
        articles: Sequence of NewsArticle records.
        as_of_time: Market cutoff timestamp (e.g. trading session close or decision time).
        lookback_window: Optional duration to look back prior to as_of_time (e.g. timedelta(days=2)).

    Returns:
        List of eligible point-in-time NewsArticle records sorted descending by publication time.
    """
    eligible: List[NewsArticle] = []
    min_time = (as_of_time - lookback_window) if lookback_window is not None else None

    for art in articles:
        # Zero look-ahead: article must have been published and ingested on or before cutoff
        if art.published_at > as_of_time:
            continue
        if art.ingested_at > as_of_time:
            continue
        if min_time is not None and art.published_at < min_time:
            continue

        eligible.append(art)

    eligible.sort(key=lambda a: a.published_at, reverse=True)
    return eligible
