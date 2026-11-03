# Phase 2 Regression Forecasting Research

Return-target walk-forward research only. No production model artifacts, dashboard code, or database records were changed.

## Acceptance policy

A model is accepted only if it beats the previous-close baseline on both MAE and RMSE in every validation fold. Models failing that gate remain rejected.

## Summary

| Instrument | XGBoost MAE | LightGBM MAE | Previous-close MAE | Best candidate |
|---|---:|---:|---:|---|
| BHARTIARTL | 13.3334 | 12.7429 | 12.2511 | NONE (rejected) |
| TCS | 35.2739 | 35.1748 | 33.8327 | NONE (rejected) |
| NIFTY_50 | 133.2188 | 134.6528 | 131.0567 | NONE (rejected) |
| NIFTY_TELECOMMUNICATIONS | 26.2252 | 26.0905 | 25.7914 | NONE (rejected) |

## Fold details

### BHARTIARTL

**xgboost** — beats previous-close on every fold: `False`; beats all baselines on every fold: `False`.

| Fold | Regime | Model MAE | Model RMSE | Model MAPE | Directional accuracy | Previous-close MAE |
|---:|---|---:|---:|---:|---:|---:|
| 1 | positive_return_regime, normal_volatility | 8.0153 | 10.8982 | 1.3291% | 0.5464 | 7.7886 |
| 2 | positive_return_regime, normal_volatility | 8.0711 | 10.4774 | 1.0942% | 0.4880 | 7.9682 |
| 3 | positive_return_regime, normal_volatility | 9.7001 | 14.1207 | 0.9204% | 0.5258 | 9.5907 |
| 4 | positive_return_regime, normal_volatility | 21.7019 | 27.5656 | 1.2951% | 0.5120 | 17.1153 |
| 5 | positive_return_regime, normal_volatility | 19.1788 | 25.0129 | 1.0002% | 0.5051 | 18.7925 |

Residual mean range: `-2.4528` to `7.3311`.
Top gain features: candle_lower_wick_ratio, annualized_volatility_5d, bb_upper, macd_histogram, ema_10.

**lightgbm** — beats previous-close on every fold: `False`; beats all baselines on every fold: `False`.

| Fold | Regime | Model MAE | Model RMSE | Model MAPE | Directional accuracy | Previous-close MAE |
|---:|---|---:|---:|---:|---:|---:|
| 1 | positive_return_regime, normal_volatility | 8.0469 | 10.8908 | 1.3339% | 0.5601 | 7.7886 |
| 2 | positive_return_regime, normal_volatility | 8.0467 | 10.4400 | 1.0911% | 0.5189 | 7.9682 |
| 3 | positive_return_regime, normal_volatility | 9.7149 | 14.2260 | 0.9217% | 0.5223 | 9.5907 |
| 4 | positive_return_regime, normal_volatility | 18.5802 | 24.4124 | 1.1079% | 0.5189 | 17.1153 |
| 5 | positive_return_regime, normal_volatility | 19.3260 | 25.1134 | 1.0084% | 0.4847 | 18.7925 |

Residual mean range: `-1.5510` to `6.1329`.
Top gain features: rolling_volatility_5d, bb_upper, atr_14, candle_lower_wick, candle_upper_wick.

### TCS

**xgboost** — beats previous-close on every fold: `False`; beats all baselines on every fold: `False`.

| Fold | Regime | Model MAE | Model RMSE | Model MAPE | Directional accuracy | Previous-close MAE |
|---:|---|---:|---:|---:|---:|---:|
| 1 | positive_return_regime, normal_volatility | 34.6364 | 47.5349 | 1.0287% | 0.5361 | 33.3229 |
| 2 | negative_return_regime, normal_volatility | 34.9141 | 47.8993 | 1.0477% | 0.5052 | 34.9749 |
| 3 | positive_return_regime, normal_volatility | 33.3252 | 44.4910 | 0.9130% | 0.4880 | 32.4746 |
| 4 | negative_return_regime, normal_volatility | 40.0034 | 55.5301 | 1.0426% | 0.4502 | 35.6533 |
| 5 | negative_return_regime, high_volatility | 33.4902 | 45.9395 | 1.3027% | 0.4373 | 32.7380 |

Residual mean range: `-0.6592` to `8.7974`.
Top gain features: ema_10, bb_lower, candle_body_return_pct, bb_upper, ema_5.

**lightgbm** — beats previous-close on every fold: `False`; beats all baselines on every fold: `False`.

| Fold | Regime | Model MAE | Model RMSE | Model MAPE | Directional accuracy | Previous-close MAE |
|---:|---|---:|---:|---:|---:|---:|
| 1 | positive_return_regime, normal_volatility | 35.2261 | 48.3805 | 1.0491% | 0.5189 | 33.3229 |
| 2 | negative_return_regime, normal_volatility | 35.4117 | 48.1140 | 1.0630% | 0.5292 | 34.9749 |
| 3 | positive_return_regime, normal_volatility | 33.1820 | 44.4148 | 0.9099% | 0.4983 | 32.4746 |
| 4 | negative_return_regime, normal_volatility | 38.7340 | 54.5618 | 1.0092% | 0.4708 | 35.6533 |
| 5 | negative_return_regime, high_volatility | 33.3200 | 46.3266 | 1.2961% | 0.4983 | 32.7380 |

