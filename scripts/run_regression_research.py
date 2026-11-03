"""Run isolated Phase 2 regression research for all supported instruments."""

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
from app.training.regression_research import evaluate_regression_research


OUTPUT = ROOT / "research" / "regression_phase2"
SYMBOLS = ["BHARTIARTL", "TCS", "NIFTY_50", "NIFTY_TELECOMMUNICATIONS"]


def _best_candidate(result: dict) -> str:
    candidates = [
        name for name, value in result["models"].items()
        if value["beats_previous_close_all_folds"]
    ]
    if not candidates:
        return "NONE (rejected)"
    return min(candidates, key=lambda name: result["models"][name]["mean_metrics"][name]["mae"])


def _report(results: list[dict]) -> str:
    lines = [
        "# Phase 2 Regression Forecasting Research",
        "",
        "Return-target walk-forward research only. No production model artifacts, dashboard code, or database records were changed.",
        "",
        "## Acceptance policy",
        "",
        "A model is accepted only if it beats the previous-close baseline on both MAE and RMSE in every validation fold. Models failing that gate remain rejected.",
        "",
        "## Summary",
        "",
        "| Instrument | XGBoost MAE | LightGBM MAE | Previous-close MAE | Best candidate |",
        "|---|---:|---:|---:|---|",
    ]
    for result in results:
        models = result["models"]
        lines.append(
            f"| {result['symbol']} | "
            f"{models['xgboost']['mean_metrics']['xgboost']['mae']:.4f} | "
            f"{models['lightgbm']['mean_metrics']['lightgbm']['mae']:.4f} | "
            f"{models['xgboost']['mean_metrics']['previous_close']['mae']:.4f} | "
            f"{_best_candidate(result)} |"
        )
    lines.extend(["", "## Fold details", ""])
    for result in results:
        lines.extend([f"### {result['symbol']}", ""])
        for model_name, model in result["models"].items():
            lines.append(
                f"**{model_name}** — beats previous-close on every fold: "
                f"`{model['beats_previous_close_all_folds']}`; "
                f"beats all baselines on every fold: `{model['beats_any_baseline_all_folds']}`."
            )
            lines.append("")
            lines.append("| Fold | Regime | Model MAE | Model RMSE | Model MAPE | Directional accuracy | Previous-close MAE |")
            lines.append("|---:|---|---:|---:|---:|---:|---:|")
            for fold in model["folds"]:
                own = fold["metrics"][model_name]
                previous = fold["metrics"]["previous_close"]
                lines.append(
                    f"| {fold['fold']} | {fold['regime']} | {own['mae']:.4f} | {own['rmse']:.4f} | "
                    f"{own['mape']:.4f}% | {own['directional_accuracy']:.4f} | {previous['mae']:.4f} |"
                )
            residuals = [fold["residual_mean"] for fold in model["folds"]]
            importance = {}
            for fold in model["folds"]:
                for name, value in fold["feature_importance"].items():
                    importance[name] = importance.get(name, 0.0) + value
            top_features = sorted(importance.items(), key=lambda item: item[1], reverse=True)[:5]
            lines.extend([
                "",
                f"Residual mean range: `{min(residuals):.4f}` to `{max(residuals):.4f}`.",
                f"Top gain features: {', '.join(name for name, _ in top_features) or 'none'}.",
                "",
            ])
    lines.extend([
        "## Recommendation",
        "",
        "Do not integrate a numerical forecast into production unless a candidate consistently beats the previous-close baseline under this gate and passes a separate production-readiness review.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    end = datetime.now(timezone.utc)
    results = []
    for symbol in SYMBOLS:
        provider = NiftyIndicesProvider() if is_index(symbol) else YFinanceProvider()
        pipeline = run_market_data_pipeline(
            symbol=symbol,
            start_date=end - timedelta(days=3650),
            end_date=end,
            provider=provider,
        )
        dataset = assemble_feature_matrix(
            pipeline,
            feature_columns=INDEX_FEATURE_COLUMNS if symbol == "NIFTY_TELECOMMUNICATIONS" else None,
        )
        results.append(evaluate_regression_research(dataset))

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "research_scope": "isolated_phase_2_return_regression",
        "results": results,
    }
    (OUTPUT / "results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (OUTPUT / "REPORT.md").write_text(_report(results), encoding="utf-8")
    print(json.dumps({
        "output": str(OUTPUT),
        "instruments": [result["symbol"] for result in results],
        "best_candidates": {result["symbol"]: _best_candidate(result) for result in results},
    }, indent=2))


if __name__ == "__main__":
    main()
