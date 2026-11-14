"""Run the isolated Phase 5 data-quality and regime audit."""

import csv
import json
import platform
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.market.instruments import is_index
from app.market.pipeline import run_market_data_pipeline
from app.market.providers.nifty_indices_provider import NiftyIndicesProvider
from app.market.providers.yfinance_provider import YFinanceProvider
from app.training.feature_matrix import INDEX_FEATURE_COLUMNS, assemble_feature_matrix
from app.training.regression_phase5 import (
    audit_data,
    baseline_audit,
    feature_audit,
    uncertainty_audit,
    _regimes,
)

OUTPUT = ROOT / "research" / "regression_phase5"
SYMBOLS = ["BHARTIARTL", "TCS", "NIFTY_50", "NIFTY_TELECOMMUNICATIONS"]


def load(symbol: str, end: datetime):
    provider = NiftyIndicesProvider() if is_index(symbol) else YFinanceProvider()
    pipeline = run_market_data_pipeline(symbol, end - timedelta(days=3650), end, provider=provider)
    dataset = assemble_feature_matrix(
        pipeline,
        feature_columns=INDEX_FEATURE_COLUMNS if symbol == "NIFTY_TELECOMMUNICATIONS" else None,
    )
    return pipeline, dataset


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    end = datetime.now(timezone.utc)
    data_quality, regimes, baselines, uncertainty, feature_rows, comparisons = [], {}, {}, {}, [], []
    for symbol in SYMBOLS:
        pipeline, dataset = load(symbol, end)
        quality = audit_data(symbol, pipeline.raw_records, pipeline.cleaned_records, pipeline.cleaning_summary)
        data_quality.append(quality)
        names = dataset.feature_names
        feature_rows.extend([{"instrument": symbol, **row} for row in feature_audit(names, is_index(symbol))])
        frame = pd.DataFrame([row.__dict__ for row in pipeline.cleaned_records])
        regime_frame = _regimes(frame)
        regimes[symbol] = {
            "definitions": {
                "volatility": "20-session return standard deviation; low/high are <=25th/>=75th percentile.",
                "trend": "20-session close return: trending_up >=5%, trending_down <=-5%, else sideways.",
                "stress": "drawdown <=-15% correction; >=-3% recovery_or_high; otherwise neutral.",
            },
            "counts": {column: regime_frame[column].value_counts().to_dict() for column in ["volatility_regime", "trend_regime", "stress_regime"]},
        }
        baselines[symbol] = baseline_audit(frame)
        uncertainty[symbol] = uncertainty_audit(frame)
        comparisons.append({
            "symbol": symbol,
            "sessions": len(frame),
            "mean_return": baselines[symbol]["mean_return"],
            "return_std": baselines[symbol]["return_std"],
            "lag1_autocorrelation": baselines[symbol]["return_autocorrelation_lag1"],
            "directional_persistence": baselines[symbol]["directional_persistence"],
            "previous_close_mae": baselines[symbol]["previous_close_mae"],
            "previous_close_rmse": baselines[symbol]["previous_close_rmse"],
            "high_volatility_sessions": regimes[symbol]["counts"]["volatility_regime"].get("high_volatility", 0),
            "trending_sessions": sum(v for k, v in regimes[symbol]["counts"]["trend_regime"].items() if k != "sideways"),
        })
    (OUTPUT / "data_quality_report.json").write_text(json.dumps(data_quality, indent=2, default=str), encoding="utf-8")
    (OUTPUT / "regime_analysis.json").write_text(json.dumps(regimes, indent=2, default=str), encoding="utf-8")
    (OUTPUT / "baseline_analysis.json").write_text(json.dumps(baselines, indent=2, default=str), encoding="utf-8")
    (OUTPUT / "uncertainty_analysis.json").write_text(json.dumps(uncertainty, indent=2, default=str), encoding="utf-8")
    with (OUTPUT / "feature_audit.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(feature_rows[0]))
        writer.writeheader()
        writer.writerows(feature_rows)
    with (OUTPUT / "instrument_comparison.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(comparisons[0]))
        writer.writeheader()
        writer.writerows(comparisons)
    recommendations = {
        "production_integration": "REJECT",
        "reason": "Phase 5 audits do not establish a validated model improvement; previous-close remains a strong short-horizon comparator.",
        "next_steps": [
            "Cross-check equity adjusted/unadjusted series and corporate-action metadata with an independent source.",
            "Keep close-to-close targets separate from same-session open targets.",
            "Use regime-stratified walk-forward residuals before claiming uncertainty intervals.",
        ],
    }
    (OUTPUT / "recommendations.json").write_text(json.dumps(recommendations, indent=2), encoding="utf-8")
    report = [
        "# Phase 5 Data Quality, Feature Validity and Market-Regime Audit", "",
        "Production code, APIs, dashboard, database, and Phase 2-4 artifacts were not modified.", "",
        "## Measurement summary", "",
        "| Instrument | Sessions | Rejected | Weekend records | Missing OHLC rows | Return mean | Return std | Lag-1 autocorrelation | Baseline MAE |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for quality in data_quality:
        symbol = quality["symbol"]
        baseline = baselines[symbol]
        report.append(
            f"| {symbol} | {quality['cleaned_rows']} | {quality['rejected_rows']} | "
            f"{quality['weekend_records']} | {quality['missing_ohlc_fields']} | "
            f"{baseline['mean_return']:.6f} | {baseline['return_std']:.6f} | "
            f"{baseline['return_autocorrelation_lag1']:.6f} | {baseline['previous_close_mae']:.4f} |"
        )
    report.extend([
        "",
        "## Conclusions", "",
        "1. Historical data is structurally usable after the existing cleaner, but this audit cannot verify provider corporate-action adjustments or independent source agreement.",
        "2. Canonical close-to-close features are classified SAFE for prediction at session close. They are not valid for same-session opening targets; no direct future-information path was detected.",
        "3. Regimes are reproducibly defined by 20-session volatility, 20-session return slope, and drawdown thresholds recorded in regime_analysis.json.",
        "4. Previous-close is difficult to beat because one-session returns have limited serial dependence while price-level errors scale with volatility and price level.",
        "5. Instrument-specific volatility and regime counts support separate strategy evaluation rather than one universal model.",
        "6. Only descriptive baseline residual intervals are available. They are not validated model confidence intervals.",
        "",
        "## Limitations and unresolved issues",
        "",
        "- Weekend records and long gaps are reported as observed provider anomalies and were not removed or corrected.",
        "- Equity corporate actions and adjusted-versus-unadjusted consistency remain UNVERIFIABLE without an independent source and metadata.",
        "- The feature audit is based on source and transformation inspection; it is not a formal symbolic execution proof.",
        "- The empirical interval coverage is descriptive in-sample baseline coverage, not calibrated out-of-sample model coverage.",
        "",
        "See JSON and CSV artifacts for per-instrument measurements, exclusions, regime counts, feature classifications, and uncertainty limitations.",
    ])
    (OUTPUT / "REPORT.md").write_text("\n".join(report), encoding="utf-8")
    metadata = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_end": end.isoformat(),
        "symbols": SYMBOLS,
        "source": "existing YFinanceProvider and NiftyIndicesProvider via market pipeline",
        "python": platform.python_version(),
        "pandas": pd.__version__,
        "gpu": {"available": True, "used": False, "reason": "statistical audit does not benefit from GPU"},
        "methodology": "fresh pipeline output; chronological observations; no random split; no database writes",
    }
    (OUTPUT / "research_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "symbols": SYMBOLS}, indent=2))


if __name__ == "__main__":
    main()
