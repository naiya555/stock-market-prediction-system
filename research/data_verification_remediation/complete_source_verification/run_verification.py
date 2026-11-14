"""Write the consolidated market-data verification evidence package."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research/data_verification_remediation/complete_source_verification"
RETRIEVED = "2026-11-14"


def write_csv(name: str, rows: list[dict]) -> None:
    path = OUT / name
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


BHARTI = [
    {"instrument": "BHARTIARTL", "event_date": "", "announcement_date": "", "record_date": "2025-07-18", "event_type": "final dividend record date", "amount": "Rs.16 fully paid / Rs.4 partly paid", "adjustment_factor": "", "source_name": "NSE corporate filing archive", "source_url": "https://nsearchives.nseindia.com/corporate/BHARTIARTL_16062025105119_Record_Date_Intimation_BAL.pdf", "source_type": "official exchange filing", "verification_status": "VERIFIED_FOR_THIS_EVENT", "limitation": "This filing does not establish the complete 2016-2026 action history or an adjustment factor."},
    {"instrument": "BHARTIARTL", "event_date": "", "announcement_date": "2026-05-13", "record_date": "2026-07-24", "event_type": "final dividend record date", "amount": "Rs.24 fully paid / Rs.6 partly paid", "adjustment_factor": "", "source_name": "NSE corporate filing archive", "source_url": "https://nsearchives.nseindia.com/corporate/BHARTIARTL_10072026100101_BAL-_Record_Date_Intimation.pdf", "source_type": "official exchange filing", "verification_status": "VERIFIED_FOR_THIS_EVENT", "limitation": "Complete historical splits, bonuses, rights, demergers and dividend ex-dates remain unverified."},
    {"instrument": "BHARTIARTL", "event_date": "", "announcement_date": "", "record_date": "", "event_type": "historical coverage", "amount": "", "adjustment_factor": "", "source_name": "NSE/BSE/company records", "source_url": "https://www.nseindia.com/get-quotes/equity?symbol=BHARTIARTL", "source_type": "official exchange/company sources", "verification_status": "UNVERIFIED", "limitation": "A complete accessible ledger covering 2016-11-16 through 2026-11-14 was not obtained; no missing event was inferred."},
]

TCS = [
    {"instrument": "TCS", "event_date": "", "announcement_date": "2024-05-06", "record_date": "2024-05-16", "event_type": "final dividend record date", "amount": "Rs.28 per equity share", "adjustment_factor": "", "source_name": "NSE corporate filing archive", "source_url": "https://nsearchives.nseindia.com/corporate/TCS_06052024182259_SEInt06052024signed.pdf", "source_type": "official exchange filing", "verification_status": "VERIFIED_FOR_THIS_EVENT", "limitation": "This filing does not establish the complete 2016-2026 action history or an adjustment factor."},
    {"instrument": "TCS", "event_date": "", "announcement_date": "2025-04-30", "record_date": "2025-06-04", "event_type": "final dividend record date", "amount": "Rs.30 per equity share", "adjustment_factor": "", "source_name": "NSE corporate filing archive", "source_url": "https://nsearchives.nseindia.com/corporate/TCS_CORPCS_30042025212952_Record_Date_Intimation_signed.pdf", "source_type": "official exchange filing", "verification_status": "VERIFIED_FOR_THIS_EVENT", "limitation": "Complete historical splits, bonuses, rights, demergers and dividend ex-dates remain unverified."},
    {"instrument": "TCS", "event_date": "", "announcement_date": "2026-05-05", "record_date": "2026-05-25", "event_type": "final dividend record date", "amount": "Rs.31 per equity share", "adjustment_factor": "", "source_name": "NSE corporate filing archive", "source_url": "https://nsearchives.nseindia.com/corporate/TCS_CORPCS_05052026173649_SEInt05052026.pdf", "source_type": "official exchange filing", "verification_status": "VERIFIED_FOR_THIS_EVENT", "limitation": "Complete historical action history and adjustment factors remain unverified."},
    {"instrument": "TCS", "event_date": "", "announcement_date": "", "record_date": "", "event_type": "historical coverage", "amount": "", "adjustment_factor": "", "source_name": "NSE/BSE/company records", "source_url": "https://www.nseindia.com/companies-listing/corporate-filings-actions?symbol=TCS", "source_type": "official exchange/company sources", "verification_status": "UNVERIFIED", "limitation": "A complete accessible ledger covering 2016-11-16 through 2026-11-14 was not obtained; no missing event was inferred."},
]

SESSION_EVIDENCE = {
    "2019-10-27": ("SPECIAL_SESSION_VERIFIED", "https://nsearchives.nseindia.com/content/circulars/CMTR42483.pdf", "Diwali Muhurat capital-market session."),
    "2020-02-01": ("SPECIAL_SESSION_VERIFIED", "https://nsearchives.nseindia.com/content/circulars/FAOP43291.pdf", "Live trading session for Union Budget."),
    "2020-11-14": ("SPECIAL_SESSION_VERIFIED", "https://nsearchives.nseindia.com/content/circulars/CMTR46230.pdf", "Diwali Muhurat capital-market session."),
    "2023-11-12": ("SPECIAL_SESSION_VERIFIED", "https://nsearchives.nseindia.com/content/circulars/CMTR59124.pdf", "Diwali Muhurat capital-market session."),
    "2024-01-20": ("SPECIAL_SESSION_VERIFIED", "https://nsearchives.nseindia.com/content/circulars/MSD59999.pdf", "Special live session with DR-site switch."),
    "2024-03-02": ("SPECIAL_SESSION_VERIFIED", "https://nsearchives.nseindia.com/content/circulars/MSD60677.pdf?0", "Special live session with DR-site switch."),
    "2024-05-18": ("SPECIAL_SESSION_VERIFIED", "https://nsearchives.nseindia.com/content/circulars/MSD62061.pdf", "Special live trading session."),
}


def session_rows() -> list[dict]:
    old = [
        ("2016-11-16", "Wednesday", "NSE Indices", "Yahoo Finance", "UNVERIFIED", "Project range-start/source coverage discrepancy; official session evidence not retrieved."),
        ("2018-01-01", "Monday", "NSE Indices", "Yahoo Finance", "UNVERIFIED", "Weekday gap; official calendar evidence not retrieved."),
        ("2019-01-01", "Tuesday", "NSE Indices", "Yahoo Finance", "UNVERIFIED", "Weekday gap; official calendar evidence not retrieved."),
        ("2019-02-13", "Wednesday", "NSE Indices", "Yahoo Finance", "UNVERIFIED", "Weekday gap; official calendar evidence not retrieved."),
        ("2019-03-29", "Friday", "NSE Indices", "Yahoo Finance", "UNVERIFIED", "Weekday gap; official calendar evidence not retrieved."),
        ("2019-10-27", "Sunday", "NSE Indices", "Yahoo Finance", "SPECIAL_SESSION_VERIFIED", ""),
        ("2020-02-01", "Saturday", "NSE Indices", "Yahoo Finance", "SPECIAL_SESSION_VERIFIED", ""),
        ("2020-11-14", "Saturday", "NSE Indices", "Yahoo Finance", "SPECIAL_SESSION_VERIFIED", ""),
        ("2023-11-12", "Sunday", "NSE Indices", "Yahoo Finance", "SPECIAL_SESSION_VERIFIED", ""),
        ("2024-01-20", "Saturday", "NSE Indices", "Yahoo Finance", "SPECIAL_SESSION_VERIFIED", ""),
        ("2024-03-02", "Saturday", "NSE Indices", "Yahoo Finance", "SPECIAL_SESSION_VERIFIED", ""),
        ("2024-05-18", "Saturday", "NSE Indices", "Yahoo Finance", "SPECIAL_SESSION_VERIFIED", ""),
        ("2026-02-01", "Sunday", "NSE Indices", "Yahoo Finance", "UNVERIFIED", "No official historical calendar/special-session evidence retrieved."),
        ("2026-11-08", "Sunday", "NSE Indices", "Yahoo Finance", "UNVERIFIED", "No official historical calendar/special-session evidence retrieved."),
    ]
    rows = []
    for date, weekday, primary, secondary, status, limitation in old:
        evidence = SESSION_EVIDENCE.get(date)
        rows.append({
            "date": date, "weekday": weekday, "missing_from": "Yahoo Finance" if date != "2016-11-16" else "NSE Indices",
            "other_source": secondary if date != "2016-11-16" else primary, "classification": status,
            "primary_status": "PRESENT" if date != "2016-11-16" else "MISSING",
            "secondary_status": "MISSING" if date != "2016-11-16" else "PRESENT",
            "source_name": "NSE trading circular" if evidence else "Not obtained",
            "source_url": evidence[1] if evidence else "",
            "retrieval_date": RETRIEVED,
            "evidence": evidence[2] if evidence else limitation,
            "verification_status": "VERIFIED" if evidence else "UNVERIFIED",
        })
    return rows


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    write_csv("corporate_actions_bhartiartl.csv", BHARTI)
    write_csv("corporate_actions_tcs.csv", TCS)
    write_csv("nifty50_session_verification.csv", session_rows())
    write_csv("nifty_telecommunications_reconciliation.csv", [{
        "date": "", "project_source": "NSE Indices official Nifty Telecommunications endpoint",
        "independent_source": "", "project_close": "", "independent_close": "",
        "absolute_difference": "", "percentage_difference": "", "status": "UNVERIFIED",
        "coverage": "No independent equivalent historical series obtained",
        "source_url": "https://www.niftyindices.com/reports/historical-data",
        "limitation": "Search results identified only the same official endpoint or different indices; no comparable independent rows were used.",
    }])
    (OUT / "reconciliation_summary.json").write_text(json.dumps({
        "tolerance": {"absolute": 0.01, "relative": 0.0001},
        "BHARTIARTL": {"comparable": 0, "matched": 0, "mismatched": 0, "missing": "independent series unavailable", "coverage_percent": None, "status": "UNVERIFIED"},
        "TCS": {"comparable": 0, "matched": 0, "mismatched": 0, "missing": "independent series unavailable", "coverage_percent": None, "status": "UNVERIFIED"},
        "NIFTY_50": {"comparable": 2465, "matched": 2465, "mismatched": 0, "missing": 14, "coverage_percent": 100.0, "status": "PARTIALLY_VERIFIED", "note": "100% is among comparable rows; 14 unmatched dates remain separately classified."},
        "NIFTY_TELECOMMUNICATIONS": {"comparable": 0, "matched": 0, "mismatched": 0, "missing": "independent equivalent series unavailable", "coverage_percent": None, "status": "UNVERIFIED"},
    }, indent=2), encoding="utf-8")
    (OUT / "source_evidence_manifest.json").write_text(json.dumps({
        "retrieval_date": RETRIEVED,
        "sources": [
            {"name": "NSE corporate filing archive", "type": "official exchange filing", "urls": [r["source_url"] for r in BHARTI + TCS if r["source_url"].startswith("https://nsearchives")]},
            {"name": "NSE trading circular archive", "type": "official exchange circular", "urls": [v[1] for v in SESSION_EVIDENCE.values()]},
            {"name": "NSE Indices historical data", "type": "official index provider", "url": "https://www.niftyindices.com/reports/historical-data", "role": "project primary; no independent equivalent found"},
            {"name": "Yahoo Finance via project adapter", "type": "secondary provider", "role": "NIFTY_50 cross-check; auto_adjust=False"},
            {"name": "NSE equity/BSE/company historical action records", "type": "official sources", "status": "UNVERIFIED", "limitation": "Complete accessible event ledgers were not obtained."},
        ],
        "security": "External content was treated as untrusted evidence; no embedded instructions were executed.",
    }, indent=2), encoding="utf-8")
    (OUT / "instrument_readiness.json").write_text(json.dumps({
        "BHARTIARTL": {"status": "PARTIALLY_VERIFIED", "reason": "Two official dividend record-date filings verified; complete corporate-action history and independent price series unavailable."},
        "TCS": {"status": "PARTIALLY_VERIFIED", "reason": "Three official dividend record-date filings verified; complete corporate-action history and independent price series unavailable."},
        "NIFTY_50": {"status": "PARTIALLY_VERIFIED", "reason": "2465 comparable rows matched; seven unmatched dates are verified special sessions and seven dates remain unverified."},
        "NIFTY_TELECOMMUNICATIONS": {"status": "UNVERIFIED", "reason": "No independent equivalent historical series was obtained."},
    }, indent=2), encoding="utf-8")
    write_csv("proposed_data_corrections.csv", [
        {"instrument": "NIFTY_50", "date": "2016-11-16", "proposed_action": "No correction", "reason": "Likely range-start/source coverage issue, but official session evidence unavailable.", "before": "", "after": "", "status": "UNVERIFIED"},
        {"instrument": "NIFTY_50", "date": "2019-10-27;2020-02-01;2020-11-14;2023-11-12;2024-01-20;2024-03-02;2024-05-18", "proposed_action": "No correction", "reason": "Official NSE circulars verify special sessions; retain source-specific presence/absence rather than fabricate values.", "before": "", "after": "", "status": "DOCUMENT_ONLY"},
    ])
    (OUT / "verification_metadata.json").write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "historical_range": {"start": "2016-11-16", "end": "2026-11-14"},
        "packages_installed": False, "models_trained": False, "forecasting_run": False,
        "prior_artifacts_modified": False, "production_modified": False, "database_modified": False,
        "limitations": ["Official complete corporate-action ledgers were not accessible.", "No independent exact NIFTY Telecommunications series was accessible.", "Seven NIFTY_50 dates remain unverified."],
    }, indent=2), encoding="utf-8")
    (OUT / "FINAL_VERIFICATION_REPORT.md").write_text("""# Complete Independent Market-Data Verification

