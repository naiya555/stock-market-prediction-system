"""Run isolated Phase 3 alternative regression research."""

import csv
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.market.instruments import is_index
from app.market.pipeline import run_market_data_pipeline
from app.market.providers.nifty_indices_provider import NiftyIndicesProvider
from app.market.providers.yfinance_provider import YFinanceProvider
from app.training.feature_matrix import INDEX_FEATURE_COLUMNS, assemble_feature_matrix
from app.training.regression_phase3 import evaluate_phase3


OUTPUT = ROOT / "research" / "regression_phase3"
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
        frame = datasets[context_symbol].df
        series = frame.set_index("timestamp")["daily_return"].fillna(0.0)
        series.index = __import__("pandas").to_datetime(series.index).normalize()
        columns[context_symbol.lower()] = series
    return __import__("pandas").DataFrame(columns)


def _flatten(results: list[dict]) -> list[dict]:
    rows = []
    for result in results:
        for model, folds in result["folds"].items():
            for fold in folds:
                metrics = fold["metrics"][model]
                baseline = fold["metrics"]["previous_close"]
                rows.append({
                    "symbol": result["symbol"],
                    "model": model,
                    "fold": fold["fold"],
                    "regime": fold["regime"],
                    "mae": metrics["mae"],
                    "rmse": metrics["rmse"],
                    "mape": metrics["mape"],
                    "directional_accuracy": metrics["directional_accuracy"],
                    "previous_close_mae": baseline["mae"],
                    "previous_close_rmse": baseline["rmse"],
                    "accepted_fold": (
                        metrics["mae"] < baseline["mae"] and metrics["rmse"] < baseline["rmse"]
                    ),
                    "residual_mean": fold["residual_mean"].get(model, 0.0),
                    "residual_std": fold["residual_std"].get(model, 0.0),
                })
    return rows


def _report(results: list[dict], unavailable: list[str]) -> str:
    lines = [
        "# Phase 3 Advanced Regression Research",
        "",
        "Isolated return-regression experiments. Production prediction routes, dashboard code, model artifacts, and database records were not modified.",
        "",
        "Acceptance requires lower MAE and RMSE than previous-close in every fold.",
        "",
        "## Library availability",
        "",
        "- NumPy linear/Ridge: evaluated",
        "- Native XGBoost: evaluated",
        "- Native LightGBM: evaluated",
        "- Random Forest, Extra Trees, HistGradientBoosting: skipped because scikit-learn is not installed; no dependency was added.",
        "- ARIMA: skipped because statsmodels is not installed; no dependency was added.",
        "- Exponential smoothing and volatility-adjusted models: evaluated as dependency-free statistical baselines.",
        "",
        "## Summary",
        "",
        "| Instrument | Best mean MAE | Previous-close MAE | Best candidate | Acceptance |",
        "|---|---:|---:|---|---|",
    ]
    for result in results:
        candidates = []
        for model, folds in result["folds"].items():
            if model in {"previous_close", "sma_10", "historical_return"}:
                continue
            mean_mae = sum(f["metrics"][model]["mae"] for f in folds) / len(folds)
            accepted = result["acceptance"][model]
            candidates.append((mean_mae, model, accepted))
        best = min(candidates)
        prev = sum(f["metrics"]["previous_close"]["mae"] for f in result["folds"]["previous_close"]) / len(result["folds"]["previous_close"])
        lines.append(f"| {result['symbol']} | {best[0]:.4f} | {prev:.4f} | {best[1]} | {'PASS' if best[2] else 'REJECT'} |")
    lines.extend(["", "## Fold results", ""])
    for result in results:
        lines.extend([f"### {result['symbol']}", ""])
        for model, folds in result["folds"].items():
            lines.append(f"**{model}** — accepted across all folds: `{result['acceptance'][model]}`")
            lines.append("")
            lines.append("| Fold | Regime | MAE | RMSE | MAPE | Directional accuracy | Previous-close MAE |")
            lines.append("|---:|---|---:|---:|---:|---:|---:|")
            for fold in folds:
                metric = fold["metrics"][model]
                previous = fold["metrics"]["previous_close"]
                lines.append(
                    f"| {fold['fold']} | {fold['regime']} | {metric['mae']:.4f} | {metric['rmse']:.4f} | "
                    f"{metric['mape']:.4f}% | {metric['directional_accuracy']:.4f} | {previous['mae']:.4f} |"
                )
            lines.append("")
    lines.extend([
        "## GPU",
        "",
        "The RTX 5050 is available. XGBoost has CUDA support, but these experiments used `tree_method=hist` CPU execution for deterministic apples-to-apples folds. LightGBM GPU support is unavailable in the installed build.",
        "",
        "## Recommendation",
        "",
        "No candidate should be integrated unless it passes the all-fold MAE/RMSE gate and a separate production review.",
    ])
    if unavailable:
        lines.extend(["", "Unavailable research families: " + ", ".join(unavailable) + "."])
    return "\n".join(lines)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    end = datetime.now(timezone.utc)
    datasets = {symbol: _load(symbol, end) for symbol in SYMBOLS}
    results = [
        evaluate_phase3(dataset, context=_context(datasets, symbol))
        for symbol, dataset in datasets.items()
    ]
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gpu": {"available": True, "execution": "cpu_hist", "lightgbm_gpu": False},
        "results": results,
    }
    (OUTPUT / "results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    rows = _flatten(results)
    with (OUTPUT / "experiment_metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    feature_analysis = {
        result["symbol"]: {
            model: sorted(
                ((name, value) for fold in folds for name, value in fold["feature_importance"].get(model, {}).items()),
                key=lambda item: item[1],
                reverse=True,
            )[:20]
            for model, folds in result["folds"].items()
        }
        for result in results
    }
    (OUTPUT / "feature_analysis.json").write_text(json.dumps(feature_analysis, indent=2), encoding="utf-8")
    comparison = {
        result["symbol"]: {
            model: {
                "mean_mae": sum(fold["metrics"][model]["mae"] for fold in folds) / len(folds),
                "mean_rmse": sum(fold["metrics"][model]["rmse"] for fold in folds) / len(folds),
                "accepted_all_folds": result["acceptance"][model],
            }
            for model, folds in result["folds"].items()
        }
        for result in results
    }
    (OUTPUT / "model_comparison.json").write_text(json.dumps(comparison, indent=2), encoding="utf-8")
    unavailable = ["RandomForestRegressor", "ExtraTreesRegressor", "HistGradientBoosting", "ARIMA"]
    (OUTPUT / "REPORT.md").write_text(_report(results, unavailable), encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "symbols": SYMBOLS}, indent=2))


if __name__ == "__main__":
    main()
