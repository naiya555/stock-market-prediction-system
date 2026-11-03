# Phase 3 Advanced Regression Research

Isolated return-regression experiments. Production prediction routes, dashboard code, model artifacts, and database records were not modified.

Acceptance requires lower MAE and RMSE than previous-close in every fold.

## Library availability

- NumPy linear/Ridge: evaluated
- Native XGBoost: evaluated
- Native LightGBM: evaluated
- Random Forest, Extra Trees, HistGradientBoosting: skipped because scikit-learn is not installed; no dependency was added.
- ARIMA: skipped because statsmodels is not installed; no dependency was added.
- Exponential smoothing and volatility-adjusted models: evaluated as dependency-free statistical baselines.

## Summary

| Instrument | Best mean MAE | Previous-close MAE | Best candidate | Acceptance |
|---|---:|---:|---|---|
| BHARTIARTL | 12.3675 | 12.3092 | volatility_adjusted | REJECT |
| TCS | 34.2126 | 33.8972 | volatility_adjusted | REJECT |
| NIFTY_50 | 132.9011 | 131.2808 | volatility_adjusted | REJECT |
| NIFTY_TELECOMMUNICATIONS | 26.2236 | 25.8409 | ridge | REJECT |

## Fold results

### BHARTIARTL

**previous_close** — accepted across all folds: `False`

| Fold | Regime | MAE | RMSE | MAPE | Directional accuracy | Previous-close MAE |
|---:|---|---:|---:|---:|---:|---:|
| 1 | normal_volatility | 8.0007 | 10.6683 | 1.3159% | 0.5017 | 8.0007 |
| 2 | normal_volatility | 7.7872 | 10.1341 | 1.0533% | 0.4879 | 7.7872 |
| 3 | normal_volatility | 9.8820 | 14.7335 | 0.9256% | 0.4567 | 9.8820 |
| 4 | normal_volatility | 16.9163 | 23.0644 | 0.9997% | 0.4706 | 16.9163 |
| 5 | normal_volatility | 18.9599 | 24.9818 | 0.9875% | 0.4966 | 18.9599 |

**sma_10** — accepted across all folds: `False`

| Fold | Regime | MAE | RMSE | MAPE | Directional accuracy | Previous-close MAE |
|---:|---|---:|---:|---:|---:|---:|
| 1 | normal_volatility | 15.0204 | 19.5190 | 2.4640% | 0.5052 | 8.0007 |
| 2 | normal_volatility | 14.1165 | 17.4778 | 1.9110% | 0.5225 | 7.7872 |
| 3 | normal_volatility | 20.5157 | 27.7263 | 1.8934% | 0.4983 | 9.8820 |
| 4 | normal_volatility | 32.9530 | 42.9499 | 1.9226% | 0.5329 | 16.9163 |
| 5 | normal_volatility | 35.2599 | 42.9578 | 1.8312% | 0.5205 | 18.9599 |

**historical_return** — accepted across all folds: `False`

| Fold | Regime | MAE | RMSE | MAPE | Directional accuracy | Previous-close MAE |
|---:|---|---:|---:|---:|---:|---:|
| 1 | normal_volatility | 8.0249 | 10.6493 | 1.3201% | 0.4983 | 8.0007 |
| 2 | normal_volatility | 7.8118 | 10.1535 | 1.0568% | 0.5121 | 7.7872 |
| 3 | normal_volatility | 9.8346 | 14.6117 | 0.9218% | 0.5433 | 9.8820 |
| 4 | normal_volatility | 16.9203 | 23.0195 | 1.0004% | 0.5294 | 16.9163 |
| 5 | normal_volatility | 19.0755 | 25.0631 | 0.9940% | 0.5034 | 18.9599 |

**ridge** — accepted across all folds: `False`

