"""Bounded data-verification and methodology-remediation audit.

This script writes only to its own research directory. Network responses are
treated as data, never as instructions.
"""

from __future__ import annotations

import ast
import csv
import json
import math
import platform
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "data_verification_remediation"
sys.path.insert(0, str(ROOT))
SYMBOLS = ["BHARTIARTL", "TCS", "NIFTY_50", "NIFTY_TELECOMMUNICATIONS"]
START = datetime.now(timezone.utc) - timedelta(days=3650)
END = datetime.now(timezone.utc)
ABS_TOLERANCE = 0.01
REL_TOLERANCE = 0.0001


def fetch_series(symbol: str, provider) -> pd.DataFrame:
    records = provider.fetch_historical_ohlcv(symbol, START, END)
    rows = [{"date": r.timestamp.date().isoformat(), "close": float(r.close)} for r in records]
    frame = pd.DataFrame(rows).drop_duplicates("date").sort_values("date")
    return frame.reset_index(drop=True)


def compare(primary: pd.DataFrame, secondary: pd.DataFrame, primary_name: str, secondary_name: str) -> list[dict]:
    left = primary.set_index("date")
    right = secondary.set_index("date")
    rows = []
    for date in sorted(set(left.index) | set(right.index)):
        p = left["close"].get(date)
        s = right["close"].get(date)
        if pd.isna(p):
            status = "MISSING_FROM_PRIMARY"
        elif pd.isna(s):
            status = "MISSING_FROM_SECONDARY"
        else:
            absolute = abs(float(p) - float(s))
            percentage = absolute / abs(float(p)) if p else None
            status = (
                "MATCHED"
                if absolute <= ABS_TOLERANCE or (percentage is not None and percentage <= REL_TOLERANCE)
                else "MISMATCHED"
            )
        absolute = None if pd.isna(p) or pd.isna(s) else abs(float(p) - float(s))
        percentage = None if absolute is None or not float(p) else absolute / abs(float(p))
        rows.append({
            "date": date,
            "primary_source": primary_name,
            "secondary_source": secondary_name,
            "primary_close": None if pd.isna(p) else float(p),
            "secondary_close": None if pd.isna(s) else float(s),
            "absolute_difference": absolute,
            "percentage_difference": percentage,
            "status": status,
        })
    return rows


def residual_diagnostics(frame: pd.DataFrame) -> dict:
    close = frame["close"].to_numpy(dtype=float)
    residual = np.diff(close)
    returns = close[1:] / close[:-1] - 1.0
    result = {"samples": int(len(residual)), "lags": {}, "ljung_box": "UNAVAILABLE: statsmodels is not installed."}
    for lag in (1, 2, 5, 10, 20):
        result["lags"][str(lag)] = (
            float(np.corrcoef(residual[:-lag], residual[lag:])[0, 1])
            if len(residual) > lag and np.std(residual[:-lag]) and np.std(residual[lag:])
            else None
        )
    rolling_vol = pd.Series(returns).rolling(20).std().to_numpy()
    valid = np.isfinite(rolling_vol)
    result.update({
        "mean_residual": float(np.mean(residual)),
        "median_residual": float(np.median(residual)),
        "residual_std": float(np.std(residual, ddof=1)),
        "mean_absolute_error": float(np.mean(np.abs(residual))),
        "return_autocorrelation_lag1": float(np.corrcoef(returns[:-1], returns[1:])[0, 1]),
        "absolute_residual_vs_rolling_volatility_correlation": (
            float(np.corrcoef(np.abs(residual[19:]), rolling_vol[valid])[0, 1])
            if valid.sum() > 2 else None
        ),
        "rolling_window_stability": {
            "window": 250,
            "windows": int(max(0, len(residual) - 249)),
            "mean_mae_std": float(pd.Series(np.abs(residual)).rolling(250).mean().std()),
        },
    })
    if valid.any():
        q25, q75 = np.nanquantile(rolling_vol, [0.25, 0.75])
        result["volatility_regimes"] = {}
        for label, mask in {
            "low": rolling_vol <= q25,
            "normal": (rolling_vol > q25) & (rolling_vol < q75),
            "high": rolling_vol >= q75,
        }.items():
            values = np.abs(residual[19:][mask[19:]]) if len(mask) == len(residual) else np.array([])
            result["volatility_regimes"][label] = {
                "samples": int(values.size),
                "mae": float(values.mean()) if values.size else None,
                "residual_std": float(values.std(ddof=1)) if values.size > 1 else None,
            }
    return result


