"""Canonical Instrument Registry and Identity Management for Equities and Indices.

Enforces clear separation between individual equities (e.g. BHARTIARTL) and
sectoral / broad-market benchmark indices (e.g. NIFTY_TELECOMMUNICATIONS, NIFTY_50).
Prevents accidental symbol substitution, price mixing, or model weight cross-application.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set


class InstrumentType(str, Enum):
    """Classification of financial instrument."""

    EQUITY = "EQUITY"
    INDEX = "INDEX"


@dataclass(frozen=True)
class Instrument:
    """Canonical instrument definition capturing identity, type, exchange, and benchmark context."""

    symbol: str  # Canonical uppercase symbol, e.g. 'BHARTIARTL' or 'NIFTY_TELECOMMUNICATIONS'
    name: str  # Official human-readable name, e.g. 'Nifty Telecommunications'
    instrument_type: InstrumentType
    exchange: str = "NSE"
    sector: Optional[str] = None
    sector_benchmark: Optional[str] = None
    official_source: str = "yfinance"  # 'yfinance' for equities, 'nifty_indices' for official NSE indices
    is_tradable: bool = True  # Indices are non-tradable benchmarks
    yahoo_ticker: Optional[str] = None  # None if unavailable on Yahoo Finance
    currency: str = "INR"
    lot_size: Optional[int] = None

    @property
    def canonical_symbol(self) -> str:
        """Alias for canonical uppercase symbol."""
        return self.symbol

    @property
    def official_name(self) -> str:
        """Alias for official instrument name."""
        return self.name


# Official Nifty Indices names and aliases
NIFTY_TELECOM_CANONICAL = "NIFTY_TELECOMMUNICATIONS"
BHARTIARTL_CANONICAL = "BHARTIARTL"
TCS_CANONICAL = "TCS"
RELIANCE_CANONICAL = "RELIANCE"
NIFTY_50_CANONICAL = "NIFTY_50"

# Canonical Instrument Registry
INSTRUMENT_REGISTRY: Dict[str, Instrument] = {
    BHARTIARTL_CANONICAL: Instrument(
        symbol=BHARTIARTL_CANONICAL,
        name="Bharti Airtel Limited",
        instrument_type=InstrumentType.EQUITY,
        exchange="NSE",
        sector="TELECOMMUNICATIONS",
        sector_benchmark=NIFTY_TELECOM_CANONICAL,
        official_source="yfinance",
        is_tradable=True,
        yahoo_ticker="BHARTIARTL.NS",
        lot_size=950,
    ),
    TCS_CANONICAL: Instrument(
        symbol=TCS_CANONICAL,
        name="Tata Consultancy Services Limited",
        instrument_type=InstrumentType.EQUITY,
        exchange="NSE",
        sector="IT",
        sector_benchmark="NIFTY_IT",
        official_source="yfinance",
        is_tradable=True,
        yahoo_ticker="TCS.NS",
        lot_size=175,
    ),
    RELIANCE_CANONICAL: Instrument(
        symbol=RELIANCE_CANONICAL,
        name="Reliance Industries Limited",
        instrument_type=InstrumentType.EQUITY,
        exchange="NSE",
        sector="ENERGY",
        sector_benchmark="NIFTY_ENERGY",
        official_source="yfinance",
        is_tradable=True,
        yahoo_ticker="RELIANCE.NS",
        lot_size=250,
    ),
    NIFTY_TELECOM_CANONICAL: Instrument(
        symbol=NIFTY_TELECOM_CANONICAL,
        name="Nifty Telecommunications",
        instrument_type=InstrumentType.INDEX,
        exchange="NSE",
        sector="TELECOMMUNICATIONS",
        sector_benchmark=None,
        official_source="nifty_indices",
        is_tradable=False,
        yahoo_ticker=None,  # Not published / supported on Yahoo Finance
        lot_size=None,
    ),
    NIFTY_50_CANONICAL: Instrument(
        symbol=NIFTY_50_CANONICAL,
        name="NIFTY 50",
        instrument_type=InstrumentType.INDEX,
        exchange="NSE",
        sector="BROAD",
        sector_benchmark=None,
        official_source="nifty_indices",
        is_tradable=False,
        yahoo_ticker="^NSEI",
        lot_size=None,
    ),
}

# Alias resolution map to canonical symbols
INSTRUMENT_ALIAS_MAP: Dict[str, str] = {
    # BHARTIARTL aliases
    "BHARTIARTL": BHARTIARTL_CANONICAL,
    "BHARTIARTL.NS": BHARTIARTL_CANONICAL,
    "BHARTIARTL.BO": BHARTIARTL_CANONICAL,
    "AIRTEL": BHARTIARTL_CANONICAL,
    # TCS aliases
    "TCS": TCS_CANONICAL,
    "TCS.NS": TCS_CANONICAL,
    "TCS.BO": TCS_CANONICAL,
    # RELIANCE aliases
    "RELIANCE": RELIANCE_CANONICAL,
    "RELIANCE.NS": RELIANCE_CANONICAL,
    "RELIANCE.BO": RELIANCE_CANONICAL,
    # Nifty Telecommunications aliases
    "NIFTY_TELECOMMUNICATIONS": NIFTY_TELECOM_CANONICAL,
    "NIFTY TELECOMMUNICATIONS": NIFTY_TELECOM_CANONICAL,
    "NIFTY_TELECOM": NIFTY_TELECOM_CANONICAL,
    "NIFTY TELECOM": NIFTY_TELECOM_CANONICAL,
    "NIFTYTELECOM": NIFTY_TELECOM_CANONICAL,
    "NIFTY-TELECOM": NIFTY_TELECOM_CANONICAL,
    "NIFTY MS IT TELCM": NIFTY_TELECOM_CANONICAL,
    "TELECOM": NIFTY_TELECOM_CANONICAL,
    "TELECOMMUNICATIONS": NIFTY_TELECOM_CANONICAL,
    # Nifty 50 aliases
    "NIFTY_50": NIFTY_50_CANONICAL,
    "NIFTY 50": NIFTY_50_CANONICAL,
    "NIFTY50": NIFTY_50_CANONICAL,
    "NIFTY": NIFTY_50_CANONICAL,
    "^NSEI": NIFTY_50_CANONICAL,
}


def resolve_canonical_symbol(symbol_or_alias: str) -> str:
    """Resolve an incoming symbol or alias to its canonical uppercase representation."""
    clean = symbol_or_alias.strip().upper()
    return INSTRUMENT_ALIAS_MAP.get(clean, clean)


def get_instrument(symbol_or_alias: str) -> Optional[Instrument]:
    """Retrieve Instrument definition by symbol or recognized alias."""
    canonical = resolve_canonical_symbol(symbol_or_alias)
    return INSTRUMENT_REGISTRY.get(canonical)


def is_index(symbol_or_alias: str) -> bool:
    """Return True if symbol resolves to a benchmark or sectoral index."""
    inst = get_instrument(symbol_or_alias)
    if inst:
        return inst.instrument_type == InstrumentType.INDEX
    clean = symbol_or_alias.strip().upper()
    return clean.startswith("^") or "NIFTY" in clean or "INDEX" in clean or "SENSEX" in clean


def is_equity(symbol_or_alias: str) -> bool:
    """Return True if symbol resolves to a single-stock equity."""
    inst = get_instrument(symbol_or_alias)
    if inst:
        return inst.instrument_type == InstrumentType.EQUITY
    return not is_index(symbol_or_alias)


def validate_instrument_separation(equity_symbol: str, index_symbol: str) -> None:
    """Enforce strict separation between equities and indices.

    Validates that:
    1. Both symbols are non-empty and distinct.
    2. The first symbol resolves to an equity instrument.
    3. The second symbol resolves to an index instrument.
    4. An equity cannot be substituted for an index or vice versa.

    Raises:
        ValueError: If symbols are identical, conflated, or fail equity/index classification.
    """
    canon_equity = resolve_canonical_symbol(equity_symbol)
    canon_index = resolve_canonical_symbol(index_symbol)

    if canon_equity == canon_index:
        raise ValueError(
            f"Instrument conflation error: equity '{equity_symbol}' and index '{index_symbol}' must be distinct."
        )

    if not is_equity(canon_equity):
        raise ValueError(
            f"Expected equity symbol for first argument, got index '{equity_symbol}' (resolved: '{canon_equity}')."
        )

    if not is_index(canon_index):
        raise ValueError(
            f"Expected index symbol for second argument, got equity '{index_symbol}' (resolved: '{canon_index}')."
        )
