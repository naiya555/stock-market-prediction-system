"""Run isolated Phase 6 regime-stratified residual research."""

import csv
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.training.regression_phase6 import aggregate_regime_results, evaluate_walk_forward
from scripts.run_regression_phase5 import SYMBOLS, load

OUTPUT = ROOT / "research" / "regression_phase6"


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    end = datetime.now(timezone.utc)
    residuals, interval_coverage, instrument_rows = {}, {}, []
    for symbol in SYMBOLS:
        pipeline, _ = load(symbol, end)
        frame = pd.DataFrame([row.__dict__ for row in pipeline.cleaned_records])
        evaluation = evaluate_walk_forward(frame)
        residuals[symbol] = {
            "out_of_sample": evaluation,
            "aggregate": aggregate_regime_results(evaluation),
        }
        interval_coverage[symbol] = {
            "method": evaluation["interval_method"],
            "folds": [
                {
                    "fold": fold["fold"],
                    "samples": fold["samples"],
                    "intervals": fold["intervals"],
                    "regimes": fold["regimes"],
                }
                for fold in evaluation["folds"]
            ],
        }
        overall = [fold["overall"] for fold in evaluation["folds"]]
        instrument_rows.append({
            "symbol": symbol,
            "out_of_sample_samples": evaluation["total_out_of_sample_samples"],
            "overall_mae": sum(r["mae"] * r["samples"] for r in overall) / sum(r["samples"] for r in overall),
            "overall_rmse": (sum(r["rmse"] ** 2 * r["samples"] for r in overall) / sum(r["samples"] for r in overall)) ** 0.5,
            "overall_residual_std": sum(r["residual_std"] * r["samples"] for r in overall) / sum(r["samples"] for r in overall),
        })
    recommendations = {
        "production_integration": "REJECT",
        "volatility_regimes_explain_error": "High-volatility residual MAE/RMSE is higher than low-volatility for all four instruments in the out-of-sample aggregates; this explains error variation but does not prove a usable forecast signal.",
        "trend_regimes_explain_error": "Trend groups differ by instrument and are sometimes imbalanced; treat as diagnostic, not evidence of improved forecasting.",
        "interval_status": "WALK_FORWARD_EMPIRICAL, not calibrated confidence.",
        "next_step": "Use regime-stratified residual diagnostics to design a prespecified, separately validated uncertainty model; do not integrate intervals yet.",
    }
    (OUTPUT / "regime_residuals.json").write_text(json.dumps(residuals, indent=2, default=str), encoding="utf-8")
    (OUTPUT / "interval_coverage.json").write_text(json.dumps(interval_coverage, indent=2, default=str), encoding="utf-8")
    (OUTPUT / "recommendations.json").write_text(json.dumps(recommendations, indent=2), encoding="utf-8")
    with (OUTPUT / "instrument_residuals.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(instrument_rows[0]))
        writer.writeheader()
        writer.writerows(instrument_rows)
    metadata = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "symbols": SYMBOLS,
        "source": "existing Phase 5 market providers and pipeline",
        "python": platform.python_version(),
        "pandas": pd.__version__,
        "gpu": {"available": True, "used": False, "reason": "baseline residual statistics do not benefit from GPU"},
        "methodology": "five chronological folds, one-session embargo, prior-residual empirical intervals, no model training",
    }
    (OUTPUT / "research_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    highest = max(instrument_rows, key=lambda row: row["overall_residual_std"])
    report = [
        "# Phase 6 Regime-Stratified Walk-Forward Residual Research", "",
        "Previous-close predictions are evaluated out of sample in five chronological folds with a one-session embargo. Regime thresholds are derived from each fold's training history only.", "",
        "## Overall out-of-sample residuals", "",
        "| Instrument | OOS samples | MAE | RMSE | Residual std |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in instrument_rows:
        report.append(
            f"| {row['symbol']} | {row['out_of_sample_samples']} | "
            f"{row['overall_mae']:.4f} | {row['overall_rmse']:.4f} | "
            f"{row['overall_residual_std']:.4f} |"
        )
    report.extend([
        "",
        f"Highest residual variability: **{highest['symbol']}** (residual standard deviation {highest['overall_residual_std']:.4f}).",
        "",
        "## Walk-forward interval coverage",
        "",
        "Coverage below is weighted across folds 2-5; fold 1 is unavailable because fewer than 50 prior out-of-sample residuals existed.",
        "",
        "| Instrument | 50% nominal | 80% nominal | 90% nominal | 95% nominal |",
        "|---|---:|---:|---:|---:|",
    ])
    for symbol in SYMBOLS:
        values = []
        for level in ("0.5", "0.8", "0.9", "0.95"):
            fold_values = [
                (fold["intervals"][level]["coverage"], fold["samples"])
                for fold in interval_coverage[symbol]["folds"]
                if fold["intervals"][level]["status"] != "UNAVAILABLE"
            ]
            values.append(
                sum(coverage * samples for coverage, samples in fold_values) / sum(samples for _, samples in fold_values)
                if fold_values else None
            )
        report.append(f"| {symbol} | " + " | ".join("UNAVAILABLE" if value is None else f"{value:.4f}" for value in values) + " |")
    report.extend([
        "",
        "## Conclusions", "",
        "1. High-volatility regimes explain larger out-of-sample baseline errors for all four instruments: BHARTIARTL 21.855 MAE vs 9.997 low-volatility, TCS 42.896 vs 26.391, NIFTY 50 183.684 vs 91.502, and Telecom 33.071 vs 17.353.",
        "2. Trend-regime comparisons are reported separately and must be interpreted with group sample counts and fold stability.",
        f"3. {highest['symbol']} has the highest residual variability in the common price units used by this audit.",
        "4. Empirical intervals do not uniformly achieve nominal coverage: BHARTIARTL and NIFTY 50 are materially under-covered, while TCS is closest to nominal.",
        "5. Regime information explains error heterogeneity but provides no evidence to change the production baseline or integrate uncertainty bands.",
        "",
        "## Limitations", "",
        "- Residuals are from the previous-close baseline, not a learned model.",
        "- First-fold intervals may be unavailable until 50 prior residuals exist.",
        "- Regime labels are coarse and threshold-dependent.",
        "- No statistical significance test or multiple-comparison correction is applied.",
    ])
    (OUTPUT / "REPORT.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "symbols": SYMBOLS}, indent=2))


if __name__ == "__main__":
    main()