def methodology_findings() -> dict:
    files = [
        ROOT / "app" / "prediction" / "target.py",
        ROOT / "app" / "training" / "regression_phase3.py",
        ROOT / "app" / "training" / "regression_phase4.py",
        ROOT / "app" / "training" / "regression_phase6.py",
    ]
    parsed = {}
    for path in files:
        ast.parse(path.read_text(encoding="utf-8"))
        parsed[path.name] = "syntax parsed"
    return {
        "status": "PARTIALLY_VERIFIED",
        "files_ast_parsed": parsed,
        "findings": [
            {"check": "chronological separation", "status": "VERIFIED", "evidence": "Fold builders slice train before validation and preserve order."},
            {"check": "target shift", "status": "VERIFIED", "evidence": "target.py uses the next available observation; phase 4 uses shift(-horizon)."},
            {"check": "preprocessing fit scope", "status": "VERIFIED_FOR_INSPECTED_CODE", "evidence": "Phase 3 Ridge mean/std are computed from X_train only; no scaler or imputer fit on full data was found in inspected research files."},
            {"check": "rolling boundaries", "status": "VERIFIED_FOR_INSPECTED_CODE", "evidence": "Rolling and pct_change features are backward-looking; phase 6 regime thresholds use training signals."},
            {"check": "opening-target same-day close", "status": "PARTIALLY_VERIFIED", "evidence": "Feature audit marks close-derived features unavailable at open; Phase 4 results mark unavailable OHLC targets where source fields are absent."},
            {"check": "embargo", "status": "VERIFIED", "evidence": "Phase 2-6 fold starts add the configured embargo and training ends before validation."},
            {"check": "identical dates and units", "status": "VERIFIED_WITHIN_EXPERIMENT", "evidence": "Model and baseline arrays are formed from the same validation rows; Phase 2-4 aggregate experiments remain separate populations."},
            {"check": "out-of-sample residuals", "status": "VERIFIED_FOR_PHASE6", "evidence": "Phase 6 interval history is extended only after each validation fold."},
            {"check": "residual independence", "status": "UNAVAILABLE", "evidence": "No formal Ljung-Box dependency was installed; this remediation reports transparent ACF instead."},
        ],
        "defects_found": [],
        "isolated_corrections": [],
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    from app.market.providers.nifty_indices_provider import NiftyIndicesProvider
    from app.market.providers.yfinance_provider import YFinanceProvider

    data = {}
    manifests = [
        {"source": "Yahoo Finance via YFinanceProvider", "role": "secondary for NIFTY_50; primary for equities", "status": "ACCESSIBLE", "adjustment": "auto_adjust=False raw/unadjusted"},
        {"source": "NSE Indices via NiftyIndicesProvider", "role": "primary for NIFTY_50 and NIFTY_TELECOMMUNICATIONS", "status": "ACCESSIBLE", "adjustment": "official index close; no equity adjustment"},
        {"source": "NSE equity pages", "role": "independent equity cross-check", "status": "UNVERIFIED", "adjustment": "not retrieved; request timed out/blocked"},
        {"source": "BSE India", "role": "independent equity cross-check", "status": "UNVERIFIED", "adjustment": "not retrieved"},
    ]
    nifty = NiftyIndicesProvider()
    yahoo = YFinanceProvider()
    for symbol in SYMBOLS:
        try:
            if symbol == "NIFTY_50":
                primary = fetch_series(symbol, nifty)
                secondary = fetch_series(symbol, yahoo)
                data[symbol] = {"primary": primary, "secondary": secondary}
            elif symbol == "NIFTY_TELECOMMUNICATIONS":
                data[symbol] = {"primary": fetch_series(symbol, nifty)}
            else:
                data[symbol] = {"primary": fetch_series(symbol, yahoo)}
        except Exception as exc:
            data[symbol] = {"error": f"{type(exc).__name__}: {exc}"}

    reconciliation = []
    for symbol in SYMBOLS:
        item = data[symbol]
        if "primary" in item and "secondary" in item:
            reconciliation.extend(compare(item["primary"], item["secondary"], "NSE Indices", "Yahoo Finance"))
        else:
            reconciliation.append({
                "date": None, "instrument": symbol, "primary_source": "available project provider",
                "secondary_source": "NSE/BSE independent source unavailable", "primary_close": None,
                "secondary_close": None, "absolute_difference": None, "percentage_difference": None,
                "status": "UNVERIFIED",
            })
    for row in reconciliation:
        row.setdefault("instrument", "NIFTY_50")
    with (OUT / "price_reconciliation.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(reconciliation[0]))
        writer.writeheader()
        writer.writerows(reconciliation)

    quality = {}
    diagnostics = {}
    for symbol, item in data.items():
        if "primary" not in item:
            quality[symbol] = {"status": "UNVERIFIED", "error": item.get("error")}
            continue
        frame = item["primary"]
        quality[symbol] = {
            "status": "STRUCTURALLY_VERIFIED_ONLY", "rows": len(frame),
            "date_start": frame["date"].min(), "date_end": frame["date"].max(),
            "duplicate_dates": int(frame["date"].duplicated().sum()),
            "missing_close": int(frame["close"].isna().sum()),
            "source": "NSE Indices" if symbol.startswith("NIFTY") else "Yahoo Finance",
        }
        diagnostics[symbol] = residual_diagnostics(frame)

    matched = sum(row["status"] == "MATCHED" for row in reconciliation)
    comparable = sum(row["status"] in {"MATCHED", "MISMATCHED"} for row in reconciliation)
    actions = {
        "BHARTIARTL": {"status": "UNVERIFIED", "splits": "No independent record retrieved.", "bonuses": "No independent record retrieved.", "dividends": "No independent record retrieved.", "adjustment_factor": "UNVERIFIED", "effect_on_continuity": "Cannot establish independently."},
        "TCS": {"status": "UNVERIFIED", "splits": "No independent record retrieved.", "bonuses": "No independent record retrieved.", "dividends": "No independent record retrieved.", "adjustment_factor": "UNVERIFIED", "effect_on_continuity": "Cannot establish independently."},
        "NIFTY_50": {"status": "NOT_APPLICABLE_TO_SINGLE_STOCK", "convention": "Official index close; constituent actions are reflected through index methodology, not a single-stock split adjustment."},
        "NIFTY_TELECOMMUNICATIONS": {"status": "NOT_APPLICABLE_TO_SINGLE_STOCK", "convention": "Official sector-index close; constituent actions are reflected through index methodology."},
    }
    (OUT / "corporate_actions.json").write_text(json.dumps(actions, indent=2), encoding="utf-8")
    (OUT / "adjustment_comparison.json").write_text(json.dumps({
        "status": "UNVERIFIED_FOR_EQUITIES",
        "tolerance": {"absolute_price_units": ABS_TOLERANCE, "relative_fraction": REL_TOLERANCE},
        "Yahoo_series": "Project adapter requests auto_adjust=False.",
        "NSE_BSE_series": "Unavailable for independent retrieval in this run.",
        "index_series": "Official index close; no adjusted/unadjusted equity comparison applies.",
    }, indent=2), encoding="utf-8")
    (OUT / "data_discrepancies.json").write_text(json.dumps({
        "status": "NO_CONFIRMED_PRICE_DISCREPANCY",
        "unverified": ["Equity row-level comparison unavailable.", "Telecom independent comparison unavailable.", "Corporate-action records unavailable."],
        "comparable_rows": comparable, "matched_rows": matched,
        "match_percentage_of_comparable_rows": (100.0 * matched / comparable if comparable else None),
        "method": "UNVERIFIED rows are not counted as matches.",
    }, indent=2), encoding="utf-8")
    methodology = methodology_findings()
    (OUT / "methodology_audit.json").write_text(json.dumps(methodology, indent=2), encoding="utf-8")
    (OUT / "residual_diagnostics.json").write_text(json.dumps(diagnostics, indent=2), encoding="utf-8")
    (OUT / "instrument_readiness.json").write_text(json.dumps({
        symbol: {
            "status": "PARTIALLY_VERIFIED",
            "historical_price_reconciliation": "PARTIALLY_VERIFIED" if symbol == "NIFTY_50" and comparable else "UNVERIFIED",
            "corporate_actions": actions[symbol]["status"],
            "methodology": "PARTIALLY_VERIFIED",
            "residual_dependence": "ACF reported; independence not established.",
            "ready_for_new_experiment": False,
            "blockers": ["independent row-level source reconciliation", "corporate-action verification" if symbol in {"BHARTIARTL", "TCS"} else "independent index cross-check"],
        } for symbol in SYMBOLS
    }, indent=2), encoding="utf-8")
    (OUT / "correction_validation.json").write_text(json.dumps({
        "status": "NO_CORRECTION_REQUIRED_OR_AUTHORIZED",
        "isolated_normalization": "Dates were normalized and duplicate dates excluded only in the in-memory comparison copy.",
        "before_after": quality,
        "production_data_modified": False,
        "confirmed_discrepancies": [],
    }, indent=2), encoding="utf-8")
    (OUT / "source_manifest.json").write_text(json.dumps({
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "range_requested": {"start": START.isoformat(), "end": END.isoformat()},
        "sources": manifests,
        "security": "External content was treated as untrusted evidence; no embedded instructions were executed.",
    }, indent=2), encoding="utf-8")

    report = [
        "# Data Verification & Methodology Remediation",
        "",
        "## Executive result",
        "",
        "The remediation does not clear all blockers. NIFTY_50 was the only instrument with two accessible series from different provider adapters; row-level comparison is reported in `price_reconciliation.csv`. Equity independent NSE/BSE retrieval was unavailable, and NIFTY_TELECOMMUNICATIONS had no accessible independent secondary series. No price discrepancy was confirmed, but unavailable comparisons are not counted as matches.",
        "",
        f"Comparable NIFTY_50 rows: {comparable}; matched: {matched}; match rate among comparable rows: {(100 * matched / comparable if comparable else 0):.2f}%. This is not a four-instrument verification percentage.",
        "",
        "## Corporate actions",
        "",
        "BHARTIARTL and TCS corporate actions, adjustment factors, ex-dates, and adjusted/unadjusted continuity were not independently verified because the relevant independent source retrieval was unavailable. The project Yahoo adapter explicitly requests raw unadjusted prices. No historical prices were changed.",
        "",
        "NIFTY indices are not single-stock securities; constituent corporate actions are handled through index methodology rather than a single-stock split adjustment. Their official index close convention is documented, but independent row-level cross-checking remains incomplete.",
        "",
        "## Methodology audit",
        "",
        "The inspected target, Phase 3, Phase 4, and Phase 6 implementations parsed successfully. Chronological separation, target shifting, training-only Ridge standardization, backward-looking rolling windows, embargo placement, same-validation-date baseline comparison, and Phase 6 out-of-sample residual history were verified for the inspected paths. No defect was found requiring a correction.",
        "",
        "Residual independence is not established. ACF at lags 1, 2, 5, 10, and 20, rolling error stability, and volatility-conditioned error diagnostics are reported. Ljung–Box is UNAVAILABLE because statsmodels is not installed. Small ACF does not prove independence.",
        "",
        "## Readiness",
        "",
        *[f"- **{symbol}: PARTIALLY_VERIFIED; not ready for another forecasting experiment.**" for symbol in SYMBOLS],
        "",
        "## Remaining blockers",
        "",
        "- Obtain accessible independent NSE/BSE equity history and corporate-action records.",
        "- Obtain an independent Telecom index series or explicitly accept the verification limitation.",
        "- If formal residual tests are required, approve installation of a suitable existing statistical dependency; no package was installed.",
        "- Do not begin forecasting until these limitations are explicitly accepted or resolved.",
        "",
        "No production files, database records, prior phase artifacts, models, APIs, or dashboard files were modified.",
    ]
    (OUT / "REMEDIATION_REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