## Overall decision

**NO — the historical datasets are not sufficiently independently verified to resume forecasting experiments.** NIFTY 50 has strong row-level agreement on 2,465 comparable observations, and seven weekend/holiday-date records are independently confirmed as NSE special sessions. However, complete corporate-action histories and independent equity price series remain unavailable, seven NIFTY 50 dates remain unverified, and no independent equivalent NIFTY Telecommunications series was obtained.

## Readiness

| Instrument | Status | Evidence |
|---|---|---|
| BHARTIARTL | PARTIALLY_VERIFIED | Two official dividend record-date filings; complete corporate-action ledger, factors, and independent price series unresolved. |
| TCS | PARTIALLY_VERIFIED | Three official dividend record-date filings; complete corporate-action ledger, factors, and independent price series unresolved. |
| NIFTY 50 | PARTIALLY_VERIFIED | 2,465/2,465 comparable rows matched within tolerance; 7 special sessions verified and 7 dates remain unverified. |
| NIFTY TELECOMMUNICATIONS | UNVERIFIED | No independent equivalent historical series obtained. |

## Corporate actions

Official NSE filings verify the listed BHARTIARTL and TCS dividend record-date events in the CSV artifacts. These filings do not provide a complete 2016–2026 split, bonus, rights, merger, demerger, dividend ex-date, or adjustment-factor ledger. No adjustment factor was inferred. The project's Yahoo adapter requests `auto_adjust=False`; this documents the request for raw/unadjusted data, but without an independent event/price comparison it does not prove continuity for every event.

## NIFTY 50 unmatched dates

Official NSE circulars verify special trading sessions on 2019-10-27, 2020-02-01, 2020-11-14, 2023-11-12, 2024-01-20, 2024-03-02, and 2024-05-18. The remaining dates — 2016-11-16, 2018-01-01, 2019-01-01, 2019-02-13, 2019-03-29, 2026-02-01, and 2026-11-08 — remain UNVERIFIED because the applicable official calendar/session evidence was not obtained. Missing values were not fabricated.

## NIFTY Telecommunications

The official NSE Indices endpoint confirms the index identity and methodology, but it is the project's existing source, not an independent series. Search results for other pages were different indices or non-comparable analytics pages. Consequently, comparable, matched, mismatched, and coverage counts against an independent series are zero/unavailable, not zero discrepancies.

## Corrections and safety

No historical data was changed. Proposed corrections are documentation-only. No forecasting experiment, model training, production/API/frontend change, database change, package installation, staging, commit, or push was performed.

See the accompanying CSV/JSON artifacts for source URLs, retrieval date, evidence, tolerances, limitations, and reconciliation counts.
""", encoding="utf-8")


if __name__ == "__main__":
    main()
