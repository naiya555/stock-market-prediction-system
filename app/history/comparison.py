"""Comparative Model Evaluation Service for Phase 15.

Enables side-by-side empirical benchmarking of Python ML (XGBoost / LightGBM)
versus Qualitative LLM reasoning versus Combined Multi-Agent Ensemble forecasts.

Adheres strictly to:
- ADR 05: Independence of Python ML and LLM predictions (measure each independently).
- ADR 06: Preservation of historical truth (evaluated only on verified immutable outcomes).
- ADR 10: Controlled, gated evaluation without automated retraining loops.
"""

from dataclasses import asdict, dataclass, field
import json
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.database.repository import PredictionRepository
from app.history.evaluator import PredictionEvaluator


@dataclass(frozen=True)
class ModelPerformanceRow:
    """Condensed performance metrics for a single model architecture."""

    model_name: str
    total_predictions: int
    verified_sessions: int
    pending_sessions: int
    correct_predictions: int
    incorrect_predictions: int
    directional_accuracy: Optional[float]
    precision_up: Optional[float]
    recall_up: Optional[float]
    f1_up: Optional[float]
    precision_down: Optional[float]
    recall_down: Optional[float]
    f1_down: Optional[float]
    brier_score: Optional[float]

    def to_dict(self) -> Dict[str, Any]:
        """Convert row to serializable dictionary."""
        return asdict(self)


@dataclass(frozen=True)
class PairwiseComparison:
    """Side-by-side comparison between two models evaluated on identical sessions."""

    model_a: str
    model_b: str
    matched_sessions: int
    agreement_count: int
    agreement_rate: Optional[float]
    agreement_accuracy: Optional[float]
    divergence_count: int
    divergence_rate: Optional[float]
    divergence_accuracy_a: Optional[float]
    divergence_accuracy_b: Optional[float]
    model_a_superior_count: int  # A correct, B incorrect
    model_b_superior_count: int  # B correct, A incorrect
    both_correct_count: int
    both_incorrect_count: int
    accuracy_delta: Optional[float]  # Accuracy(A) - Accuracy(B)

    def to_dict(self) -> Dict[str, Any]:
        """Convert comparison to serializable dictionary."""
        return asdict(self)


@dataclass(frozen=True)
class ComparativeEvaluationReport:
    """Comprehensive comparative evaluation report across models."""

    symbol: Optional[str]
    total_records_analyzed: int
    models: List[ModelPerformanceRow]
    pairwise_comparisons: List[PairwiseComparison]
    ensemble_lift_over_ml: Optional[float]
    ensemble_lift_over_llm: Optional[float]
    disclaimer: str = (
        "Model comparison metrics evaluate binary next-session directional forecasts (UP vs DOWN) "
        "strictly across completed, verified market outcomes. Brier scores measure probability calibration "
        "(lower is better, 0.0 is perfect). Past comparative accuracy reflects historical out-of-sample "
        "performance and does not guarantee future financial market profitability or risk immunity."
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "symbol": self.symbol,
            "total_records_analyzed": self.total_records_analyzed,
            "models": [m.to_dict() for m in self.models],
            "pairwise_comparisons": [p.to_dict() for p in self.pairwise_comparisons],
            "ensemble_lift_over_ml": self.ensemble_lift_over_ml,
            "ensemble_lift_over_llm": self.ensemble_lift_over_llm,
            "disclaimer": self.disclaimer,
        }

    def format_summary(self) -> str:
        """Render a clean text audit table comparing model performance."""
        lines = [
            "================================================================================",
            "PHASE 15 COMPARATIVE MODEL EVALUATION REPORT",
            "================================================================================",
            f"  Symbol Filter:             {self.symbol or 'ALL SYMBOLS'}",
            f"  Total Records Analyzed:    {self.total_records_analyzed}",
            "--------------------------------------------------------------------------------",
            f"  {'Model':<15} {'Verified':<10} {'Accuracy':<12} {'F1 (UP)':<10} {'F1 (DN)':<10} {'Brier Score':<12}",
            f"  {'-'*15} {'-'*10} {'-'*12} {'-'*10} {'-'*10} {'-'*12}",
        ]
        for m in self.models:
            acc_str = f"{m.directional_accuracy * 100:.2f}%" if m.directional_accuracy is not None else "N/A"
            f1_up = f"{m.f1_up:.4f}" if m.f1_up is not None else "N/A"
            f1_dn = f"{m.f1_down:.4f}" if m.f1_down is not None else "N/A"
            brier_str = f"{m.brier_score:.4f}" if m.brier_score is not None else "N/A"
            lines.append(
                f"  {m.model_name:<15} {m.verified_sessions:<10} {acc_str:<12} {f1_up:<10} {f1_dn:<10} {brier_str:<12}"
            )

        if self.pairwise_comparisons:
            lines.extend([
                "--------------------------------------------------------------------------------",
                "  Pairwise Session Alignment & Superiority:",
            ])
            for pw in self.pairwise_comparisons:
                agr_str = f"{pw.agreement_rate * 100:.1f}%" if pw.agreement_rate is not None else "N/A"
                delta_str = f"{pw.accuracy_delta * 100:+.2f}%" if pw.accuracy_delta is not None else "N/A"
                lines.append(
                    f"    [{pw.model_a.upper()} vs {pw.model_b.upper()}] "
                    f"Matched: {pw.matched_sessions} | Agreement: {agr_str} | "
                    f"Wins: {pw.model_a}={pw.model_a_superior_count}, {pw.model_b}={pw.model_b_superior_count} | "
                    f"Delta ({pw.model_a}-{pw.model_b}): {delta_str}"
                )

        if self.ensemble_lift_over_ml is not None:
            lines.append(f"  Ensemble Lift over ML:     {self.ensemble_lift_over_ml * 100:+.2f}%")
        if self.ensemble_lift_over_llm is not None:
            lines.append(f"  Ensemble Lift over LLM:    {self.ensemble_lift_over_llm * 100:+.2f}%")

        lines.extend([
            "================================================================================",
            f"Disclaimer: {self.disclaimer}",
            "================================================================================",
        ])
        return "\n".join(lines)


