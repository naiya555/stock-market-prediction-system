"""Probability Calibration & Statistical Significance Layer (Day 62).

Implements leakage-safe probability baselines, reliability diagrams, Expected Calibration
Error (ECE), Wilson score confidence intervals, and paired McNemar significance testing
for financial direction classifiers.

Invariants & Constraints:
1. No Holdout Calibrator Fitting:
   Calibrators (e.g. Platt scaling, isotonic regression) must NEVER be fitted on the
   final evaluation holdout partition. Doing so constitutes direct post-hoc leakage.
2. Genuine Probabilities Only:
   Calibration metrics (Brier, LogLoss, ECE, MCE) require continuous probabilities
   in [0, 1], not discrete hard labels.
3. Paired Significance Testing:
   Models evaluated on identical chronological sessions are correlated/paired.
   Independent-samples tests (e.g. standard two-sample t-test or z-test) are
   statistically invalid; McNemar's test with continuity correction is used.
4. Empty Bin Safety:
   Reliability diagram bins with zero samples are handled safely without NaNs.
"""

from dataclasses import asdict, dataclass
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import numpy as np
from scipy import stats

from app.core.logging_config import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class ReliabilityBin:
    """Bin summary in a reliability diagram."""

    bin_index: int
    bin_range: Tuple[float, float]
    sample_count: int
    mean_confidence: Optional[float]
    empirical_accuracy: Optional[float]
    calibration_gap: Optional[float]

    def to_dict(self) -> Dict[str, Any]:
        """Convert bin to dictionary."""
        return {
            "bin_index": self.bin_index,
            "bin_range": [round(self.bin_range[0], 2), round(self.bin_range[1], 2)],
            "sample_count": self.sample_count,
            "mean_confidence": self.mean_confidence,
            "empirical_accuracy": self.empirical_accuracy,
            "calibration_gap": self.calibration_gap,
        }


@dataclass(frozen=True)
class ReliabilityDiagramResult:
    """Complete reliability diagram and calibration error metrics."""

    n_bins: int
    bins: List[ReliabilityBin]
    expected_calibration_error: float
    max_calibration_error: float
    brier_score: float
    log_loss: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "n_bins": self.n_bins,
            "bins": [b.to_dict() for b in self.bins],
            "expected_calibration_error": round(self.expected_calibration_error, 4),
            "max_calibration_error": round(self.max_calibration_error, 4),
            "brier_score": round(self.brier_score, 4),
            "log_loss": round(self.log_loss, 4),
        }


@dataclass(frozen=True)
class ConfidenceInterval:
    """Confidence interval for an empirical metric (e.g. Wilson score for accuracy)."""

    metric_name: str
    observed_value: float
    confidence_level: float
    lower_bound: float
    upper_bound: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert confidence interval to dictionary."""
        return {
            "metric_name": self.metric_name,
            "observed_value": round(self.observed_value, 4),
            "confidence_level": self.confidence_level,
            "lower_bound": round(self.lower_bound, 4),
            "upper_bound": round(self.upper_bound, 4),
        }


@dataclass(frozen=True)
class PairedComparisonResult:
    """Statistical outcome of a paired model comparison test."""

    model_a: str
    model_b: str
    sample_size: int
    both_correct: int
    both_incorrect: int
    a_correct_b_incorrect: int
    b_correct_a_incorrect: int
    statistic: float
    p_value: float
    alpha: float
    is_significant: bool
    conclusion: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert paired comparison result to dictionary."""
        return {
            "model_a": self.model_a,
            "model_b": self.model_b,
            "sample_size": self.sample_size,
            "contingency_table": {
                "both_correct": self.both_correct,
                "both_incorrect": self.both_incorrect,
                f"{self.model_a}_correct_{self.model_b}_incorrect": self.a_correct_b_incorrect,
                f"{self.model_b}_correct_{self.model_a}_incorrect": self.b_correct_a_incorrect,
            },
            "statistic": round(self.statistic, 4),
            "p_value": round(self.p_value, 4),
            "alpha": self.alpha,
            "is_significant": self.is_significant,
            "conclusion": self.conclusion,
        }


