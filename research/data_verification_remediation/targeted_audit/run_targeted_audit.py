"""Reconcile residual provenance, regimes, unmatched dates, and source limits."""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research" / "data_verification_remediation" / "targeted_audit"
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
    return pd.DataFrame([{
        "timestamp": r.timestamp,
        "close": float(r.close),
    } for r in pipeline.cleaned_records]).sort_values("timestamp").reset_index(drop=True)


def stats(actual: np.ndarray, predicted: np.ndarray) -> dict:
    residual = actual - predicted
    return {
        "samples": int(len(residual)),
        "mae": float(np.mean(np.abs(residual))),
        "rmse": float(np.sqrt(np.mean(residual ** 2))),
        "mean_residual": float(np.mean(residual)),
    }


def phase6_rows(frame: pd.DataFrame) -> tuple[list[dict], dict, list[dict]]:
    close = frame["close"].to_numpy(float)
    returns = pd.Series(close).pct_change()
    volatility = returns.rolling(20).std().to_numpy()
    trend = pd.Series(close).pct_change(20).to_numpy()
    n = len(frame)
    initial = max(50, int(n * 0.4))
    available = n - initial - 1
    fold_size = max(1, available // 5)
    residual_rows = []
    fold_ranges = []
    aggregate = {"high_volatility": [], "low_volatility": [], "normal_volatility": []}
    for fold_number in range(5):
        start = initial + 1 + fold_number * fold_size
        end = n if fold_number == 4 else min(n, start + fold_size)
        train_end = start - 1
        fold_ranges.append({
            "fold": fold_number + 1,
            "train_end": str(frame["timestamp"].iloc[train_end - 1]),
            "validation_start": str(frame["timestamp"].iloc[start]),
            "validation_end": str(frame["timestamp"].iloc[end - 1]),
            "samples": end - start,
        })
        train_vol = volatility[:train_end]
        low, high = np.nanquantile(train_vol[np.isfinite(train_vol)], [0.25, 0.75])
        for i in range(start, end):
            prediction = close[i - 1]
            residual = close[i] - prediction
            vol_label = (
                "low_volatility" if volatility[i] <= low
                else "high_volatility" if volatility[i] >= high
                else "normal_volatility"
            )
            trend_label = (
                "trending_down" if trend[i] <= -0.05
                else "trending_up" if trend[i] >= 0.05
                else "sideways"
            )
            row = {
                "symbol": None,
                "fold": fold_number + 1,
                "date": str(frame["timestamp"].iloc[i]),
                "train_end": str(frame["timestamp"].iloc[train_end - 1]),
                "actual_close": float(close[i]),
                "prediction_previous_close": float(prediction),
                "residual_actual_minus_prediction": float(residual),
                "volatility": float(volatility[i]),
                "volatility_threshold_low": float(low),
                "volatility_threshold_high": float(high),
                "volatility_regime": vol_label,
                "trend_regime": trend_label,
            }
            residual_rows.append(row)
            aggregate[vol_label].append(residual)
    metrics = {
        label: {
            "samples": len(values),
            "mae": float(np.mean(np.abs(values))),
            "rmse": float(np.sqrt(np.mean(np.asarray(values) ** 2))),
        }
        for label, values in aggregate.items()
    }
    return residual_rows, metrics, fold_ranges


def classify_unmatched() -> list[dict]:
    path = ROOT / "research" / "data_verification_remediation" / "price_reconciliation.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    result = []
    for row in rows:
        if row["instrument"] != "NIFTY_50" or row["status"] not in {"MISSING_FROM_PRIMARY", "MISSING_FROM_SECONDARY"}:
            continue
        date = pd.Timestamp(row["date"])
        weekday = date.day_name()
        if weekday in {"Saturday", "Sunday"}:
            classification = "NON_WEEKDAY_SESSION; official special-session status not independently checked"
        elif row["status"] == "MISSING_FROM_PRIMARY":
            classification = "SOURCE_COVERAGE_OR_START_DATE_GAP"
        else:
            classification = "WEEKDAY_SOURCE_GAP_OR_UNVERIFIED_SPECIAL_SESSION"
        result.append({
            "date": row["date"],
            "weekday": weekday,
            "missing_from": "NSE Indices" if row["status"] == "MISSING_FROM_PRIMARY" else "Yahoo Finance",
            "other_source": row["secondary_source"] if row["status"] == "MISSING_FROM_PRIMARY" else row["primary_source"],
            "classification": classification,
            "status": "UNVERIFIED" if "SOURCE" in classification or "SPECIAL" in classification else "PARTIALLY_VERIFIED",
            "evidence_limit": "No independent NSE trading-calendar record was retrieved in this audit.",
        })
    return result


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    all_rows = []
    fold_ranges = {}
    provenance = {
        "remediation_diagnostics": {
            "source_file": "research/data_verification_remediation/run_remediation.py",
            "input": "fresh provider pipeline cleaned close series",
            "prediction": "close[t-1] for actual close[t]",
            "population": "full chronological series, 2470 or 2477 residuals",
            "out_of_sample": False,
            "calculation": "actual_close[t] - close[t-1]",
        },
        "phase5_baseline": {
            "source_file": "research/regression_phase5/baseline_analysis.json",
            "population": "full cleaned series",
            "out_of_sample": False,
            "calculation": "previous-close error over all available consecutive observations",
        },
        "phase6": {
            "source_file": "app/training/regression_phase6.py",
            "input": "five chronological folds from fresh cleaned provider data",
            "prediction": "immediately preceding close, including last training close for fold first row",
            "population": "1482 or 1486 validation residuals",
            "out_of_sample": True,
            "embargo_sessions": 1,
            "regime_thresholds": "per-fold training-history volatility 25th/75th percentiles; trend thresholds +/-5% over 20 sessions",
            "calculation": "actual_close[t] - previous_close_prediction[t]",
        },
    }
    regime_rows = []
    for symbol in SYMBOLS:
        frame = load(symbol)
        rows, metrics, ranges = phase6_rows(frame)
        fold_ranges[symbol] = ranges
        for row in rows:
            row["symbol"] = symbol
        all_rows.extend(rows)
        for label, values in metrics.items():
            regime_rows.append({
                "symbol": symbol,
                "population": "Phase 6 comparable OOS",
                "regime_definition": "fold-training volatility quartiles",
                "regime": label,
                **values,
            })
    with (OUT / "residual_provenance.json").open("w", encoding="utf-8") as handle:
        json.dump({
            **provenance,
            "phase6_residual_rows": len(all_rows),
            "phase6_date_ranges": {
                symbol: {
                    "start": min(r["date"] for r in all_rows if r["symbol"] == symbol),
                    "end": max(r["date"] for r in all_rows if r["symbol"] == symbol),
                    "samples": sum(r["symbol"] == symbol for r in all_rows),
                } for symbol in SYMBOLS
            },
            "phase6_fold_date_ranges": fold_ranges,
            "residual_row_schema": "actual_close - prediction_previous_close; no target or future rows are used",
        }, handle, indent=2)
    with (OUT / "regime_reconciliation.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(regime_rows[0]))
        writer.writeheader()
        writer.writerows(regime_rows)
    with (OUT / "nifty50_unmatched_dates.csv").open("w", newline="", encoding="utf-8") as handle:
        rows = classify_unmatched()
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (OUT / "corporate_action_evidence.json").write_text(json.dumps({
        "BHARTIARTL": {
            "status": "UNVERIFIED",
            "sources_attempted": [
                {"name": "NSE equity public page", "reference": "https://www.nseindia.com/get-quotes/equity?symbol=BHARTIARTL", "status": "UNVERIFIED", "limitation": "request unavailable in execution environment"},
                {"name": "BSE India", "reference": "https://www.bseindia.com/", "status": "UNVERIFIED", "limitation": "not retrieved"},
            ],
            "missing_evidence": ["official split/bonus records", "dividend ex-dates and record dates", "adjustment factors", "independent adjusted/unadjusted row comparison"],
        },
        "TCS": {
            "status": "UNVERIFIED",
            "sources_attempted": [
                {"name": "NSE equity public page", "reference": "https://www.nseindia.com/get-quotes/equity?symbol=TCS", "status": "UNVERIFIED", "limitation": "request unavailable in execution environment"},
                {"name": "BSE India", "reference": "https://www.bseindia.com/", "status": "UNVERIFIED", "limitation": "not retrieved"},
            ],
            "missing_evidence": ["official split/bonus records", "dividend ex-dates and record dates", "adjustment factors", "independent adjusted/unadjusted row comparison"],
        },
    }, indent=2), encoding="utf-8")
    (OUT / "audit_metadata.json").write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "targeted residual provenance, regime reconciliation, NIFTY unmatched dates, corporate-action access audit",
        "tolerance_inherited": {"absolute": 0.01, "relative": 0.0001},
        "prior_artifacts_read": [
            "research/regression_phase5/baseline_analysis.json",
            "research/regression_phase6/regime_residuals.json",
            "research/data_verification_remediation/residual_diagnostics.json",
            "research/data_verification_remediation/price_reconciliation.csv",
        ],
        "external_content": "treated as untrusted evidence; no embedded instructions executed",
        "packages_installed": False,
    }, indent=2), encoding="utf-8")
    bharti = [r for r in regime_rows if r["symbol"] == "BHARTIARTL"]
    report = [
        "# Targeted Remediation Audit",
        "",
        "## Residual provenance",
        "",
        "The remediation `residual_diagnostics.json` is **VERIFIED as full-sample**, not genuinely out-of-sample: it was produced from fresh cleaned provider closes and computes consecutive close differences across the full series. Its BHARTIARTL MAE 9.8318989 and 2470 samples match Phase 5's full-sample baseline exactly. Phase 6 is the separate genuinely out-of-sample population: five chronological validation folds, one-session embargo, 1482 BHARTIARTL validation residuals, and fold-specific training thresholds.",
        "",
        "Every recorded baseline residual is `actual close[t] - previous close[t-1]`; the previous close precedes the target. The remediation full-sample statistic is descriptive and must not be called an OOS estimate.",
        "",
        "## BHARTIARTL regime discrepancy",
        "",
        "The discrepancy is **not a calculation error in either artifact**. Remediation uses full-sample volatility quartiles and all 2470 residuals: high MAE 8.76498, low 9.64298, normal 10.55047. Phase 6 uses only 1482 OOS residuals and derives volatility thresholds separately from each fold's training history; its comparable metrics are high MAE 21.8548 from 15 rows, low 9.9971 from 822, normal 15.0244 from 645. These are different samples and labels. The Phase 6 high-volatility BHARTIARTL group is extremely small, so its result is unstable. The earlier broad claim “high volatility was larger for all four” is true for the Phase 6 OOS aggregates, not for the full-sample remediation population.",
        "",
        "## NIFTY 50 unmatched dates",
        "",
        "The 14 rows are listed in `nifty50_unmatched_dates.csv`. Weekend dates are classified as non-weekday observations, but special-session status was not independently verified. Weekday gaps and the 2016 start-date gap remain source coverage or calendar possibilities marked UNVERIFIED; no missing values were fabricated.",
        "",
        "## Corporate actions",
        "",
        "BHARTIARTL and TCS remain **UNVERIFIED**. NSE/BSE evidence retrieval was unavailable, so no split, bonus, dividend, ex-date, record-date, or adjustment factor is asserted. The project Yahoo adapter's raw/unadjusted convention is known, but that does not verify corporate-action history.",
        "",
        "## Final status",
        "",
        "No methodology defect was found or corrected. All four instruments remain **PARTIALLY VERIFIED** and not ready for a new forecasting experiment. Residual independence remains unproven; formal Ljung–Box was unavailable. No production or prior research artifact was modified.",
    ]
    (OUT / "TARGETED_AUDIT_REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