| Fold | Regime | MAE | RMSE | MAPE | Directional accuracy | Previous-close MAE |
|---:|---|---:|---:|---:|---:|---:|
| 1 | normal_volatility | 8.1773 | 11.0346 | 1.3450% | 0.4983 | 8.0007 |
| 2 | normal_volatility | 8.0873 | 10.4988 | 1.0952% | 0.4740 | 7.7872 |
| 3 | normal_volatility | 9.7028 | 14.5802 | 0.9066% | 0.5882 | 9.8820 |
| 4 | normal_volatility | 18.1142 | 24.2159 | 1.0702% | 0.5017 | 16.9163 |
| 5 | normal_volatility | 19.9534 | 25.8668 | 1.0407% | 0.5034 | 18.9599 |

**linear** — accepted across all folds: `False`

| Fold | Regime | MAE | RMSE | MAPE | Directional accuracy | Previous-close MAE |
|---:|---|---:|---:|---:|---:|---:|
| 1 | normal_volatility | 8.3067 | 11.2417 | 1.3625% | 0.4879 | 8.0007 |
| 2 | normal_volatility | 8.1841 | 10.6810 | 1.1079% | 0.5017 | 7.7872 |
| 3 | normal_volatility | 9.9014 | 14.7271 | 0.9250% | 0.5363 | 9.8820 |
| 4 | normal_volatility | 18.3318 | 24.5267 | 1.0832% | 0.4983 | 16.9163 |
| 5 | normal_volatility | 20.0656 | 26.0006 | 1.0466% | 0.5171 | 18.9599 |

**xgboost** — accepted across all folds: `False`

| Fold | Regime | MAE | RMSE | MAPE | Directional accuracy | Previous-close MAE |
|---:|---|---:|---:|---:|---:|---:|
| 1 | normal_volatility | 8.0366 | 10.9810 | 1.3198% | 0.5709 | 8.0007 |
| 2 | normal_volatility | 7.9063 | 10.2847 | 1.0688% | 0.5225 | 7.7872 |
| 3 | normal_volatility | 9.9137 | 14.4369 | 0.9283% | 0.5260 | 9.8820 |
| 4 | normal_volatility | 17.7755 | 23.6126 | 1.0534% | 0.5536 | 16.9163 |
| 5 | normal_volatility | 19.2414 | 25.1151 | 1.0042% | 0.5240 | 18.9599 |

**lightgbm** — accepted across all folds: `False`

| Fold | Regime | MAE | RMSE | MAPE | Directional accuracy | Previous-close MAE |
|---:|---|---:|---:|---:|---:|---:|
| 1 | normal_volatility | 8.0420 | 10.9873 | 1.3177% | 0.5467 | 8.0007 |
| 2 | normal_volatility | 7.9919 | 10.3775 | 1.0805% | 0.4671 | 7.7872 |
| 3 | normal_volatility | 9.8347 | 14.3233 | 0.9242% | 0.5260 | 9.8820 |
| 4 | normal_volatility | 18.3966 | 24.4325 | 1.0924% | 0.5121 | 16.9163 |
| 5 | normal_volatility | 19.4605 | 25.3298 | 1.0157% | 0.4966 | 18.9599 |

**exponential_smoothing** — accepted across all folds: `False`

| Fold | Regime | MAE | RMSE | MAPE | Directional accuracy | Previous-close MAE |
|---:|---|---:|---:|---:|---:|---:|
| 1 | normal_volatility | 8.5007 | 10.9319 | 1.3983% | 0.4983 | 8.0007 |
| 2 | normal_volatility | 7.9643 | 10.3300 | 1.0774% | 0.5121 | 7.7872 |
| 3 | normal_volatility | 9.8932 | 14.5302 | 0.9283% | 0.5433 | 9.8820 |
| 4 | normal_volatility | 16.9212 | 23.0198 | 1.0004% | 0.5294 | 16.9163 |
| 5 | normal_volatility | 19.6444 | 25.5959 | 1.0243% | 0.5034 | 18.9599 |

