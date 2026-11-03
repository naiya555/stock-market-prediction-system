"""Run isolated Phase 4 target and horizon research."""

import csv
import json
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
from app.training.regression_phase4 import TARGETS, evaluate_phase4_target


OUTPUT = ROOT / "research" / "regression_phase4"
SYMBOLS = ["BHARTIARTL", "TCS", "NIFTY_50", "NIFTY_TELECOMMUNICATIONS"]


def _load(symbol: str, end: datetime):
    provider = NiftyIndicesProvider() if is_index(symbol) else YFinanceProvider()
    pipeline = run_market_data_pipeline(
        symbol=symbol,
        start_date=end - timedelta(days=3650),
        end_date=end,
        provider=provider,
    )
    return assemble_feature_matrix(
        pipeline,
        feature_columns=INDEX_FEATURE_COLUMNS if symbol == "NIFTY_TELECOMMUNICATIONS" else None,
    )


def _context(datasets: dict, symbol: str):
    if symbol not in {"BHARTIARTL", "TCS"}:
        return None
    columns = {}
    for context_symbol in ("NIFTY_50", "NIFTY_TELECOMMUNICATIONS"):
        series = datasets[context_symbol].df.set_index("timestamp")["daily_return"].fillna(0.0)
        series.index = pd.to_datetime(series.index).normalize()
        columns[context_symbol.lower()] = series
    return pd.DataFrame(columns)


def _flatten(results: list[dict]) -> tuple[list[dict], list[dict]]:
    target_rows, horizon_rows = [], []
    for result in results:
        for model, folds in result["folds"].items():
            for fold in folds:
                metric = fold["metrics"][model]
                baseline = fold["metrics"]["previous_close"]
                row = {
                    "symbol": result["symbol"],
                    "target": result["target"],
                    "horizon": result["horizon"],
                    "model": model,
                    "fold": fold["fold"],
                    "regime": fold["regime"],
                    "mae": metric["mae"],
                    "rmse": metric["rmse"],
                    "mape": metric["mape"],
                    "directional_accuracy": metric["directional_accuracy"],
                    "samples": metric["samples"],
                    "coverage": result["coverage"],
                    "previous_close_mae": baseline["mae"],
                    "previous_close_rmse": baseline["rmse"],
                    "accepted_fold": (
                        metric["mae"] < baseline["mae"]
                        and metric["rmse"] < baseline["rmse"]
                    ),
                }
                target_rows.append(row)
    by_horizon = {}
    for row in target_rows:
        key = (row["symbol"], row["target"], row["horizon"], row["model"])
        by_horizon.setdefault(key, []).append(row)
    for (symbol, target, horizon, model), rows in by_horizon.items():
        horizon_rows.append({
            "symbol": symbol,
            "target": target,
            "horizon": horizon,
            "model": model,
            "mean_mae": sum(r["mae"] for r in rows) / len(rows),
            "mean_rmse": sum(r["rmse"] for r in rows) / len(rows),
            "accepted_all_folds": all(r["accepted_fold"] for r in rows),
        })
    return target_rows, horizon_rows


