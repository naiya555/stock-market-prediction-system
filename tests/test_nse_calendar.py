from datetime import date

import pytest

from app.market.quality.nse_calendar import classify_nse_date, load_calendar_evidence


def test_cached_special_session_and_unresolved_date():
    evidence = load_calendar_evidence(
        "research/forecasting_readiness/calendar_classifications.csv"
    )
    assert classify_nse_date(date(2026, 11, 8), evidence).classification == "SPECIAL_SESSION"
    assert classify_nse_date(date(2026, 2, 1), evidence).verification_status == "UNVERIFIED"
    assert classify_nse_date(date(2030, 1, 1), evidence).classification == "UNVERIFIED"


def test_verified_evidence_requires_a_source(tmp_path):
    path = tmp_path / "calendar.csv"
    path.write_text(
        "date,exchange,classification,verification_status,source_url,"
        "circular_or_calendar_reference,evidence_description,retrieval_date,source_type\n"
        "2026-01-01,NSE,SPECIAL_SESSION,VERIFIED,,,,official_nse\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="lacks official source"):
        load_calendar_evidence(path)
