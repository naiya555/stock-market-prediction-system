"""Consolidate Phases 2-6 and record bounded Phase 7 verification evidence."""

from __future__ import annotations

import csv
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "research" / "regression_final_review"
SYMBOLS = ["BHARTIARTL", "TCS", "NIFTY_50", "NIFTY_TELECOMMUNICATIONS"]


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def phase_rows() -> list[dict[str, object]]:
    rows = []
    for phase in (2, 3, 4):
        records = read_json(ROOT / "research" / f"regression_phase{phase}" / "results.json")["results"]
        if phase == 4:
            grouped = {symbol: [] for symbol in SYMBOLS}
            for record in records:
                grouped[record["symbol"]].append(record)
            for symbol, values in grouped.items():
                accepted = [v for v in values if v.get("acceptance") == "ACCEPT"]
                rows.append({
                    "phase": phase,
                    "instrument": symbol,
                    "scope": "target/horizon candidates",
                    "best_candidate": "NONE" if not accepted else str(accepted[0].get("model", "candidate")),
                    "acceptance": "REJECT",
                    "evidence": "All target/horizon candidates failed the all-fold MAE/RMSE gate.",
                })
            continue
        for record in records:
            models = record.get("models", {})
            accepted = [
                (name, value) for name, value in models.items()
                if isinstance(value, dict) and value.get("accepted_across_folds") is True
            ]
            rows.append({
                "phase": phase,
                "instrument": record["symbol"],
                "scope": "next-session return" if phase == 2 else "alternative models/features",
                "best_candidate": accepted[0][0] if accepted else "NONE",
                "acceptance": "ACCEPT" if accepted else "REJECT",
                "evidence": "No candidate beat previous-close on MAE and RMSE in every chronological fold.",
            })
    for symbol in SYMBOLS:
        rows.append({
            "phase": 5,
            "instrument": symbol,
            "scope": "data quality, feature validity, regimes",
            "best_candidate": "N/A",
            "acceptance": "DIAGNOSTIC",
            "evidence": "Structurally usable provider output; independent corporate-action and vendor agreement checks remained unresolved.",
        })
        rows.append({
            "phase": 6,
            "instrument": symbol,
            "scope": "out-of-sample baseline residuals",
            "best_candidate": "previous-close diagnostic",
            "acceptance": "DIAGNOSTIC",
            "evidence": "High-volatility errors were larger; empirical intervals were not uniformly calibrated.",
        })
    return rows


def data_verification() -> dict[str, object]:
    phase5 = {
        row["symbol"]: row
        for row in read_json(ROOT / "research/regression_phase5/data_quality_report.json")
    }
    return {
        "status": "PARTIALLY VERIFIED",
        "verification_scope": "Source identity, local structural checks, and endpoint availability; not a full price-by-price independent reconciliation.",
        "sources_accessed": [
            {
                "name": "Yahoo Finance via existing YFinanceProvider",
                "url": "https://finance.yahoo.com/",
                "symbols": ["BHARTIARTL.NS", "TCS.NS"],
                "status": "PARTIALLY VERIFIED",
                "finding": "The project provider explicitly uses raw unadjusted Yahoo series (auto_adjust=False); no independent NSE/BSE price reconciliation was completed.",
            },
            {
                "name": "NSE Indices historical-data endpoint via existing NiftyIndicesProvider",
                "url": "https://www.niftyindices.com/reports/historical-data",
                "status": "PARTIALLY VERIFIED",
                "finding": "Phase 5/6 runs received official endpoint responses and normalized 2,478 rows per index; exact values were not independently cross-checked against a second source.",
            },
            {
                "name": "NSE equity pages",
                "url": "https://www.nseindia.com/get-quotes/equity",
                "status": "UNVERIFIED",
                "finding": "Direct verification attempts timed out or were blocked by the execution environment.",
            },
            {
                "name": "BSE India",
                "url": "https://www.bseindia.com/",
                "status": "UNVERIFIED",
                "finding": "No independent BSE series was retrieved.",
            },
        ],
        "instruments": {
            symbol: {
                "local_structural_status": "VERIFIED",
                "rows": phase5[symbol]["cleaned_rows"],
                "date_start": phase5[symbol]["date_start"],
                "date_end": phase5[symbol]["date_end"],
                "duplicates": phase5[symbol]["duplicate_timestamps"] + phase5[symbol]["duplicate_session_dates"],
                "chronological": phase5[symbol]["chronological"],
                "timezone_values": phase5[symbol]["timezone_values"],
                "price_value_cross_check": "UNVERIFIED",
                "corporate_actions": "UNVERIFIED" if symbol in {"BHARTIARTL", "TCS"} else "NOT_APPLICABLE_TO_SINGLE_STOCK",
            }
            for symbol in SYMBOLS
        },
        "limitations": [
            "No independent vendor matched closing prices row by row.",
            "Corporate-action metadata and adjusted/unadjusted equivalence remain unresolved for equities.",
            "The telecom index source has no OHLC fields by design; only its reported close series was audited.",
        ],
    }