**volatility_adjusted** — accepted across all folds: `False`

| Fold | Regime | MAE | RMSE | MAPE | Directional accuracy | Previous-close MAE |
|---:|---|---:|---:|---:|---:|---:|
| 1 | normal_volatility | 8.3001 | 10.7849 | 1.3654% | 0.4983 | 8.0007 |
| 2 | normal_volatility | 7.7997 | 10.1420 | 1.0551% | 0.5121 | 7.7872 |
| 3 | normal_volatility | 9.8341 | 14.5949 | 0.9219% | 0.5433 | 9.8820 |
| 4 | normal_volatility | 16.9436 | 23.0304 | 1.0019% | 0.5294 | 16.9163 |
| 5 | normal_volatility | 18.9599 | 24.9818 | 0.9875% | 0.5034 | 18.9599 |

### TCS

**previous_close** — accepted across all folds: `False`

| Fold | Regime | MAE | RMSE | MAPE | Directional accuracy | Previous-close MAE |
|---:|---|---:|---:|---:|---:|---:|
| 1 | normal_volatility | 33.7332 | 45.4695 | 0.9933% | 0.4533 | 33.7332 |
| 2 | normal_volatility | 34.9434 | 47.2751 | 1.0522% | 0.5190 | 34.9434 |
| 3 | normal_volatility | 32.1176 | 43.6850 | 0.8769% | 0.4948 | 32.1176 |
| 4 | normal_volatility | 36.0943 | 52.4359 | 0.9347% | 0.5536 | 36.0943 |
| 5 | high_volatility | 32.5976 | 45.5557 | 1.2732% | 0.5514 | 32.5976 |

**sma_10** — accepted across all folds: `False`

| Fold | Regime | MAE | RMSE | MAPE | Directional accuracy | Previous-close MAE |
|---:|---|---:|---:|---:|---:|---:|
| 1 | normal_volatility | 72.1345 | 88.6518 | 2.1228% | 0.4567 | 33.7332 |
| 2 | normal_volatility | 73.2792 | 88.8711 | 2.2206% | 0.4602 | 34.9434 |
| 3 | normal_volatility | 62.6474 | 81.1717 | 1.7054% | 0.5190 | 32.1176 |
| 4 | normal_volatility | 86.2070 | 108.7144 | 2.2370% | 0.4913 | 36.0943 |
| 5 | high_volatility | 71.4057 | 92.3346 | 2.8071% | 0.5068 | 32.5976 |

**historical_return** — accepted across all folds: `False`

| Fold | Regime | MAE | RMSE | MAPE | Directional accuracy | Previous-close MAE |
|---:|---|---:|---:|---:|---:|---:|
| 1 | normal_volatility | 33.5855 | 45.3907 | 0.9898% | 0.5467 | 33.7332 |
| 2 | normal_volatility | 35.1994 | 47.6116 | 1.0604% | 0.4810 | 34.9434 |
| 3 | normal_volatility | 32.2139 | 43.6427 | 0.8797% | 0.5052 | 32.1176 |
| 4 | normal_volatility | 36.4795 | 52.6703 | 0.9457% | 0.4464 | 36.0943 |
| 5 | high_volatility | 32.7905 | 45.6744 | 1.2812% | 0.4486 | 32.5976 |

**ridge** — accepted across all folds: `False`

| Fold | Regime | MAE | RMSE | MAPE | Directional accuracy | Previous-close MAE |
|---:|---|---:|---:|---:|---:|---:|
| 1 | normal_volatility | 36.8937 | 49.7472 | 1.0821% | 0.5329 | 33.7332 |
| 2 | normal_volatility | 35.1193 | 47.9781 | 1.0586% | 0.5329 | 34.9434 |
| 3 | normal_volatility | 33.3707 | 44.6906 | 0.9123% | 0.5087 | 32.1176 |
| 4 | normal_volatility | 37.9749 | 53.9222 | 0.9888% | 0.4879 | 36.0943 |
| 5 | high_volatility | 33.9546 | 46.5586 | 1.3236% | 0.4521 | 32.5976 |

