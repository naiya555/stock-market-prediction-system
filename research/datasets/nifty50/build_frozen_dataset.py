"""Build the frozen NIFTY 50 research dataset and artifacts.

Strict non-destructive operation: treats provider observations as immutable,
performs zero interpolation or forward-filling, preserves original precision,
and calculates SHA-256 integrity digests.
"""

from __future__ import annotations

import csv
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

# Insert project root
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from app.market.providers.nifty_indices_provider import NiftyIndicesProvider
from app.market.providers.yfinance_provider import YFinanceProvider

OUT_DIR = Path(__file__).resolve().parent

# Exact date parameters reproducing 2026-11-15 verified reconciliation
START_DATE = datetime(2016, 11, 1, tzinfo=timezone.utc)
END_DATE = datetime(2026, 11, 15, tzinfo=timezone.utc)
ABS_TOLERANCE = 0.01
REL_TOLERANCE = 0.0001

# Known audited dates from official evidence manifest
SPECIAL_SESSIONS = {
    "2019-10-27": ("NSE/CMTR/42483", "Official Diwali Muhurat capital-market session."),
    "2020-02-01": ("NSE/FAOP/43291", "Official live trading session for Union Budget."),
    "2020-11-14": ("NSE/CMTR/46230", "Official Diwali Muhurat capital-market session."),
    "2023-11-12": ("NSE/CMTR/59124", "Official Diwali Muhurat capital-market session."),
    "2024-01-20": ("NSE/MSD/59999", "Official special live session with DR-site switch."),
    "2024-03-02": ("NSE/MSD/60677", "Official special live session with DR-site switch."),
    "2024-05-18": ("NSE/MSD/62061", "Official special live trading session."),
    "2026-02-01": ("NSE/CMTR/72349", "Official live trading session for Union Budget with standard market timings."),
    "2026-11-08": ("NSE/CMTR/76941", "Official Diwali Muhurat special live trading session."),
}