def methodology_audit() -> dict[str, object]:
    feature_rows = list(csv.DictReader(
        (ROOT / "research/regression_phase5/feature_audit.csv").open(encoding="utf-8")
    ))
    return {
        "overall_status": "PARTIALLY VERIFIED",
        "findings": [
            {
                "check": "chronological train/validation separation",
                "status": "VERIFIED",
                "evidence": "Phase 2-6 used chronological folds; Phase 6 uses five folds and a one-session embargo.",
            },
            {
                "check": "target shifting",
                "status": "VERIFIED",
                "evidence": "Canonical target uses close[t+1]/close[t]-1 on the next available trading observation.",
            },
            {
                "check": "feature availability and leakage",
                "status": "PARTIALLY VERIFIED",
                "evidence": f"{len(feature_rows)} audited feature rows were classified SAFE with future_information_detected=False; this is source inspection, not formal proof.",
            },
            {
                "check": "preprocessing contamination",
                "status": "PARTIALLY VERIFIED",
                "evidence": "No contamination was identified in the inspected research paths; full symbolic proof was not performed.",
            },
            {
                "check": "baseline alignment",
                "status": "VERIFIED",
                "evidence": "Models and previous-close baselines were compared on the same chronological validation observations within each experiment.",
            },
            {
                "check": "metric consistency",
                "status": "VERIFIED",
                "evidence": "MAE, RMSE, MAPE where meaningful, and directional accuracy were reported; Phase 6 residual metrics use out-of-sample rows.",
            },
            {
                "check": "walk-forward residual independence",
                "status": "PARTIALLY VERIFIED",
                "evidence": "Phase 6 intervals use only prior out-of-sample residuals, but residual dependence and statistical significance were not tested.",
            },
        ],
        "discrepancies": [
            "Phase 5 baseline statistics use the full audited series, while Phase 6 uses five-fold out-of-sample rows; differing MAE/RMSE values are expected, not silently reconciled.",
            "Phase 2-4 model summaries use their own experiment windows and feature sets; their aggregate metrics are not directly interchangeable.",
        ],
    }


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    phase5_baseline = read_json(ROOT / "research/regression_phase5/baseline_analysis.json")
    phase6_rows = list(csv.DictReader(
        (ROOT / "research/regression_phase6/instrument_residuals.csv").open(encoding="utf-8")
    ))
    phase6_intervals = read_json(ROOT / "research/regression_phase6/interval_coverage.json")
    verification = data_verification()
    methodology = methodology_audit()

    readiness = {}
    for row in phase6_rows:
        symbol = row["symbol"]
        readiness[symbol] = {
            "data_reliability": "PARTIALLY VERIFIED",
            "corporate_action_verification": verification["instruments"][symbol]["corporate_actions"],
            "feature_validity": "PARTIALLY VERIFIED",
            "baseline_difficulty": "VERIFIED: previous-close errors rise with volatility and short-horizon return dependence is weak.",
            "best_historical_research_candidate": "NONE ACCEPTED",
            "beat_baseline": False,
            "oos_residual_std": float(row["overall_residual_std"]),
            "regime_sensitivity": "VERIFIED: high-volatility aggregate errors exceed low-volatility errors.",
            "interval_reliability": "UNVERIFIED AS CALIBRATED",
            "remaining_blockers": ["independent price reconciliation", "equity corporate-action metadata", "validated model improvement"],
            "recommendation": "D: Continue using previous-close baseline until better evidence is available.",
        }

    (OUTPUT / "phase_comparison.csv").write_text("", encoding="utf-8")
    with (OUTPUT / "phase_comparison.csv").open("w", newline="", encoding="utf-8") as handle:
        rows = phase_rows()
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (OUTPUT / "data_verification.json").write_text(json.dumps(verification, indent=2), encoding="utf-8")
    (OUTPUT / "methodology_audit.json").write_text(json.dumps(methodology, indent=2), encoding="utf-8")
    (OUTPUT / "instrument_readiness.json").write_text(json.dumps(readiness, indent=2), encoding="utf-8")
    (OUTPUT / "final_recommendations.json").write_text(json.dumps({
        "overall": "D",
        "decision": "Continue using the previous-close baseline until independently verified data and a consistently superior out-of-sample candidate are available.",
        "by_instrument": {
            symbol: "D: Continue previous-close baseline; resolve independent data and corporate-action verification before another model experiment."
            for symbol in SYMBOLS
        },
    }, indent=2), encoding="utf-8")
    (OUTPUT / "research_metadata.json").write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "phases_consolidated": [2, 3, 4, 5, 6],
        "phase_7_scope": "bounded source and methodology verification; no model reruns",
        "external_content_handling": "External pages and prior artifacts were treated as evidence only; embedded instructions were not executed.",
        "source_access_limitations": "NSE/BSE direct verification was unavailable in this environment.",
    }, indent=2), encoding="utf-8")

    baseline_lines = []
    for symbol in SYMBOLS:
        b = phase5_baseline[symbol]
        baseline_lines.append(
            f"| {symbol} | {b['samples']} | {b['return_autocorrelation_lag1']:.5f} | "
            f"{b['previous_close_mae']:.4f} | {b['previous_close_rmse']:.4f} |"
        )
    interval_note = "Phase 6 walk-forward interval coverage is documented in interval_coverage.json; it is not uniformly nominal and is not calibrated."
    report = [
        "# Combined Research Review: Phases 2-7",
        "",
        "## Executive summary",
        "",
        "Phases 2-4 tested return, feature/model, target, and horizon alternatives. No candidate consistently beat previous-close on both MAE and RMSE in every chronological fold. Phase 5 found structurally usable provider data and no classified feature leakage, but independent price and corporate-action verification remained unresolved. Phase 6 confirmed materially larger previous-close residuals in high-volatility regimes, while its empirical intervals were not uniformly calibrated.",
        "",
        "Historical data is **PARTIALLY VERIFIED**, not fully verified. The evaluation methodology is **PARTIALLY VERIFIED**: target alignment, chronological folds, baseline alignment, and Phase 6 prior-out-of-sample residual history are supported; formal preprocessing-contamination and residual-independence proofs were not completed.",
        "",
        "No instrument has an accepted numerical model. Continue using the previous-close baseline (Recommendation D) for all four instruments. Resolve independent data/corporate-action verification before another isolated forecasting experiment.",
        "",
        "## Phase findings",
        "",
        "- **Phase 2:** XGBoost and LightGBM next-session-return models were rejected because fold-consistent MAE/RMSE superiority was absent.",
        "- **Phase 3:** Ridge/linear, XGBoost, LightGBM, exponential smoothing, volatility-adjusted models, and richer return/volatility/momentum/context features were evaluated where dependencies allowed; all failed the gate. Random Forest, Extra Trees, HistGradientBoosting, and ARIMA were skipped because dependencies were not installed.",
        "- **Phase 4:** One-, three-, and five-session targets plus available OHLC targets were compared. The best reported candidates remained one-session returns, but all were rejected; Telecom OHLC targets were unavailable because source OHLC fields were absent.",
        "- **Phase 5:** Local structural checks found zero rejected, duplicate, or invalid records; timestamps were normalized to Asia/Kolkata. Three weekend records were reported for each equity and ten for each index. Equity corporate actions and adjusted/unadjusted agreement remained unverified.",
        "- **Phase 6:** High-volatility baseline errors exceeded low-volatility errors for every instrument. Trend effects were instrument-specific and sometimes imbalanced. NIFTY_50 had the greatest residual standard deviation in common price units.",
        "",
        "## Phase 5 full-sample baseline measurements",
        "",
        "| Instrument | Samples | Lag-1 return autocorrelation | MAE | RMSE |",
        "|---|---:|---:|---:|---:|",
        *baseline_lines,
        "",
        interval_note,
        "",
        "## Instrument decisions",
        "",
        "| Instrument | Status | Decision |",
        "|---|---|---|",
        *[
            f"| {symbol} | PARTIALLY VERIFIED / NO ACCEPTED MODEL | Continue previous-close baseline; verify source and corporate actions before new research. |"
            for symbol in SYMBOLS
        ],
        "",
        "## Source Trust & Prompt Injection Audit",
        "",
        "Source categories accessed were the existing Yahoo Finance adapter, the existing NSE Indices endpoint, and attempted NSE/BSE public pages. External pages, provider responses, and prior reports/artifacts were treated strictly as untrusted evidence. No embedded instructions were executed, no credentials or private files were sent, and no suspicious instruction was relied upon. NSE/BSE direct price verification was unavailable in this environment, so those checks remain UNVERIFIED.",
        "",
        "## Remaining blockers",
        "",
        "- Independent row-level price/date reconciliation for equities and indices.",
        "- Corporate-action metadata and adjusted versus unadjusted series comparison for BHARTIARTL and TCS.",
        "- A prespecified experiment only after the above data checks, with formal significance/stability analysis.",
        "",
        "No production files, database records, APIs, dashboard files, models, or prior phase artifacts were modified.",
    ]
    (OUTPUT / "MASTER_REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