**linear** — accepted across all folds: `False`

| Fold | Regime | MAE | RMSE | MAPE | Directional accuracy | Previous-close MAE |
|---:|---|---:|---:|---:|---:|---:|
| 1 | normal_volatility | 36.1492 | 48.8912 | 1.0612% | 0.5156 | 33.7332 |
| 2 | normal_volatility | 35.3754 | 48.7281 | 1.0658% | 0.5606 | 34.9434 |
| 3 | normal_volatility | 33.3053 | 45.0076 | 0.9099% | 0.5260 | 32.1176 |
| 4 | normal_volatility | 38.6783 | 54.2788 | 1.0048% | 0.5017 | 36.0943 |
| 5 | high_volatility | 36.0260 | 52.4987 | 1.3918% | 0.4795 | 32.5976 |

**xgboost** — accepted across all folds: `False`

| Fold | Regime | MAE | RMSE | MAPE | Directional accuracy | Previous-close MAE |
|---:|---|---:|---:|---:|---:|---:|
| 1 | normal_volatility | 36.1931 | 48.9426 | 1.0669% | 0.5363 | 33.7332 |
| 2 | normal_volatility | 35.0324 | 47.7293 | 1.0561% | 0.5398 | 34.9434 |
| 3 | normal_volatility | 32.7898 | 44.6321 | 0.8946% | 0.4948 | 32.1176 |
| 4 | normal_volatility | 41.4896 | 57.2052 | 1.0929% | 0.4948 | 36.0943 |
| 5 | high_volatility | 33.3390 | 45.9595 | 1.3032% | 0.4486 | 32.5976 |

**lightgbm** — accepted across all folds: `False`

| Fold | Regime | MAE | RMSE | MAPE | Directional accuracy | Previous-close MAE |
|---:|---|---:|---:|---:|---:|---:|
| 1 | normal_volatility | 36.9822 | 50.2539 | 1.0910% | 0.5363 | 33.7332 |
| 2 | normal_volatility | 35.2650 | 48.2126 | 1.0643% | 0.5744 | 34.9434 |
| 3 | normal_volatility | 32.8570 | 44.5401 | 0.8968% | 0.5329 | 32.1176 |
| 4 | normal_volatility | 39.6030 | 55.1392 | 1.0366% | 0.4879 | 36.0943 |
| 5 | high_volatility | 33.2815 | 45.7722 | 1.3009% | 0.4829 | 32.5976 |

**exponential_smoothing** — accepted across all folds: `False`

| Fold | Regime | MAE | RMSE | MAPE | Directional accuracy | Previous-close MAE |
|---:|---|---:|---:|---:|---:|---:|
| 1 | normal_volatility | 35.2456 | 46.8900 | 1.0403% | 0.5467 | 33.7332 |
| 2 | normal_volatility | 35.6678 | 48.2011 | 1.0751% | 0.4810 | 34.9434 |
| 3 | normal_volatility | 33.7174 | 46.0395 | 0.9209% | 0.4948 | 32.1176 |
| 4 | normal_volatility | 36.6810 | 52.8232 | 0.9513% | 0.4464 | 36.0943 |
| 5 | high_volatility | 32.5695 | 45.5377 | 1.2719% | 0.5514 | 32.5976 |

**volatility_adjusted** — accepted across all folds: `False`

| Fold | Regime | MAE | RMSE | MAPE | Directional accuracy | Previous-close MAE |
|---:|---|---:|---:|---:|---:|---:|
| 1 | normal_volatility | 34.9296 | 46.6073 | 1.0308% | 0.5467 | 33.7332 |
| 2 | normal_volatility | 35.2465 | 47.4334 | 1.0601% | 0.5190 | 34.9434 |
| 3 | normal_volatility | 32.3109 | 44.0696 | 0.8820% | 0.4948 | 32.1176 |
| 4 | normal_volatility | 36.0723 | 52.4254 | 0.9341% | 0.5536 | 36.0943 |
| 5 | high_volatility | 32.5036 | 45.4871 | 1.2674% | 0.5514 | 32.5976 |