def compute_log_loss(
    y_true: Sequence[int],
    y_prob_up: Sequence[float],
    eps: float = 1e-15,
) -> float:
    """Compute binary cross-entropy (log loss) with probability clipping.

    Args:
        y_true: Binary ground truth labels {0, 1}.
        y_prob_up: Probability of positive class (UP) in [0.0, 1.0].
        eps: Epsilon clipping to prevent log(0).

    Returns:
        Mean binary log loss.

    Raises:
        ValueError: If inputs are empty or lengths mismatch.
    """
    yt = np.asarray(y_true, dtype=float).ravel()
    yp = np.asarray(y_prob_up, dtype=float).ravel()

    if len(yt) == 0 or len(yp) == 0:
        raise ValueError("Cannot compute log loss on empty arrays.")
    if len(yt) != len(yp):
        raise ValueError(f"Length mismatch: len(y_true)={len(yt)} != len(y_prob_up)={len(yp)}")

    yp_clipped = np.clip(yp, eps, 1.0 - eps)
    loss = -np.mean(yt * np.log(yp_clipped) + (1.0 - yt) * np.log(1.0 - yp_clipped))
    return float(loss)


def compute_reliability_diagram(
    y_true: Sequence[int],
    y_prob_up: Sequence[float],
    n_bins: int = 5,
) -> ReliabilityDiagramResult:
    """Compute reliability diagram bins, ECE, MCE, Brier score, and LogLoss.

    Args:
        y_true: Binary ground truth labels in {0, 1}.
        y_prob_up: Predicted probabilities of class 1 (UP) in [0, 1].
        n_bins: Number of equal-width bins in [0, 1] (default 5).

    Returns:
        ReliabilityDiagramResult containing bin diagnostics and calibration errors.

    Raises:
        ValueError: If input arrays are empty or lengths do not match.
    """
    yt = np.asarray(y_true, dtype=int).ravel()
    yp = np.asarray(y_prob_up, dtype=float).ravel()

    if len(yt) == 0 or len(yp) == 0:
        raise ValueError("Cannot compute reliability diagram on empty arrays.")
    if len(yt) != len(yp):
        raise ValueError(f"Length mismatch: len(y_true)={len(yt)} != len(y_prob)={len(yp)}")
    if n_bins < 2:
        raise ValueError(f"n_bins must be at least 2, got {n_bins}")

    # Clip probabilities to valid [0, 1] domain
    yp = np.clip(yp, 0.0, 1.0)

    # Bin edges in [0.0, 1.0]
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    # Digitize samples: bin 0 is [0, edge_1], last bin is (edge_{n-1}, 1.0]
    bin_indices = np.digitize(yp, bin_edges) - 1
    bin_indices = np.clip(bin_indices, 0, n_bins - 1)

    bins: List[ReliabilityBin] = []
    total_samples = len(yt)
    weighted_ece = 0.0
    max_mce = 0.0

    for b in range(n_bins):
        low = float(bin_edges[b])
        high = float(bin_edges[b + 1])
        mask = (bin_indices == b)
        count = int(np.sum(mask))

        if count == 0:
            bins.append(
                ReliabilityBin(
                    bin_index=b,
                    bin_range=(low, high),
                    sample_count=0,
                    mean_confidence=None,
                    empirical_accuracy=None,
                    calibration_gap=None,
                )
            )
            continue

        conf = float(np.mean(yp[mask]))
        acc = float(np.mean(yt[mask]))
        gap = abs(acc - conf)

        weighted_ece += (count / total_samples) * gap
        max_mce = max(max_mce, gap)

        bins.append(
            ReliabilityBin(
                bin_index=b,
                bin_range=(low, high),
                sample_count=count,
                mean_confidence=round(conf, 4),
                empirical_accuracy=round(acc, 4),
                calibration_gap=round(gap, 4),
            )
        )

    brier = float(np.mean((yp - yt) ** 2))
    loss = compute_log_loss(yt, yp)

    return ReliabilityDiagramResult(
        n_bins=n_bins,
        bins=bins,
        expected_calibration_error=round(weighted_ece, 4),
        max_calibration_error=round(max_mce, 4),
        brier_score=round(brier, 4),
        log_loss=round(loss, 4),
    )


def compute_wilson_score_interval(
    successes: int,
    total: int,
    confidence: float = 0.95,
) -> ConfidenceInterval:
    """Compute Wilson score confidence interval for a binomial proportion.

    Args:
        successes: Number of successful outcomes (k >= 0).
        total: Number of trials (n > 0).
        confidence: Confidence level in (0, 1), default 0.95.

    Returns:
        ConfidenceInterval with lower and upper bounds.

    Raises:
        ValueError: On invalid trial counts or confidence values.
    """
    if total <= 0:
        raise ValueError(f"Total trials must be positive, got {total}")
    if successes < 0 or successes > total:
        raise ValueError(f"Successes ({successes}) must be between 0 and total ({total})")
    if not (0.0 < confidence < 1.0):
        raise ValueError(f"Confidence level must be between 0 and 1, got {confidence}")

    p = successes / total
    z = float(stats.norm.ppf(1.0 - (1.0 - confidence) / 2.0))

    z2 = z ** 2
    denom = 1.0 + z2 / total
    center = (p + z2 / (2.0 * total)) / denom
    margin = (z / denom) * math.sqrt((p * (1.0 - p) / total) + (z2 / (4.0 * (total ** 2))))

    lower = max(0.0, center - margin)
    upper = min(1.0, center + margin)

    return ConfidenceInterval(
        metric_name="accuracy",
        observed_value=p,
        confidence_level=confidence,
        lower_bound=lower,
        upper_bound=upper,
    )


