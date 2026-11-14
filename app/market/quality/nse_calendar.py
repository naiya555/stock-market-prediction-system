"""Cached, official-evidence-backed NSE date classifications."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass(frozen=True)
class NSECalendarEvidence:
    date: date
    exchange: str
    classification: str
    verification_status: str
    source_url: str | None
    reference: str | None
    evidence_description: str
    retrieval_date: str | None
    source_type: str


def load_calendar_evidence(path: str | Path) -> dict[date, NSECalendarEvidence]:
    """Load cached classifications; reject malformed or non-NSE evidence."""
    result: dict[date, NSECalendarEvidence] = {}
    with Path(path).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row.get("exchange") != "NSE":
                raise ValueError("calendar evidence must use exchange NSE")
            day = date.fromisoformat(row["date"])
            classification = row["classification"]
            if classification not in {
                "REGULAR_SESSION", "SPECIAL_SESSION", "HOLIDAY",
                "NON_TRADING_DAY", "UNVERIFIED",
            }:
                raise ValueError(f"unsupported calendar classification: {classification}")
            status = row["verification_status"]
            if status == "VERIFIED" and not row.get("source_url"):
                raise ValueError(f"verified date lacks official source: {day}")
            result[day] = NSECalendarEvidence(
                day, "NSE", classification, status, row.get("source_url") or None,
                row.get("circular_or_calendar_reference") or None,
                row.get("evidence_description", ""),
                row.get("retrieval_date") or None,
                row.get("source_type", "official_nse" if row.get("source_url") else "unverified"),
            )
    return result


def classify_nse_date(day: date, evidence: dict[date, NSECalendarEvidence]) -> NSECalendarEvidence:
    """Return cached evidence or an explicit UNVERIFIED result; never infer from weekday."""
    return evidence.get(
        day,
        NSECalendarEvidence(
            day, "NSE", "UNVERIFIED", "UNVERIFIED", None, None,
            "No cached official NSE evidence establishes this date.",
            None, "unverified",
        ),
    )