### NIFTY_50

**previous_close** — accepted across all folds: `False`

| Fold | Regime | MAE | RMSE | MAPE | Directional accuracy | Previous-close MAE |
|---:|---|---:|---:|---:|---:|---:|
| 1 | normal_volatility | 121.5098 | 160.8937 | 0.7594% | 0.4448 | 121.5098 |
| 2 | normal_volatility | 126.9912 | 166.5520 | 0.7417% | 0.5034 | 126.9912 |
| 3 | normal_volatility | 112.9614 | 167.1278 | 0.5420% | 0.3931 | 112.9614 |
| 4 | normal_volatility | 143.6371 | 196.2497 | 0.5942% | 0.5000 | 143.6371 |
| 5 | normal_volatility | 151.3044 | 200.9440 | 0.6247% | 0.5034 | 151.3044 |

**sma_10** — accepted across all folds: `False`

| Fold | Regime | MAE | RMSE | MAPE | Directional accuracy | Previous-close MAE |
|---:|---|---:|---:|---:|---:|---:|
| 1 | normal_volatility | 238.2116 | 301.2454 | 1.4799% | 0.4862 | 121.5098 |
| 2 | normal_volatility | 272.4856 | 339.3290 | 1.5961% | 0.4690 | 126.9912 |
| 3 | normal_volatility | 235.6889 | 289.0667 | 1.1338% | 0.4724 | 112.9614 |
| 4 | normal_volatility | 320.7826 | 391.7100 | 1.3272% | 0.4138 | 143.6371 |
| 5 | normal_volatility | 299.4314 | 384.4304 | 1.2335% | 0.5000 | 151.3044 |

**historical_return** — accepted across all folds: `False`

| Fold | Regime | MAE | RMSE | MAPE | Directional accuracy | Previous-close MAE |
|---:|---|---:|---:|---:|---:|---:|
| 1 | normal_volatility | 120.9375 | 160.4791 | 0.7558% | 0.5552 | 121.5098 |
| 2 | normal_volatility | 127.3675 | 166.8307 | 0.7442% | 0.4966 | 126.9912 |
| 3 | normal_volatility | 111.1013 | 166.1315 | 0.5331% | 0.6069 | 112.9614 |
| 4 | normal_volatility | 144.5001 | 196.5981 | 0.5981% | 0.5000 | 143.6371 |
| 5 | normal_volatility | 151.8523 | 201.7434 | 0.6272% | 0.4966 | 151.3044 |

**ridge** — accepted across all folds: `False`

| Fold | Regime | MAE | RMSE | MAPE | Directional accuracy | Previous-close MAE |
|---:|---|---:|---:|---:|---:|---:|
| 1 | normal_volatility | 137.4098 | 181.3039 | 0.8585% | 0.5241 | 121.5098 |
| 2 | normal_volatility | 131.3039 | 171.5750 | 0.7679% | 0.5276 | 126.9912 |
| 3 | normal_volatility | 115.9631 | 174.3689 | 0.5554% | 0.5069 | 112.9614 |
| 4 | normal_volatility | 148.8404 | 201.1347 | 0.6161% | 0.5103 | 143.6371 |
| 5 | normal_volatility | 153.9099 | 204.9098 | 0.6361% | 0.5272 | 151.3044 |

**linear** — accepted across all folds: `False`