def compute_mcnemar_paired_test(
    y_true: Sequence[int],
    y_pred_a: Sequence[int],
    y_pred_b: Sequence[int],
    model_a_name: str = "Model_A",
    model_b_name: str = "Model_B",
    alpha: float = 0.05,
    continuity_correction: bool = True,
) -> PairedComparisonResult:
    """Perform McNemar's test for paired classification accuracy comparison.

    Null Hypothesis (H0):
        The two models have identical marginal error rates (discordant pairs are equally likely,
        i.e. P(Model A correct, Model B wrong) = P(Model B correct, Model A wrong)).

    Assumptions:
        - The observations are paired (both models evaluated on the identical sessions).
        - The outcomes are binary (correct vs. incorrect).
        - Test statistic with Edwards' continuity correction:
          chi2 = (|b - c| - 1)^2 / (b + c) if (b + c) > 0 else 0.0.

    Args:
        y_true: Ground truth binary labels.
        y_pred_a: Predictions from Model A.
        y_pred_b: Predictions from Model B.
        model_a_name: Label for Model A.
        model_b_name: Label for Model B.
        alpha: Significance threshold (default 0.05).
        continuity_correction: Whether to apply Edwards' continuity correction (default True).

    Returns:
        PairedComparisonResult with test statistics and clear conclusion.
    """
    yt = np.asarray(y_true, dtype=int).ravel()
    pa = np.asarray(y_pred_a, dtype=int).ravel()
    pb = np.asarray(y_pred_b, dtype=int).ravel()

    if len(yt) != len(pa) or len(yt) != len(pb):
        raise ValueError(
            f"Length mismatch: len(y_true)={len(yt)}, len(y_pred_a)={len(pa)}, len(y_pred_b)={len(pb)}"
        )
    if len(yt) == 0:
        raise ValueError("Cannot perform McNemar test on empty data.")

    correct_a = (pa == yt).astype(int)
    correct_b = (pb == yt).astype(int)

    both_correct = int(np.sum((correct_a == 1) & (correct_b == 1)))
    both_incorrect = int(np.sum((correct_a == 0) & (correct_b == 0)))
    b = int(np.sum((correct_a == 0) & (correct_b == 1)))  # A wrong, B right
    c = int(np.sum((correct_a == 1) & (correct_b == 0)))  # A right, B wrong

    discordant = b + c
    if discordant == 0:
        return PairedComparisonResult(
            model_a=model_a_name,
            model_b=model_b_name,
            sample_size=len(yt),
            both_correct=both_correct,
            both_incorrect=both_incorrect,
            a_correct_b_incorrect=c,
            b_correct_a_incorrect=b,
            statistic=0.0,
            p_value=1.0,
            alpha=alpha,
            is_significant=False,
            conclusion="Identical predictions on all evaluation samples (0 discordant pairs).",
        )

    if continuity_correction:
        chi2 = ((abs(b - c) - 1.0) ** 2) / discordant if abs(b - c) >= 1.0 else 0.0
    else:
        chi2 = ((b - c) ** 2) / discordant

    p_value = float(stats.chi2.sf(chi2, df=1))
    is_sig = bool(p_value < alpha)

    if is_sig:
        better = model_b_name if b > c else model_a_name
        conclusion = (
            f"Statistically significant difference detected (chi2={chi2:.4f}, p={p_value:.4f} < {alpha}). "
            f"{better} demonstrated superior paired accuracy."
        )
    else:
        conclusion = (
            f"Inconclusive / No statistically significant difference detected (chi2={chi2:.4f}, p={p_value:.4f} >= {alpha}). "
            f"Observed accuracy discrepancy ({abs(b - c)} discordant difference out of {len(yt)} sessions) "
            "cannot reject the null hypothesis of equal model performance."
        )

    return PairedComparisonResult(
        model_a=model_a_name,
        model_b=model_b_name,
        sample_size=len(yt),
        both_correct=both_correct,
        both_incorrect=both_incorrect,
        a_correct_b_incorrect=c,
        b_correct_a_incorrect=b,
        statistic=chi2,
        p_value=p_value,
        alpha=alpha,
        is_significant=is_sig,
        conclusion=conclusion,
    )