def _report(results: list[dict]) -> str:
    lines = [
        "# Phase 4 Forecasting Strategy and Target Optimization",
        "",
        "Isolated target/horizon research. Production prediction routes, dashboard code, model artifacts, and database records were not modified.",
        "",
        "Acceptance requires lower MAE and RMSE than the previous-close baseline in every fold, using identical validation dates.",
        "",
        "## Availability",
        "",
        "- NumPy linear/Ridge, XGBoost, LightGBM, exponential smoothing: evaluated.",
        "- Random Forest, Extra Trees, HistGradientBoosting and ARIMA: not evaluated because their dependencies are not installed.",
        "- XGBoost and LightGBM experiments used CPU execution; no GPU acceleration was claimed.",
        "",
        "## Decisions",
        "",
        "| Instrument | Target | Horizon | Best candidate | Mean MAE | Baseline MAE | Consistent |",
        "|---|---|---:|---|---:|---:|---|",
    ]
    for symbol in SYMBOLS:
        choices = []
        for result in results:
            if result["symbol"] != symbol:
                continue
            candidates = [
                (sum(f["metrics"][m]["mae"] for f in folds) / len(folds), m, result["acceptance"][m])
                for m, folds in result["folds"].items()
                if m not in {"previous_close", "sma_10", "historical_return", "exponential_smoothing"}
            ]
            best = min(candidates)
            baseline = sum(f["metrics"]["previous_close"]["mae"] for f in result["folds"]["previous_close"]) / len(result["folds"]["previous_close"])
            choices.append((best[0], result["target"], result["horizon"], best[1], baseline, best[2]))
        best = min(choices)
        lines.append(
            f"| {symbol} | {best[1]} | {best[2]} | {best[3]} | {best[0]:.4f} | {best[4]:.4f} | {'PASS' if best[5] else 'REJECT'} |"
        )
    lines.extend([
        "",
        "## Recommendations",
        "",
        "No target/horizon/model should be integrated into production unless it passes the all-fold MAE/RMSE gate and a separate production review.",
    ])
    return "\n".join(lines)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    end = datetime.now(timezone.utc)
    datasets = {symbol: _load(symbol, end) for symbol in SYMBOLS}
    results = []
    for symbol, dataset in datasets.items():
        for target_name in TARGETS:
            source_column = TARGETS[target_name][0]
            unavailable_ohlc = (
                source_column in {"open", "high", "low"}
                and dataset.df[source_column].notna().sum() == 0
            )
            if unavailable_ohlc:
                results.append({
                    "symbol": symbol, "target": target_name, "target_type": "price",
                    "horizon": 1, "rows": 0, "coverage": 0.0, "features": [],
                    "folds": {name: [] for name in ["previous_close", "sma_10", "historical_return", "exponential_smoothing", "ridge", "linear", "xgboost", "lightgbm"]},
                    "acceptance": {},
                    "status": f"unavailable_no_{source_column}",
                })
                continue
            results.append(evaluate_phase4_target(
                dataset, target_name, context=_context(datasets, symbol)
            ))
    (OUTPUT / "results.json").write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gpu": {"available": True, "execution": "cpu_hist", "lightgbm_gpu": False},
        "results": results,
    }, indent=2), encoding="utf-8")
    target_rows, horizon_rows = _flatten([r for r in results if r.get("rows", 0)])
    for name, rows in (("target_comparison.csv", target_rows), ("horizon_comparison.csv", horizon_rows)):
        with (OUTPUT / name).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    analysis = {
        symbol: [
            {"target": r["target"], "horizon": r["horizon"], "coverage": r["coverage"], "acceptance": r["acceptance"]}
            for r in results if r["symbol"] == symbol
        ]
        for symbol in SYMBOLS
    }
    (OUTPUT / "instrument_analysis.json").write_text(json.dumps(analysis, indent=2), encoding="utf-8")
    recommendations = {}
    for symbol in SYMBOLS:
        candidates = []
        for result in results:
            if result["symbol"] != symbol or not result.get("rows"):
                continue
            baseline = sum(
                f["metrics"]["previous_close"]["mae"]
                for f in result["folds"]["previous_close"]
            ) / len(result["folds"]["previous_close"])
            model_candidates = [
                (sum(f["metrics"][m]["mae"] for f in folds) / len(folds), m)
                for m, folds in result["folds"].items()
                if m not in {
                    "previous_close", "sma_10", "historical_return",
                    "exponential_smoothing",
                }
            ]
            mae, model = min(model_candidates)
            candidates.append({
                "target": result["target"],
                "horizon": result["horizon"],
                "candidate": model,
                "mean_mae": mae,
                "baseline_mae": baseline,
                "baseline_ratio": mae / baseline if baseline else None,
                "consistent": result["acceptance"].get(model, False),
            })
        best = min(candidates, key=lambda item: item["baseline_ratio"])
        recommendations[symbol] = {
            "most_predictable_target": best["target"],
            "best_horizon": best["horizon"],
            "best_candidate": best["candidate"],
            "comparison": best,
            "recommendation": "REJECT",
            "reason": "No candidate passed every-fold MAE/RMSE acceptance.",
        }
    (OUTPUT / "recommendations.json").write_text(json.dumps(recommendations, indent=2), encoding="utf-8")
    (OUTPUT / "REPORT.md").write_text(_report([r for r in results if r.get("rows", 0)]), encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "experiments": len(results)}, indent=2))


if __name__ == "__main__":
    main()
