"""Prediction Outcome Evaluation Service for Phase 7.

Computes directional classification performance metrics over verified market outcomes,
including directional accuracy, symmetrical class precision/recall/F1, and confusion matrices.
Adheres strictly to the requirement that accuracy is computed only over eligible, verified sessions.
"""

from typing import Any, Dict, List, Optional

from app.database.repository import PredictionRepository
from app.history.contract import EvaluationMetrics


class PredictionEvaluator:
    """Evaluates prediction performance against verified market outcomes."""

    def __init__(self, repository: PredictionRepository) -> None:
        """Initialize evaluator with database repository."""
        self.repository = repository

    def evaluate(
        self,
        symbol: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> EvaluationMetrics:
        """Compute comprehensive evaluation metrics for stored predictions.

        Args:
            symbol: Optional symbol filter (e.g. 'BHARTIARTL').
            model_name: Optional model filter (e.g. 'xgboost', 'lightgbm').

        Returns:
            EvaluationMetrics container with full statistics and formatted audit summary.
        """
        records = self.repository.list_predictions_with_actuals(
            symbol=symbol,
            model_name=model_name,
            limit=100000,
        )

        return self.compute_metrics(records)

    @staticmethod
    def compute_metrics(records: List[Dict[str, Any]]) -> EvaluationMetrics:
        """Compute evaluation metrics from a list of prediction-with-actual dictionaries."""
        total = len(records)
        eligible = 0
        ineligible = 0
        pending = 0
        verified = 0

        # Sub-group tracking
        by_model_records: Dict[str, List[Dict[str, Any]]] = {}
        by_symbol_records: Dict[str, List[Dict[str, Any]]] = {}

        tp = 0  # Pred UP, Act UP
        fp = 0  # Pred UP, Act DOWN
        tn = 0  # Pred DOWN, Act DOWN
        fn = 0  # Pred DOWN, Act UP

        pred_up = 0
        pred_down = 0
        act_up = 0
        act_down = 0
        correct = 0
        incorrect = 0

        for r in records:
            m_name = str(r.get("model_name", "unknown")).lower()
            sym = str(r.get("symbol", "unknown")).upper()
            by_model_records.setdefault(m_name, []).append(r)
            by_symbol_records.setdefault(sym, []).append(r)

            status = r.get("status")
            p_dir = r.get("predicted_direction")
            p_lbl = r.get("predicted_label")
            latest_ts = r.get("latest_input_timestamp")

            is_elig = (status == "SUCCESS" and p_dir in ("UP", "DOWN") and p_lbl in (0, 1) and bool(latest_ts))
            if not is_elig:
                ineligible += 1
                continue

            eligible += 1

            act_dir = r.get("actual_direction")
            act_lbl = r.get("actual_label")

            if not act_dir or act_lbl is None:
                # Target session has not occurred or outcome not recorded
                pending += 1
                continue

            verified += 1
            act_dir = act_dir.upper()

            if p_dir == "UP":
                pred_up += 1
            else:
                pred_down += 1

            if act_dir == "UP":
                act_up += 1
            else:
                act_down += 1

            # Confusion matrix accumulation
            if p_dir == "UP" and act_dir == "UP":
                tp += 1
                correct += 1
            elif p_dir == "UP" and act_dir == "DOWN":
                fp += 1
                incorrect += 1
            elif p_dir == "DOWN" and act_dir == "DOWN":
                tn += 1
                correct += 1
            elif p_dir == "DOWN" and act_dir == "UP":
                fn += 1
                incorrect += 1

        # Accuracy calculated strictly on verified predictions (the denominator)
        accuracy = (correct / verified) if verified > 0 else None

        # Precision, Recall, F1 for UP
        prec_up = (tp / (tp + fp)) if (tp + fp) > 0 else None
        rec_up = (tp / (tp + fn)) if (tp + fn) > 0 else None
        f1_up = (2 * prec_up * rec_up / (prec_up + rec_up)) if (prec_up and rec_up and (prec_up + rec_up) > 0) else None

        # Precision, Recall, F1 for DOWN
        prec_down = (tn / (tn + fn)) if (tn + fn) > 0 else None
        rec_down = (tn / (tn + fp)) if (tn + fp) > 0 else None
        f1_down = (2 * prec_down * rec_down / (prec_down + rec_down)) if (prec_down and rec_down and (prec_down + rec_down) > 0) else None

        # Compute breakdown by model
        by_model: Dict[str, Any] = {}
        for m, m_recs in by_model_records.items():
            m_metrics = PredictionEvaluator._compute_subgroup_summary(m_recs)
            by_model[m] = m_metrics

        # Compute breakdown by symbol
        by_symbol: Dict[str, Any] = {}
        for s, s_recs in by_symbol_records.items():
            s_metrics = PredictionEvaluator._compute_subgroup_summary(s_recs)
            by_symbol[s] = s_metrics

        return EvaluationMetrics(
            total_predictions=total,
            eligible_predictions=eligible,
            ineligible_predictions=ineligible,
            verified_predictions=verified,
            pending_predictions=pending,
            unverifiable_predictions=0,
            correct_predictions=correct,
            incorrect_predictions=incorrect,
            directional_accuracy=round(accuracy, 4) if accuracy is not None else None,
            up_predictions=pred_up,
            down_predictions=pred_down,
            actual_up_count=act_up,
            actual_down_count=act_down,
            true_positives=tp,
            false_positives=fp,
            true_negatives=tn,
            false_negatives=fn,
            precision_up=round(prec_up, 4) if prec_up is not None else None,
            recall_up=round(rec_up, 4) if rec_up is not None else None,
            f1_up=round(f1_up, 4) if f1_up is not None else None,
            precision_down=round(prec_down, 4) if prec_down is not None else None,
            recall_down=round(rec_down, 4) if rec_down is not None else None,
            f1_down=round(f1_down, 4) if f1_down is not None else None,
            by_model=by_model,
            by_symbol=by_symbol,
        )

    @staticmethod
    def _compute_subgroup_summary(records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compute condensed accuracy and counts for a model or symbol subset."""
        tot = len(records)
        ver = 0
        corr = 0
        pend = 0
        for r in records:
            if r.get("status") == "SUCCESS" and r.get("predicted_direction"):
                act_dir = r.get("actual_direction")
                if act_dir:
                    ver += 1
                    if r.get("predicted_direction") == act_dir:
                        corr += 1
                else:
                    pend += 1

        acc = (corr / ver) if ver > 0 else None
        return {
            "total": tot,
            "verified": ver,
            "pending": pend,
            "correct": corr,
            "incorrect": ver - corr,
            "directional_accuracy": round(acc, 4) if acc is not None else None,
        }