| Fold | Regime | MAE | RMSE | MAPE | Directional accuracy | Previous-close MAE |
|---:|---|---:|---:|---:|---:|---:|
| 1 | normal_volatility | 143.0441 | 194.4046 | 0.8886% | 0.5103 | 121.5098 |
| 2 | normal_volatility | 134.2917 | 174.7135 | 0.7850% | 0.4828 | 126.9912 |
| 3 | normal_volatility | 120.2126 | 179.0864 | 0.5758% | 0.4621 | 112.9614 |
| 4 | normal_volatility | 151.2192 | 203.6461 | 0.6259% | 0.4931 | 143.6371 |
| 5 | normal_volatility | 155.6381 | 204.4768 | 0.6432% | 0.4966 | 151.3044 |

**xgboost** — accepted across all folds: `False`

| Fold | Regime | MAE | RMSE | MAPE | Directional accuracy | Previous-close MAE |
|---:|---|---:|---:|---:|---:|---:|
| 1 | normal_volatility | 124.1189 | 166.1687 | 0.7766% | 0.5310 | 121.5098 |
| 2 | normal_volatility | 135.6855 | 175.2297 | 0.7956% | 0.5069 | 126.9912 |
| 3 | normal_volatility | 110.8632 | 158.3336 | 0.5323% | 0.5655 | 112.9614 |
| 4 | normal_volatility | 146.1285 | 196.9185 | 0.6046% | 0.5310 | 143.6371 |
| 5 | normal_volatility | 157.9322 | 221.7088 | 0.6540% | 0.5646 | 151.3044 |

**lightgbm** — accepted across all folds: `False`

| Fold | Regime | MAE | RMSE | MAPE | Directional accuracy | Previous-close MAE |
|---:|---|---:|---:|---:|---:|---:|
| 1 | normal_volatility | 123.3078 | 166.7304 | 0.7710% | 0.5621 | 121.5098 |
| 2 | normal_volatility | 136.0747 | 175.5496 | 0.7979% | 0.5000 | 126.9912 |
| 3 | normal_volatility | 113.0699 | 166.4932 | 0.5424% | 0.5379 | 112.9614 |
| 4 | normal_volatility | 151.7613 | 201.7768 | 0.6281% | 0.5207 | 143.6371 |
| 5 | normal_volatility | 155.3661 | 215.0999 | 0.6425% | 0.5170 | 151.3044 |

**exponential_smoothing** — accepted across all folds: `False`

| Fold | Regime | MAE | RMSE | MAPE | Directional accuracy | Previous-close MAE |
|---:|---|---:|---:|---:|---:|---:|
| 1 | normal_volatility | 124.9622 | 166.8092 | 0.7797% | 0.5552 | 121.5098 |
| 2 | normal_volatility | 127.1357 | 166.8361 | 0.7422% | 0.5034 | 126.9912 |
| 3 | normal_volatility | 109.1850 | 166.1116 | 0.5241% | 0.6069 | 112.9614 |
| 4 | normal_volatility | 155.3756 | 205.3677 | 0.6434% | 0.5000 | 143.6371 |
| 5 | normal_volatility | 151.4127 | 201.1901 | 0.6253% | 0.4966 | 151.3044 |

**volatility_adjusted** — accepted across all folds: `False`

| Fold | Regime | MAE | RMSE | MAPE | Directional accuracy | Previous-close MAE |
|---:|---|---:|---:|---:|---:|---:|
| 1 | normal_volatility | 125.7331 | 167.7858 | 0.7844% | 0.5552 | 121.5098 |
| 2 | normal_volatility | 128.0301 | 168.1680 | 0.7468% | 0.5034 | 126.9912 |
| 3 | normal_volatility | 109.2141 | 166.7089 | 0.5243% | 0.6069 | 112.9614 |
| 4 | normal_volatility | 150.0904 | 200.6898 | 0.6215% | 0.5000 | 143.6371 |
| 5 | normal_volatility | 151.4379 | 200.9336 | 0.6251% | 0.5034 | 151.3044 |

### NIFTY_TELECOMMUNICATIONS

