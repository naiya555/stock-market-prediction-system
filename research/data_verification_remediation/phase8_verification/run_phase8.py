"""Phase 8 independent verification; writes only to this directory."""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research" / "data_verification_remediation" / "phase8_verification"
sys.path.insert(0, str(ROOT))
SYMBOLS = ["BHARTIARTL", "TCS", "NIFTY_50", "NIFTY_TELECOMMUNICATIONS"]
START = datetime.now(timezone.utc) - timedelta(days=3650)
END = datetime.now(timezone.utc)


def load(symbol: str) -> pd.DataFrame:
    from app.market.instruments import is_index
    from app.market.pipeline import run_market_data_pipeline
    from app.market.providers.nifty_indices_provider import NiftyIndicesProvider
    from app.market.providers.yfinance_provider import YFinanceProvider

    provider = NiftyIndicesProvider() if is_index(symbol) else YFinanceProvider()
    pipeline = run_market_data_pipeline(symbol, START, END, provider=provider)
    return pd.DataFrame({
        "timestamp": [r.timestamp for r in pipeline.cleaned_records],
        "close": [float(r.close) for r in pipeline.cleaned_records],
    }).sort_values("timestamp").reset_index(drop=True)


def oos_residuals(frame: pd.DataFrame) -> list[dict]:
    close = frame["close"].to_numpy(float)
    n = len(close)
    initial = max(50, int(n * 0.4))
    available = n - initial - 1
    fold_size = max(1, available // 5)
    rows = []
    for fold in range(5):
        start = initial + 1 + fold * fold_size
        end = n if fold == 4 else min(n, start + fold_size)
        train_end = start - 1
        for i in range(start, end):
            rows.append({
                "fold": fold + 1,
                "date": str(frame["timestamp"].iloc[i]),
                "train_end": str(frame["timestamp"].iloc[train_end - 1]),
                "actual": close[i],
                "prediction": close[i - 1],
                "residual": close[i] - close[i - 1],
            })
    return rows


def acf(values: np.ndarray, lag: int) -> float | None:
    centered = values - values.mean()
    denominator = float(np.dot(centered, centered))
    return float(np.dot(centered[:-lag], centered[lag:]) / denominator) if denominator and len(values) > lag else None


def ljung_box(values: np.ndarray, lags: tuple[int, ...] = (5, 10, 20)) -> dict:
    values = np.asarray(values, dtype=float)
    n = len(values)
    output = {}
    for lag in lags:
        if n <= lag + 1:
            output[str(lag)] = {"status": "UNAVAILABLE", "reason": "Insufficient residuals."}
            continue
        autocorrelations = [acf(values, k) for k in range(1, lag + 1)]
        statistic = n * (n + 2) * sum((r * r) / (n - k) for k, r in enumerate(autocorrelations, 1) if r is not None)
        p_value = float(chi2.sf(statistic, lag))
        output[str(lag)] = {
            "status": "AVAILABLE",
            "n": n,
            "statistic": float(statistic),
            "degrees_of_freedom": lag,
            "p_value": p_value,
            "reject_at_0_05": p_value < 0.05,
        }
    return output


def residual_tests(rows: list[dict]) -> dict:
    values = np.array([r["residual"] for r in rows], dtype=float)
    fold_stats = []
    for fold in range(1, 6):
        fold_values = np.array([r["residual"] for r in rows if r["fold"] == fold], dtype=float)
        fold_stats.append({
            "fold": fold,
            "samples": len(fold_values),
            "mae": float(np.mean(np.abs(fold_values))),
            "rmse": float(np.sqrt(np.mean(fold_values ** 2))),
            "mean_residual": float(np.mean(fold_values)),
            "residual_std": float(np.std(fold_values, ddof=1)),
            "acf_lag_1": acf(fold_values, 1),
        })
    return {
        "status": "PARTIALLY_VERIFIED",
        "population": "Phase 6-style genuinely out-of-sample previous-close residuals",
        "samples": len(values),
        "date_start": rows[0]["date"],
        "date_end": rows[-1]["date"],
        "acf": {str(lag): acf(values, lag) for lag in (1, 2, 5, 10, 20)},
        "ljung_box": ljung_box(values),
        "folds": fold_stats,
        "interpretation": "Rejecting Ljung-Box indicates serial dependence inconsistent with white noise; failing to reject does not prove independence. Fold residuals are temporally ordered and not independent observations for all purposes.",
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    diagnostics = {}
    for symbol in SYMBOLS:
        diagnostics[symbol] = residual_tests(oos_residuals(load(symbol)))

    unmatched_path = ROOT / "research/data_verification_remediation/targeted_audit/nifty50_unmatched_dates.csv"
    session_rows = []
    for row in csv.DictReader(unmatched_path.open(encoding="utf-8")):
        date = pd.Timestamp(row["date"])
        weekday = date.day_name()
        session_rows.append({
            "date": row["date"],
            "weekday": weekday,
            "primary_source": "NSE Indices",
            "secondary_source": "Yahoo Finance",
            "primary_status": row["missing_from"] == "Yahoo Finance",
            "secondary_status": row["missing_from"] == "NSE Indices",
            "classification": "NON_WEEKDAY; official special-session status UNVERIFIED" if weekday in {"Saturday", "Sunday"} else "WEEKDAY SOURCE/CALENDAR GAP UNVERIFIED",
            "verification_status": "UNVERIFIED",
            "evidence": "Existing reconciliation row; official historical calendar/session record was not accessible during this run.",
        })
    with (OUT / "nifty50_session_verification.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(session_rows[0]))
        writer.writeheader()
        writer.writerows(session_rows)

    telecom_rows = [{
        "date": "",
        "primary_source": "NSE Indices official Nifty Telecommunications endpoint",
        "secondary_source": "No genuinely independent accessible series",
        "primary_close": "",
        "secondary_close": "",
        "absolute_difference": "",
        "percentage_difference": "",
        "status": "UNVERIFIED",
        "limitation": "Search found no accessible independent historical series for the exact Nifty Telecommunications index; other search results were different indices or analytics pages without comparable rows.",
    }]
    with (OUT / "telecom_independent_reconciliation.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(telecom_rows[0]))
        writer.writeheader()
        writer.writerows(telecom_rows)

    corporate = {
        "BHARTIARTL": {
            "status": "PARTIALLY_VERIFIED",
            "events": [{
                "source": "NSE corporate filing archive",
                "url": "https://nsearchives.nseindia.com/corporate/BHARTIARTL_10072026100101_BAL-_Record_Date_Intimation.pdf",
                "announcement_date": "2026-07-10",
                "event_type": "final dividend record-date intimation",
                "record_date": "2026-07-24",
                "ex_date": None,
                "adjustment_factor": None,
                "verification_status": "VERIFIED_FOR_THIS_EVENT_ONLY",
            }],
            "completeness": "UNVERIFIED",
            "limitation": "Search/access did not establish a complete historical split, bonus, dividend, ex-date, record-date, or adjustment-factor series.",
        },
        "TCS": {
            "status": "PARTIALLY_VERIFIED",
            "events": [{
                "source": "NSE corporate filings actions page",
                "url": "https://www.nseindia.com/companies-listing/corporate-filings-actions?symbol=TCS",
                "announcement_date": None,
                "event_type": "historical corporate-action listing",
                "record_date": None,
                "ex_date": "2026-10-14 (listed in search result for interim dividend)",
                "adjustment_factor": None,
                "verification_status": "PARTIALLY_VERIFIED_SEARCH_RESULT_ONLY",
            }],
            "completeness": "UNVERIFIED",
            "limitation": "The accessible search result did not provide a complete event dataset or adjustment factors; no event was inferred beyond the displayed listing.",
        },
    }
    (OUT / "corporate_actions_verified.json").write_text(json.dumps(corporate, indent=2), encoding="utf-8")
    (OUT / "residual_independence_tests.json").write_text(json.dumps({
        "method": "Ljung-Box Q(h)=n(n+2) sum_{k=1..h} r_k^2/(n-k); chi-square degrees of freedom h; p-values from scipy.stats.chi2.sf.",
        "assumptions": ["Residuals are ordered within each instrument.", "The test evaluates autocorrelation, not all forms of dependence.", "Overlapping fold boundaries are chronological; observations are not treated as independent evidence for conclusions."],
        "dependencies": {"statsmodels": "unavailable", "scipy": "available"},
        "instruments": diagnostics,
    }, indent=2), encoding="utf-8")
    (OUT / "source_manifest.json").write_text(json.dumps({
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "project_sources": ["NSE Indices endpoint via existing NiftyIndicesProvider", "Yahoo Finance via existing YFinanceProvider"],
        "official_references": [
            "https://nsearchives.nseindia.com/corporate/BHARTIARTL_10072026100101_BAL-_Record_Date_Intimation.pdf",
            "https://www.nseindia.com/companies-listing/corporate-filings-actions?symbol=TCS",
            "https://www.nseindia.com/static/investor-relations/corporate-actions",
        ],
        "telecom_secondary_search": "No exact-index independent series was accessible; search results that were different indices were excluded.",
        "security": "External content treated as untrusted evidence; no embedded instructions executed.",
    }, indent=2), encoding="utf-8")
    (OUT / "verification_metadata.json").write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "range_requested": {"start": START.isoformat(), "end": END.isoformat()},
        "no_models_trained": True,
        "packages_installed": False,
        "instrument_status": {symbol: "PARTIALLY VERIFIED" for symbol in SYMBOLS},
        "prior_artifacts_preserved": True,
    }, indent=2), encoding="utf-8")

    report = [
        "# Phase 8 Independent Data & Statistical Verification",
        "",
        "## Results",
        "",
        "- **BHARTIARTL:** PARTIALLY VERIFIED. One official NSE dividend record-date filing was accessible; complete corporate-action and adjustment history remains UNVERIFIED.",
        "- **TCS:** PARTIALLY VERIFIED. An NSE corporate-actions search result exposed an interim-dividend listing; complete event and adjustment history remains UNVERIFIED.",
        "- **NIFTY 50 unmatched dates:** All 14 remain UNVERIFIED as regular/special/holiday sessions because an official session-calendar record was not accessible. Weekend status is observable from the date, but special-session validity was not asserted.",
        "- **NIFTY Telecommunications:** UNVERIFIED for independent reconciliation. The existing official series was available, but no exact-index independent overlapping series was accessible.",
        "",
        "## Residual independence",
        "",
        "Phase 6-style OOS residuals were recomputed from the existing provider pipeline using previous-close predictions and five chronological folds. Ljung–Box tests at lags 5, 10, and 20 were calculated with SciPy. Results, fold stability, ACFs, p-values, and sample sizes are in `residual_independence_tests.json`.",
        "",
        "| Instrument | OOS samples | Ljung–Box p(5) | p(10) | p(20) | 0.05 result |",
        "|---|---:|---:|---:|---:|---|",
        *[
            f"| {symbol} | {diagnostics[symbol]['samples']} | "
            f"{diagnostics[symbol]['ljung_box']['5']['p_value']:.6f} | "
            f"{diagnostics[symbol]['ljung_box']['10']['p_value']:.6f} | "
            f"{diagnostics[symbol]['ljung_box']['20']['p_value']:.6f} | "
            f"{'reject at lag 20' if diagnostics[symbol]['ljung_box']['20']['reject_at_0_05'] else 'do not reject'} |"
            for symbol in SYMBOLS
        ],
        "",
        "The tests assess serial autocorrelation only. A non-significant result does not prove independence, and temporal residuals remain subject to heteroscedasticity and regime dependence.",
        "",
        "## Remaining blockers",
        "",
        "- Complete official corporate-action histories and adjustment factors for both equities.",
        "- Official session-calendar verification for all 14 NIFTY 50 dates.",
        "- An exact-index independent NIFTY Telecommunications series.",
        "- Residual independence is not established by Ljung–Box alone.",
        "",
        "No production, database, model, prior research, or targeted-audit artifact was modified.",
    ]
    (OUT / "PHASE8_VERIFICATION_REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