Residual mean range: `-1.0074` to `7.7478`.
Top gain features: rolling_volatility_5d, volume, bb_lower, atr_14, sma_5.

### NIFTY_50

**xgboost** — beats previous-close on every fold: `False`; beats all baselines on every fold: `False`.

| Fold | Regime | Model MAE | Model RMSE | Model MAPE | Directional accuracy | Previous-close MAE |
|---:|---|---:|---:|---:|---:|---:|
| 1 | positive_return_regime, normal_volatility | 117.8137 | 155.6290 | 0.7431% | 0.5529 | 118.4746 |
| 2 | positive_return_regime, normal_volatility | 137.8277 | 178.2629 | 0.8078% | 0.4505 | 130.3493 |
| 3 | positive_return_regime, normal_volatility | 109.8125 | 163.3023 | 0.5278% | 0.5666 | 111.3430 |
| 4 | positive_return_regime, normal_volatility | 147.8155 | 198.9866 | 0.6116% | 0.5154 | 144.1686 |
| 5 | negative_return_regime, normal_volatility | 152.8247 | 211.9301 | 0.6319% | 0.4983 | 150.9481 |

Residual mean range: `-9.2402` to `27.9557`.
Top gain features: bb_bandwidth, candle_body_ratio, sma_10, bb_upper, bb_percent_b.

**lightgbm** — beats previous-close on every fold: `False`; beats all baselines on every fold: `False`.

| Fold | Regime | Model MAE | Model RMSE | Model MAPE | Directional accuracy | Previous-close MAE |
|---:|---|---:|---:|---:|---:|---:|
| 1 | positive_return_regime, normal_volatility | 119.8866 | 161.0559 | 0.7559% | 0.5700 | 118.4746 |
| 2 | positive_return_regime, normal_volatility | 138.1387 | 178.1403 | 0.8100% | 0.4573 | 130.3493 |
| 3 | positive_return_regime, normal_volatility | 111.4339 | 165.4789 | 0.5353% | 0.5495 | 111.3430 |
| 4 | positive_return_regime, normal_volatility | 150.3459 | 199.0645 | 0.6222% | 0.5631 | 144.1686 |
| 5 | negative_return_regime, normal_volatility | 153.4587 | 211.4136 | 0.6346% | 0.5119 | 150.9481 |

Residual mean range: `-14.2083` to `26.0405`.
Top gain features: high, bb_bandwidth, daily_return, roc_10, rolling_return_5d.

### NIFTY_TELECOMMUNICATIONS

**xgboost** — beats previous-close on every fold: `False`; beats all baselines on every fold: `False`.

| Fold | Regime | Model MAE | Model RMSE | Model MAPE | Directional accuracy | Previous-close MAE |
|---:|---|---:|---:|---:|---:|---:|
| 1 | positive_return_regime, normal_volatility | 21.8283 | 28.8791 | 1.1830% | 0.5085 | 21.6068 |
| 2 | negative_return_regime, normal_volatility | 19.0415 | 27.4252 | 1.0565% | 0.5154 | 18.4573 |
| 3 | positive_return_regime, normal_volatility | 25.2966 | 42.4486 | 1.0546% | 0.5188 | 24.2758 |
| 4 | negative_return_regime, normal_volatility | 32.4367 | 42.0779 | 1.1421% | 0.4949 | 31.8077 |
| 5 | positive_return_regime, normal_volatility | 32.5227 | 41.9491 | 1.0068% | 0.5768 | 32.8096 |

Residual mean range: `-5.1778` to `4.7725`.
Top gain features: annualized_volatility_5d, ema_10, sma_5, bb_bandwidth, rolling_volatility_5d.

**lightgbm** — beats previous-close on every fold: `False`; beats all baselines on every fold: `False`.

| Fold | Regime | Model MAE | Model RMSE | Model MAPE | Directional accuracy | Previous-close MAE |
|---:|---|---:|---:|---:|---:|---:|
| 1 | positive_return_regime, normal_volatility | 22.4533 | 29.3743 | 1.2179% | 0.4846 | 21.6068 |
| 2 | negative_return_regime, normal_volatility | 18.4930 | 26.3463 | 1.0265% | 0.5427 | 18.4573 |
| 3 | positive_return_regime, normal_volatility | 24.6754 | 39.6952 | 1.0342% | 0.5188 | 24.2758 |
| 4 | negative_return_regime, normal_volatility | 32.0863 | 41.7265 | 1.1310% | 0.5392 | 31.8077 |
| 5 | positive_return_regime, normal_volatility | 32.7443 | 41.8672 | 1.0135% | 0.5154 | 32.8096 |

Residual mean range: `-4.1796` to `5.2279`.
Top gain features: rolling_volatility_5d, daily_return, roc_10, macd_histogram, bb_lower.

## Recommendation

Do not integrate a numerical forecast into production unless a candidate consistently beats the previous-close baseline under this gate and passes a separate production-readiness review.