**previous_close** — accepted across all folds: `False`

| Fold | Regime | MAE | RMSE | MAPE | Directional accuracy | Previous-close MAE |
|---:|---|---:|---:|---:|---:|---:|
| 1 | normal_volatility | 22.1486 | 29.2324 | 1.1892% | 0.4621 | 22.1486 |
| 2 | normal_volatility | 17.8864 | 25.5123 | 0.9987% | 0.4966 | 17.8864 |
| 3 | normal_volatility | 24.5908 | 39.0088 | 1.0288% | 0.4310 | 24.5908 |
| 4 | normal_volatility | 31.5877 | 41.3295 | 1.1118% | 0.4966 | 31.5877 |
| 5 | normal_volatility | 32.9909 | 42.1079 | 1.0231% | 0.4286 | 32.9909 |

**sma_10** — accepted across all folds: `False`

| Fold | Regime | MAE | RMSE | MAPE | Directional accuracy | Previous-close MAE |
|---:|---|---:|---:|---:|---:|---:|
| 1 | normal_volatility | 44.2880 | 57.8759 | 2.3629% | 0.4931 | 22.1486 |
| 2 | normal_volatility | 37.9259 | 49.6936 | 2.1145% | 0.4793 | 17.8864 |
| 3 | normal_volatility | 50.2898 | 65.0605 | 2.1148% | 0.4793 | 24.5908 |
| 4 | normal_volatility | 62.1820 | 76.2862 | 2.1951% | 0.4621 | 31.5877 |
| 5 | normal_volatility | 68.3136 | 84.3571 | 2.1452% | 0.4456 | 32.9909 |

**historical_return** — accepted across all folds: `False`

| Fold | Regime | MAE | RMSE | MAPE | Directional accuracy | Previous-close MAE |
|---:|---|---:|---:|---:|---:|---:|
| 1 | normal_volatility | 22.1282 | 29.2135 | 1.1879% | 0.5379 | 22.1486 |
| 2 | normal_volatility | 17.8947 | 25.5683 | 0.9996% | 0.5034 | 17.8864 |
| 3 | normal_volatility | 24.5115 | 38.9347 | 1.0256% | 0.5690 | 24.5908 |
| 4 | normal_volatility | 31.6132 | 41.4413 | 1.1129% | 0.5034 | 31.5877 |
| 5 | normal_volatility | 32.8068 | 42.0174 | 1.0177% | 0.5714 | 32.9909 |

**ridge** — accepted across all folds: `False`

| Fold | Regime | MAE | RMSE | MAPE | Directional accuracy | Previous-close MAE |
|---:|---|---:|---:|---:|---:|---:|
| 1 | normal_volatility | 21.9954 | 29.1328 | 1.1823% | 0.5586 | 22.1486 |
| 2 | normal_volatility | 17.9276 | 25.5600 | 1.0017% | 0.5517 | 17.8864 |
| 3 | normal_volatility | 25.3735 | 39.9426 | 1.0549% | 0.5069 | 24.5908 |
| 4 | normal_volatility | 32.2225 | 41.9359 | 1.1350% | 0.5345 | 31.5877 |
| 5 | normal_volatility | 33.5990 | 42.6900 | 1.0403% | 0.5034 | 32.9909 |

**linear** — accepted across all folds: `False`

| Fold | Regime | MAE | RMSE | MAPE | Directional accuracy | Previous-close MAE |
|---:|---|---:|---:|---:|---:|---:|
| 1 | normal_volatility | 22.4818 | 29.9456 | 1.2057% | 0.5276 | 22.1486 |
| 2 | normal_volatility | 18.2218 | 25.9136 | 1.0183% | 0.5207 | 17.8864 |
| 3 | normal_volatility | 25.4470 | 39.7094 | 1.0573% | 0.5069 | 24.5908 |
| 4 | normal_volatility | 32.4559 | 42.2170 | 1.1429% | 0.4966 | 31.5877 |
| 5 | normal_volatility | 34.7760 | 44.1718 | 1.0746% | 0.4796 | 32.9909 |