class ModelComparator:
    """Compares Python ML, LLM reasoning, and Combined Ensemble models."""

    def __init__(self, repository: Optional[PredictionRepository] = None) -> None:
        """Initialize comparator with optional database repository."""
        self.repository = repository

    def compare_from_repository(
        self,
        symbol: Optional[str] = None,
        min_verified: int = 1,
    ) -> ComparativeEvaluationReport:
        """Fetch all joined prediction/actual records and compute comparative report."""
        if not self.repository:
            raise ValueError("PredictionRepository must be provided to fetch from database.")

        clean_sym = symbol.strip().upper() if symbol else None
        records = self.repository.list_predictions_with_actuals(
            symbol=clean_sym,
            limit=100000,
        )
        return self.compare_records(records, symbol=clean_sym, min_verified=min_verified)

    @staticmethod
    def compare_records(
        records: Sequence[Dict[str, Any]],
        symbol: Optional[str] = None,
        min_verified: int = 1,
    ) -> ComparativeEvaluationReport:
        """Compute comparative performance report from prediction records.

        Deconstructs standalone predictions and constituent ensemble components
        into unified model streams and performs pairwise alignment comparisons.
        """
        # Step 1: Collect canonical unified items per model
        # A record maps to model_name -> list of prediction dicts
        by_model_items: Dict[str, List[Dict[str, Any]]] = {}

        # Session map: session_key -> dict of model_name -> prediction dict
        # session_key is (symbol, target_date or latest_input_timestamp)
        sessions: Dict[Tuple[str, str], Dict[str, Dict[str, Any]]] = {}

        for r in records:
            m_name = str(r.get("model_name", "unknown")).lower()
            sym = str(r.get("symbol", "unknown")).upper()
            target_key = r.get("target_date") or r.get("latest_input_timestamp")
            if not target_key:
                continue
            session_key = (sym, str(target_key))

            by_model_items.setdefault(m_name, []).append(r)
            sessions.setdefault(session_key, {})[m_name] = r

            # Check if this is an ensemble record with embedded constituent ML and LLM results
            raw_res = r.get("raw_result")
            if not raw_res and r.get("raw_result_json"):
                try:
                    raw_res = json.loads(r["raw_result_json"])
                except Exception:
                    raw_res = None

            if isinstance(raw_res, dict):
                # Extract embedded ML prediction if not already present as separate row
                ml_dict = raw_res.get("ml_prediction")
                if isinstance(ml_dict, dict) and ml_dict.get("predicted_direction"):
                    ml_name = str(ml_dict.get("model_name", "ml_component")).lower()
                    virtual_ml = {
                        "prediction_id": f"{r.get('prediction_id')}_ml",
                        "symbol": sym,
                        "model_name": ml_name,
                        "model_version": ml_dict.get("model_version", "v1"),
                        "status": ml_dict.get("status", "SUCCESS"),
                        "predicted_direction": ml_dict.get("predicted_direction"),
                        "predicted_label": ml_dict.get("predicted_label"),
                        "probability_up": ml_dict.get("probability_up"),
                        "probability_down": ml_dict.get("probability_down"),
                        "actual_direction": r.get("actual_direction"),
                        "actual_label": r.get("actual_label"),
                        "actual_return": r.get("actual_return"),
                        "target_date": r.get("target_date"),
                        "latest_input_timestamp": r.get("latest_input_timestamp"),
                    }
                    if ml_name not in sessions[session_key]:
                        sessions[session_key][ml_name] = virtual_ml
                        by_model_items.setdefault(ml_name, []).append(virtual_ml)

                # Extract embedded LLM reasoning if not already present
                llm_dict = raw_res.get("llm_reasoning")
                if isinstance(llm_dict, dict) and llm_dict.get("direction"):
                    llm_dir_val = llm_dict.get("direction")
                    if hasattr(llm_dir_val, "value"):
                        llm_dir_val = llm_dir_val.value
                    llm_dir_val = str(llm_dir_val).upper()
                    if llm_dir_val in ("UP", "DOWN"):
                        virtual_llm = {
                            "prediction_id": f"{r.get('prediction_id')}_llm",
                            "symbol": sym,
                            "model_name": "llm",
                            "model_version": str(llm_dict.get("model_version", "gemma3")),
                            "status": "SUCCESS",
                            "predicted_direction": llm_dir_val,
                            "predicted_label": 1 if llm_dir_val == "UP" else 0,
                            "probability_up": 1.0 if llm_dir_val == "UP" else 0.0,
                            "probability_down": 0.0 if llm_dir_val == "UP" else 1.0,
                            "actual_direction": r.get("actual_direction"),
                            "actual_label": r.get("actual_label"),
                            "actual_return": r.get("actual_return"),
                            "target_date": r.get("target_date"),
                            "latest_input_timestamp": r.get("latest_input_timestamp"),
                        }
                        if "llm" not in sessions[session_key]:
                            sessions[session_key]["llm"] = virtual_llm
                            by_model_items.setdefault("llm", []).append(virtual_llm)

        # Step 2: Compute individual model performance rows
        model_rows: List[ModelPerformanceRow] = []
        for m_name in sorted(by_model_items.keys()):
            m_recs = by_model_items[m_name]
            metrics = PredictionEvaluator.compute_metrics(m_recs)

            # Compute Brier score over verified sessions with probability_up
            brier_sq_errors: List[float] = []
            for r in m_recs:
                if r.get("actual_label") is not None and r.get("probability_up") is not None:
                    try:
                        p = float(r["probability_up"])
                        y = float(r["actual_label"])
                        if math.isfinite(p) and math.isfinite(y):
                            brier_sq_errors.append((p - y) ** 2)
                    except (ValueError, TypeError):
                        pass

            brier = round(sum(brier_sq_errors) / len(brier_sq_errors), 4) if brier_sq_errors else None

            model_rows.append(
                ModelPerformanceRow(
                    model_name=m_name,
                    total_predictions=metrics.total_predictions,
                    verified_sessions=metrics.verified_predictions,
                    pending_sessions=metrics.pending_predictions,
                    correct_predictions=metrics.correct_predictions,
                    incorrect_predictions=metrics.incorrect_predictions,
                    directional_accuracy=metrics.directional_accuracy,
                    precision_up=metrics.precision_up,
                    recall_up=metrics.recall_up,
                    f1_up=metrics.f1_up,
                    precision_down=metrics.precision_down,
                    recall_down=metrics.recall_down,
                    f1_down=metrics.f1_down,
                    brier_score=brier,
                )
            )

        # Step 3: Compute Pairwise Comparisons on Matched Sessions
        pairwise_list: List[PairwiseComparison] = []
        model_names = [m.model_name for m in model_rows]

        for i in range(len(model_names)):
            for j in range(i + 1, len(model_names)):
                name_a = model_names[i]
                name_b = model_names[j]

                pw = ModelComparator._compute_pairwise(sessions, name_a, name_b)
                if pw.matched_sessions >= min_verified:
                    pairwise_list.append(pw)

        # Step 4: Calculate Ensemble Lift
        ensemble_row = next((m for m in model_rows if m.model_name == "ensemble"), None)
        ml_candidates = [m for m in model_rows if m.model_name in ("xgboost", "lightgbm") or "ml" in m.model_name]
        llm_row = next((m for m in model_rows if m.model_name in ("llm", "gemma3")), None)

        ens_lift_ml = None
        if ensemble_row and ensemble_row.directional_accuracy is not None and ml_candidates:
            # Pick primary ML model or average
            primary_ml = ml_candidates[0]
            if primary_ml.directional_accuracy is not None:
                ens_lift_ml = round(ensemble_row.directional_accuracy - primary_ml.directional_accuracy, 4)

        ens_lift_llm = None
        if ensemble_row and ensemble_row.directional_accuracy is not None and llm_row:
            if llm_row.directional_accuracy is not None:
                ens_lift_llm = round(ensemble_row.directional_accuracy - llm_row.directional_accuracy, 4)

        return ComparativeEvaluationReport(
            symbol=symbol,
            total_records_analyzed=len(records),
            models=model_rows,
            pairwise_comparisons=pairwise_list,
            ensemble_lift_over_ml=ens_lift_ml,
            ensemble_lift_over_llm=ens_lift_llm,
        )

    @staticmethod
    def _compute_pairwise(
        sessions: Dict[Tuple[str, str], Dict[str, Dict[str, Any]]],
        model_a: str,
        model_b: str,
    ) -> PairwiseComparison:
        """Compute side-by-side alignment, divergence, and superiority for two models."""
        matched = 0
        agree_cnt = 0
        agree_corr = 0
        div_cnt = 0
        div_corr_a = 0
        div_corr_b = 0

        a_wins = 0
        b_wins = 0
        both_corr = 0
        both_incorr = 0
        corr_a = 0
        corr_b = 0

        for session_key, model_dict in sessions.items():
            if model_a in model_dict and model_b in model_dict:
                rec_a = model_dict[model_a]
                rec_b = model_dict[model_b]

                act_dir = rec_a.get("actual_direction") or rec_b.get("actual_direction")
                dir_a = rec_a.get("predicted_direction")
                dir_b = rec_b.get("predicted_direction")

                # Both must be verified with completed outcomes
                if not act_dir or not dir_a or not dir_b:
                    continue

                act_dir = act_dir.upper()
                dir_a = dir_a.upper()
                dir_b = dir_b.upper()

                matched += 1
                is_a_corr = (dir_a == act_dir)
                is_b_corr = (dir_b == act_dir)

                if is_a_corr:
                    corr_a += 1
                if is_b_corr:
                    corr_b += 1

                if dir_a == dir_b:
                    agree_cnt += 1
                    if is_a_corr:
                        agree_corr += 1
                else:
                    div_cnt += 1
                    if is_a_corr:
                        div_corr_a += 1
                    if is_b_corr:
                        div_corr_b += 1

                # Win / Loss / Concordance
                if is_a_corr and not is_b_corr:
                    a_wins += 1
                elif is_b_corr and not is_a_corr:
                    b_wins += 1
                elif is_a_corr and is_b_corr:
                    both_corr += 1
                else:
                    both_incorr += 1

        agr_rate = round(agree_cnt / matched, 4) if matched > 0 else None
        agr_acc = round(agree_corr / agree_cnt, 4) if agree_cnt > 0 else None
        div_rate = round(div_cnt / matched, 4) if matched > 0 else None
        div_acc_a = round(div_corr_a / div_cnt, 4) if div_cnt > 0 else None
        div_acc_b = round(div_corr_b / div_cnt, 4) if div_cnt > 0 else None

        acc_a = (corr_a / matched) if matched > 0 else None
        acc_b = (corr_b / matched) if matched > 0 else None
        delta = round(acc_a - acc_b, 4) if (acc_a is not None and acc_b is not None) else None

        return PairwiseComparison(
            model_a=model_a,
            model_b=model_b,
            matched_sessions=matched,
            agreement_count=agree_cnt,
            agreement_rate=agr_rate,
            agreement_accuracy=agr_acc,
            divergence_count=div_cnt,
            divergence_rate=div_rate,
            divergence_accuracy_a=div_acc_a,
            divergence_accuracy_b=div_acc_b,
            model_a_superior_count=a_wins,
            model_b_superior_count=b_wins,
            both_correct_count=both_corr,
            both_incorrect_count=both_incorr,
            accuracy_delta=delta,
        )