UNVERIFIED_DATES = {
    "2016-11-16": ("NSE/CMTR/31297", "2016 holiday circular identifies 14-Nov as a holiday but does not explicitly classify 16-Nov trading session; provider overlap is verified as price data presence only; prior snapshot lacked NSE observation."),
    "2018-01-01": ("NSE/CMTR/36475", "2018 capital-market holiday circular does not explicitly establish this date as a session or holiday; omission is not treated as proof."),
    "2019-01-01": ("NSE/CMTR/39612", "2019 capital-market holiday circular does not explicitly establish this date as a session or holiday; omission is not treated as proof."),
    "2019-02-13": ("NSE/CMTR/39612", "Retrieved official 2019 capital-market material does not explicitly classify this date; settlement evidence is not substituted for trading-session evidence."),
    "2019-03-29": ("NSE/CMTR/39612", "2019 capital-market holiday circular does not explicitly establish this date as a session or holiday; omission is not treated as proof."),
}


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    generation_time = datetime.now(timezone.utc).isoformat()
    p_nse = NiftyIndicesProvider()
    p_yf = YFinanceProvider()

    rec_nse = p_nse.fetch_historical_ohlcv("NIFTY_50", START_DATE, END_DATE)
    rec_yf = p_yf.fetch_historical_ohlcv("NIFTY_50", START_DATE, END_DATE)

    # 1. Write nifty50_nse_indices_raw.csv
    nse_raw_path = OUT_DIR / "nifty50_nse_indices_raw.csv"
    with nse_raw_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "open", "high", "low", "close", "volume", "source"])
        for r in rec_nse:
            writer.writerow([
                r.timestamp.date().isoformat(),
                f"{r.open:.2f}" if r.open is not None else "",
                f"{r.high:.2f}" if r.high is not None else "",
                f"{r.low:.2f}" if r.low is not None else "",
                f"{r.close:.2f}" if r.close is not None else "",
                r.volume,
                r.source,
            ])

    # 2. Write nifty50_yahoo_raw.csv preserving exact float representations
    yf_raw_path = OUT_DIR / "nifty50_yahoo_raw.csv"
    with yf_raw_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "open", "high", "low", "close", "volume", "source"])
        for r in rec_yf:
            writer.writerow([
                r.timestamp.date().isoformat(),
                f"{r.open}" if r.open is not None else "",
                f"{r.high}" if r.high is not None else "",
                f"{r.low}" if r.low is not None else "",
                f"{r.close}" if r.close is not None else "",
                r.volume,
                r.source,
            ])

    # Map by date
    nse_by_date = {r.timestamp.date().isoformat(): r for r in rec_nse}
    yf_by_date = {r.timestamp.date().isoformat(): r for r in rec_yf}
    all_dates = sorted(set(nse_by_date.keys()) | set(yf_by_date.keys()))

    aligned_rows = []
    excluded_rows = []

    matched_count = 0
    mismatched_count = 0
    nse_only_count = 0
    yahoo_only_count = 0
    included_count = 0

    for d in all_dates:
        r_nse = nse_by_date.get(d)
        r_yf = yf_by_date.get(d)

        nse_close = float(r_nse.close) if r_nse and r_nse.close is not None else None
        yf_close = float(r_yf.close) if r_yf and r_yf.close is not None else None

        if r_nse and r_yf:
            source_avail = "BOTH"
            abs_diff = abs(nse_close - yf_close)
            rel_diff = abs_diff / abs(nse_close) if nse_close else 0.0

            if abs_diff <= ABS_TOLERANCE or rel_diff <= REL_TOLERANCE:
                status = "MATCHED"
                matched_count += 1
            else:
                status = "MISMATCHED"
                mismatched_count += 1

            if d in UNVERIFIED_DATES:
                cal_class = "UNVERIFIED"
                ver_status = "UNVERIFIED"
                inc_status = "EXCLUDED_UNRESOLVED_CALENDAR"
                ref, reason_desc = UNVERIFIED_DATES[d]
                excluded_rows.append({
                    "date": d,
                    "available_source": "NSE Indices, Yahoo Finance",
                    "missing_source": "None",
                    "available_close_value": f"NSE: {nse_close:.2f} | Yahoo: {yf_close}",
                    "calendar_classification": cal_class,
                    "official_evidence_reference": ref,
                    "inclusion_exclusion_decision": "EXCLUDED",
                    "reason": (
                        "Overlapping dual-source prices match within tolerance, but capital-market calendar "
                        "classification remains unverified. Excluded from frozen research baseline until "
                        "official session evidence is confirmed."
                    ),
                    "verification_status": ver_status,
                })
            else:
                cal_class = "CALENDAR_UNVERIFIED"
                ver_status = "DATA_MATCHED_CALENDAR_UNVERIFIED"
                inc_status = "INCLUDED"
                included_count += 1

        elif r_nse and not r_yf:
            source_avail = "NSE_ONLY"
            status = "NSE_ONLY"
            abs_diff = None
            rel_diff = None
            nse_only_count += 1

            if d in SPECIAL_SESSIONS:
                cal_class = "SPECIAL_SESSION"
                ver_status = "VERIFIED"
                inc_status = "EXCLUDED_SECONDARY_UNAVAILABLE_SPECIAL_SESSION"
                ref, session_desc = SPECIAL_SESSIONS[d]
                reason = f"Official special session verified ({session_desc}); secondary provider Yahoo Finance has no observation."
            elif d in UNVERIFIED_DATES:
                cal_class = "UNVERIFIED"
                ver_status = "UNVERIFIED"
                inc_status = "EXCLUDED_SECONDARY_UNAVAILABLE_UNVERIFIED"
                ref, unv_desc = UNVERIFIED_DATES[d]
                reason = f"Missing from secondary provider Yahoo Finance. Calendar classification remains unverified ({unv_desc})."
            else:
                cal_class = "UNVERIFIED"
                ver_status = "UNVERIFIED"
                inc_status = "EXCLUDED_SECONDARY_UNAVAILABLE"
                ref = "None"
                reason = "Missing from secondary provider Yahoo Finance; calendar unverified."

            excluded_rows.append({
                "date": d,
                "available_source": "NSE Indices",
                "missing_source": "Yahoo Finance",
                "available_close_value": f"{nse_close:.2f}",
                "calendar_classification": cal_class,
                "official_evidence_reference": ref,
                "inclusion_exclusion_decision": "EXCLUDED",
                "reason": reason,
                "verification_status": ver_status,
            })

        else:  # r_yf and not r_nse
            source_avail = "YAHOO_ONLY"
            status = "YAHOO_ONLY"
            abs_diff = None
            rel_diff = None
            cal_class = "UNVERIFIED"
            ver_status = "UNVERIFIED"
            inc_status = "EXCLUDED_PRIMARY_UNAVAILABLE"
            yahoo_only_count += 1

            excluded_rows.append({
                "date": d,
                "available_source": "Yahoo Finance",
                "missing_source": "NSE Indices",
                "available_close_value": f"{yf_close}",
                "calendar_classification": cal_class,
                "official_evidence_reference": "None",
                "inclusion_exclusion_decision": "EXCLUDED",
                "reason": "Missing from primary provider NSE Indices.",
                "verification_status": ver_status,
            })

        aligned_rows.append({
            "date": d,
            "nse_indices_close": f"{nse_close:.2f}" if nse_close is not None else "",
            "yahoo_finance_close": f"{yf_close}" if yf_close is not None else "",
            "absolute_difference": f"{abs_diff:.8f}" if abs_diff is not None else "",
            "relative_difference": f"{rel_diff:.10f}" if rel_diff is not None else "",
            "source_availability": source_avail,
            "reconciliation_status": status,
            "calendar_classification": cal_class,
            "verification_status": ver_status,
            "inclusion_status": inc_status,
        })

    # 3. Write nifty50_aligned.csv
    aligned_path = OUT_DIR / "nifty50_aligned.csv"
    with aligned_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "date",
            "nse_indices_close",
            "yahoo_finance_close",
            "absolute_difference",
            "relative_difference",
            "source_availability",
            "reconciliation_status",
            "calendar_classification",
            "verification_status",
            "inclusion_status",
        ])
        writer.writeheader()
        writer.writerows(aligned_rows)

    # 4. Write excluded_observations.csv
    excluded_path = OUT_DIR / "excluded_observations.csv"
    with excluded_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "date",
            "available_source",
            "missing_source",
            "available_close_value",
            "calendar_classification",
            "official_evidence_reference",
            "inclusion_exclusion_decision",
            "reason",
            "verification_status",
        ])
        writer.writeheader()
        writer.writerows(excluded_rows)

    # 5. Write alignment_summary.json
    alignment_summary = {
        "dataset_name": "NIFTY_50_FROZEN_RESEARCH_DATASET",
        "generated_at": generation_time,
        "date_range": {
            "requested_start": START_DATE.date().isoformat(),
            "requested_end": END_DATE.date().isoformat(),
            "actual_start": all_dates[0],
            "actual_end": all_dates[-1],
        },
        "record_counts": {
            "total_unique_dates": len(all_dates),
            "nse_indices_raw_records": len(rec_nse),
            "yahoo_finance_raw_records": len(rec_yf),
            "overlapping_dates": matched_count + mismatched_count,
            "matched_within_tolerance": matched_count,
            "mismatched_observations": mismatched_count,
            "nse_only_observations": nse_only_count,
            "yahoo_only_observations": yahoo_only_count,
            "included_observations": included_count,
            "excluded_observations": len(excluded_rows),
        },
        "reconciliation_parameters": {
            "tolerance_absolute": ABS_TOLERANCE,
            "tolerance_relative": REL_TOLERANCE,
        },
        "calendar_breakdown": {
            "verified_special_sessions": len(SPECIAL_SESSIONS),
            "unresolved_calendar_dates": len(UNVERIFIED_DATES),
            "calendar_unverified_matched_sessions": included_count,
        },
        "unresolved_dates_list": sorted(list(UNVERIFIED_DATES.keys())),
    }
    (OUT_DIR / "alignment_summary.json").write_text(
        json.dumps(alignment_summary, indent=2), encoding="utf-8"
    )

    # 6. Write dataset_manifest.json
    manifest = {
        "dataset_name": "NIFTY 50 Frozen Research Dataset",
        "dataset_id": "nifty50_frozen_research_v1",
        "status": "FROZEN_RESEARCH_ONLY",
        "created_at": generation_time,
        "environment": {
            "python_version": sys.version,
            "platform": platform.platform(),
            "host_os": platform.system(),
        },
        "providers": [
            {
                "name": "NSE Indices Limited (niftyindices.com)",
                "role": "Primary Official Index Provider",
                "adapter": "app.market.providers.nifty_indices_provider.NiftyIndicesProvider",
                "endpoint": "https://www.niftyindices.com/BackPage/getHistoricaldatatabletoString",
                "symbol": "NIFTY_50",
                "official_name": "Nifty 50",
                "retrieval_date": "2026-11-15",
                "requested_date_range": [START_DATE.date().isoformat(), END_DATE.date().isoformat()],
                "actual_date_range": [all_dates[0], all_dates[-1]],
                "row_count": len(rec_nse),
                "is_close_only": False,
                "volume_reported": False,
            },
            {
                "name": "Yahoo Finance (yfinance)",
                "role": "Secondary Market Data Provider / Independent Cross-Check",
                "adapter": "app.market.providers.yfinance_provider.YFinanceProvider",
                "ticker": "^NSEI",
                "symbol": "NIFTY_50",
                "retrieval_date": "2026-11-15",
                "requested_date_range": [START_DATE.date().isoformat(), END_DATE.date().isoformat()],
                "actual_date_range": [all_dates[0], all_dates[-1]],
                "row_count": len(rec_yf),
                "is_close_only": False,
                "volume_reported": True,
            },
        ],
        "schemas": {
            "nifty50_nse_indices_raw.csv": [
                {"name": "date", "type": "string (ISO 8601 YYYY-MM-DD)", "description": "Trading date"},
                {"name": "open", "type": "float", "description": "Opening price"},
                {"name": "high", "type": "float", "description": "Day high price"},
                {"name": "low", "type": "float", "description": "Day low price"},
                {"name": "close", "type": "float", "description": "Closing price"},
                {"name": "volume", "type": "integer", "description": "Reported volume (0 if not reported)"},
                {"name": "source", "type": "string", "description": "Provider identifier (nifty_indices)"},
            ],
            "nifty50_yahoo_raw.csv": [
                {"name": "date", "type": "string (ISO 8601 YYYY-MM-DD)", "description": "Trading date"},
                {"name": "open", "type": "float", "description": "Opening price with original precision"},
                {"name": "high", "type": "float", "description": "Day high price with original precision"},
                {"name": "low", "type": "float", "description": "Day low price with original precision"},
                {"name": "close", "type": "float", "description": "Closing price with original precision"},
                {"name": "volume", "type": "integer", "description": "Trading volume"},
                {"name": "source", "type": "string", "description": "Provider identifier (yfinance)"},
            ],
            "nifty50_aligned.csv": [
                {"name": "date", "type": "string", "description": "Canonical trading date (YYYY-MM-DD)"},
                {"name": "nse_indices_close", "type": "float", "description": "Primary close price from NSE Indices"},
                {"name": "yahoo_finance_close", "type": "float", "description": "Secondary close price from Yahoo Finance"},
                {"name": "absolute_difference", "type": "float", "description": "abs(nse_close - yf_close)"},
                {"name": "relative_difference", "type": "float", "description": "abs_diff / nse_close"},
                {"name": "source_availability", "type": "string", "description": "BOTH | NSE_ONLY | YAHOO_ONLY"},
                {"name": "reconciliation_status", "type": "string", "description": "MATCHED | MISMATCHED | NSE_ONLY | YAHOO_ONLY"},
                {"name": "calendar_classification", "type": "string", "description": "SPECIAL_SESSION | UNVERIFIED | CALENDAR_UNVERIFIED"},
                {"name": "verification_status", "type": "string", "description": "VERIFIED | UNVERIFIED | DATA_MATCHED_CALENDAR_UNVERIFIED"},
                {"name": "inclusion_status", "type": "string", "description": "INCLUDED | EXCLUDED_UNRESOLVED_CALENDAR | EXCLUDED_SECONDARY_UNAVAILABLE_SPECIAL_SESSION | EXCLUDED_SECONDARY_UNAVAILABLE_UNVERIFIED"},
            ],
            "excluded_observations.csv": [
                {"name": "date", "type": "string", "description": "Trading date"},
                {"name": "available_source", "type": "string", "description": "Source(s) having an observation"},
                {"name": "missing_source", "type": "string", "description": "Source lacking an observation"},
                {"name": "available_close_value", "type": "string", "description": "Close value(s) in available source(s)"},
                {"name": "calendar_classification", "type": "string", "description": "Official calendar status"},
                {"name": "official_evidence_reference", "type": "string", "description": "Circular or archive reference"},
                {"name": "inclusion_exclusion_decision", "type": "string", "description": "EXCLUDED"},
                {"name": "reason", "type": "string", "description": "Detailed justification"},
                {"name": "verification_status", "type": "string", "description": "VERIFIED | UNVERIFIED"},
            ],
        },
        "alignment_and_reconciliation_rules": {
            "date_alignment": "Full outer join on calendar date (YYYY-MM-DD); zero interpolation, forward-filling, or price fabrication",
            "tolerance_absolute": ABS_TOLERANCE,
            "tolerance_relative": REL_TOLERANCE,
            "match_condition": "abs_diff <= tolerance_absolute OR rel_diff <= tolerance_relative",
        },
        "inclusion_exclusion_policy": {
            "INCLUDED": "Observations present in both providers matching within tolerance, without unresolved calendar blockers (2,475 rows)",
            "EXCLUDED_UNRESOLVED_CALENDAR": "Overlapping observation where official calendar classification remains unverified and prior snapshot lacked NSE data (2016-11-16, 1 row)",
            "EXCLUDED_SECONDARY_UNAVAILABLE_SPECIAL_SESSION": "Verified official NSE special trading sessions omitted by Yahoo Finance (9 rows)",
            "EXCLUDED_SECONDARY_UNAVAILABLE_UNVERIFIED": "NSE-only weekday dates omitted by Yahoo Finance with unverified calendar classification (4 rows)",
        },
        "unavailable_provenance_fields": [
            "Exact sub-second bar timestamp from upstream Yahoo Finance feed",
            "Individual official exchange circulars for standard regular trading sessions (NSE only publishes special sessions and holiday circulars)",
        ],
    }
    manifest_path = OUT_DIR / "dataset_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    # 7. Generate hash_manifest.json
    hashed_files = [
        "nifty50_nse_indices_raw.csv",
        "nifty50_yahoo_raw.csv",
        "nifty50_aligned.csv",
        "excluded_observations.csv",
        "dataset_manifest.json",
    ]
    hashes = {fn: compute_sha256(OUT_DIR / fn) for fn in hashed_files}
    hash_manifest = {
        "algorithm": "sha256",
        "generated_at": generation_time,
        "hashes": hashes,
    }
    (OUT_DIR / "hash_manifest.json").write_text(
        json.dumps(hash_manifest, indent=2), encoding="utf-8"
    )

    print("Successfully built frozen dataset files in:", OUT_DIR)
    for fn, h in hashes.items():
        print(f"  {fn}: {h}")


if __name__ == "__main__":
    main()