**xgboost** — accepted across all folds: `False`

| Fold | Regime | MAE | RMSE | MAPE | Directional accuracy | Previous-close MAE |
|---:|---|---:|---:|---:|---:|---:|
| 1 | normal_volatility | 22.2004 | 29.4820 | 1.1910% | 0.5241 | 22.1486 |
| 2 | normal_volatility | 18.4286 | 26.3024 | 1.0288% | 0.5310 | 17.8864 |
| 3 | normal_volatility | 25.6412 | 42.4007 | 1.0630% | 0.4897 | 24.5908 |
| 4 | normal_volatility | 31.8009 | 41.6505 | 1.1207% | 0.5172 | 31.5877 |
| 5 | normal_volatility | 33.4418 | 42.6533 | 1.0365% | 0.5068 | 32.9909 |

**lightgbm** — accepted across all folds: `False`

| Fold | Regime | MAE | RMSE | MAPE | Directional accuracy | Previous-close MAE |
|---:|---|---:|---:|---:|---:|---:|
| 1 | normal_volatility | 22.6321 | 29.8985 | 1.2117% | 0.4931 | 22.1486 |
| 2 | normal_volatility | 18.0348 | 25.4247 | 1.0064% | 0.5069 | 17.8864 |
| 3 | normal_volatility | 25.2906 | 40.8111 | 1.0521% | 0.5138 | 24.5908 |
| 4 | normal_volatility | 32.0291 | 41.6366 | 1.1302% | 0.5138 | 31.5877 |
| 5 | normal_volatility | 33.1703 | 42.3697 | 1.0299% | 0.5204 | 32.9909 |

**exponential_smoothing** — accepted across all folds: `False`

| Fold | Regime | MAE | RMSE | MAPE | Directional accuracy | Previous-close MAE |
|---:|---|---:|---:|---:|---:|---:|
| 1 | normal_volatility | 23.3086 | 30.3461 | 1.2528% | 0.4621 | 22.1486 |
| 2 | normal_volatility | 18.8051 | 25.9954 | 1.0460% | 0.4966 | 17.8864 |
| 3 | normal_volatility | 24.4433 | 38.8741 | 1.0229% | 0.5690 | 24.5908 |
| 4 | normal_volatility | 32.3390 | 42.7452 | 1.1403% | 0.5034 | 31.5877 |
| 5 | normal_volatility | 33.1588 | 43.1013 | 1.0309% | 0.5714 | 32.9909 |

**volatility_adjusted** — accepted across all folds: `False`

| Fold | Regime | MAE | RMSE | MAPE | Directional accuracy | Previous-close MAE |
|---:|---|---:|---:|---:|---:|---:|
| 1 | normal_volatility | 23.3838 | 30.9262 | 1.2502% | 0.5379 | 22.1486 |
| 2 | normal_volatility | 19.0880 | 26.2530 | 1.0611% | 0.4966 | 17.8864 |
| 3 | normal_volatility | 24.7148 | 39.1246 | 1.0339% | 0.4310 | 24.5908 |
| 4 | normal_volatility | 32.5175 | 42.9922 | 1.1468% | 0.5034 | 31.5877 |
| 5 | normal_volatility | 34.6153 | 43.3862 | 1.0716% | 0.4286 | 32.9909 |

## GPU

The RTX 5050 is available. XGBoost has CUDA support, but these experiments used `tree_method=hist` CPU execution for deterministic apples-to-apples folds. LightGBM GPU support is unavailable in the installed build.

## Recommendation

No candidate should be integrated unless it passes the all-fold MAE/RMSE gate and a separate production review.

Unavailable research families: RandomForestRegressor, ExtraTreesRegressor, HistGradientBoosting, ARIMA.