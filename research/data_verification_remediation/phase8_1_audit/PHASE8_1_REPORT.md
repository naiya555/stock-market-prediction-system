# Phase 8.1 Residual Sequence Equivalence Audit

## Result

Phase 8 reproduces the exact Phase 6 previous-close OOS residual population for all four instruments. Both use `initial=max(50,int(n*0.4))`, five folds, `available=n-initial-1`, `fold_size=available//5`, validation start `initial+1+fold*fold_size`, final fold through the last row, and one-session embargo. Both predict the immediately preceding close and compute `actual - prediction`.

The row-by-row comparison contains 5,936 matched rows across the four instruments. No duplicate dates or chronology violations were found. Phase 8 is therefore not a separate recomputed population; its OOS residuals are sequence-equivalent to Phase 6 for the same provider snapshot.

## Ljung–Box validation

The implementation matches the standard Q statistic, centered autocorrelation, degrees of freedom equal to the tested lag, and chi-square survival-function p-value. The deterministic `[1,2,3,4,5]` lag-3 example passed: Q=4.316666666666667 and p=0.2292378217841052.

## Pooling limitations

Pooling is acceptable for this fixed previous-close baseline as an overall descriptive diagnostic, but it does not establish independent identically distributed residuals. Price scale, volatility, and regimes change over time; fold-specific results and heteroscedasticity remain necessary.

Exact fold boundaries, counts, row comparisons, and statistical validation are in the accompanying JSON/CSV artifacts. No Phase 6 or Phase 8 output was modified.
