"""Outcome Verification Service for Phase 7.

Validates persisted stock-direction predictions against realized market sessions,
computes forward return and directional labels according to the canonical target definition,
enforces strict anti-leakage temporal bounds, and persists immutable actual outcomes.
"""

from datetime import datetime, timedelta, timezone
import math
from typing import Any, Dict, List, Optional, Sequence, Union

from app.core.logging_config import get_logger
from app.core.schemas import MarketOHLCV
from app.database.repository import PredictionRepository
from app.history.contract import (
    ActualOutcome,
    VerificationRecord,
    VerificationStatus,
)
from app.market.cleaner import clean_market_data
from app.market.providers.base import BaseMarketDataProvider
from app.market.providers.yfinance_provider import YFinanceProvider
from app.prediction.target import (
    calculate_forward_return,
    classify_forward_direction,
)

logger = get_logger(__name__)


def parse_session_date(dt_val: Union[str, datetime]) -> datetime.date:
    """Extract calendar session date from ISO string or datetime object."""
    if isinstance(dt_val, datetime):
        return dt_val.date()
    if isinstance(dt_val, str):
        # Support ISO 8601 strings (e.g. '2026-10-14T00:00:00+05:30', '2026-10-14')
        clean_str = dt_val.strip()
        if "T" in clean_str:
            clean_str = clean_str.split("T")[0]
        elif " " in clean_str:
            clean_str = clean_str.split(" ")[0]
        return datetime.strptime(clean_str, "%Y-%m-%d").date()
    raise TypeError(f"Cannot parse date from {type(dt_val).__name__}: {dt_val!r}")


class OutcomeVerifier:
    """Service verifying saved predictions against realized market outcomes."""

    def __init__(
        self,
        repository: PredictionRepository,
        provider: Optional[BaseMarketDataProvider] = None,
    ) -> None:
        """Initialize verifier with database repository and optional data provider."""
        self.repository = repository
        self.provider = provider or YFinanceProvider()

    def verify_prediction(
        self,
        prediction: Union[str, Dict[str, Any]],
        market_bars: Optional[Sequence[MarketOHLCV]] = None,
        persist: bool = True,
    ) -> VerificationRecord:
        """Verify an individual prediction against actual market data.

        Args:
            prediction: Prediction ID string or prediction dictionary.
            market_bars: Optional pre-fetched market bars. If None, fetched via provider.
            persist: Whether to save the verified outcome to the actuals table.

        Returns:
            VerificationRecord detailing verification status, actual outcome, and correctness.
        """
        # 1. Resolve prediction record
        if isinstance(prediction, str):
            pred_record = self.repository.get_prediction(prediction)
            if pred_record is None:
                return VerificationRecord(
                    prediction_id=prediction,
                    symbol="UNKNOWN",
                    status=VerificationStatus.INELIGIBLE,
                    predicted_direction=None,
                    predicted_label=None,
                    message=f"Prediction '{prediction}' not found in database.",
                )
        elif isinstance(prediction, dict):
            pred_record = prediction
        else:
            raise TypeError(f"Expected prediction_id or dict, got {type(prediction).__name__}")

        pid = str(pred_record.get("prediction_id", ""))
        symbol = str(pred_record.get("symbol", "")).strip().upper()
        status = pred_record.get("status")
        pred_dir = pred_record.get("predicted_direction")
        pred_label = pred_record.get("predicted_label")

        # 2. Check eligibility
        if status != "SUCCESS" or not pred_dir or pred_label is None:
            return VerificationRecord(
                prediction_id=pid,
                symbol=symbol,
                status=VerificationStatus.INELIGIBLE,
                predicted_direction=pred_dir,
                predicted_label=pred_label,
                message=f"Prediction status is '{status}'; only SUCCESS predictions with direction are eligible.",
            )

        latest_input_ts = pred_record.get("latest_input_timestamp")
        if not latest_input_ts:
            return VerificationRecord(
                prediction_id=pid,
                symbol=symbol,
                status=VerificationStatus.INELIGIBLE,
                predicted_direction=pred_dir,
                predicted_label=pred_label,
                message="Prediction is missing latest_input_timestamp.",
            )

        try:
            ref_date = parse_session_date(latest_input_ts)
        except Exception as exc:
            return VerificationRecord(
                prediction_id=pid,
                symbol=symbol,
                status=VerificationStatus.INELIGIBLE,
                predicted_direction=pred_dir,
                predicted_label=pred_label,
                message=f"Invalid latest_input_timestamp '{latest_input_ts}': {exc}",
            )

        # 3. Check if outcome is already verified in database
        existing_actual = self.repository.get_actual(pid)
        if existing_actual is not None:
            act_dir = existing_actual["actual_direction"]
            act_label = existing_actual["actual_label"]
            is_corr = (pred_dir == act_dir)
            return VerificationRecord(
                prediction_id=pid,
                symbol=symbol,
                status=VerificationStatus.ALREADY_VERIFIED,
                predicted_direction=pred_dir,
                predicted_label=pred_label,
                actual_direction=act_dir,
                actual_label=act_label,
                target_date=existing_actual["target_date"],
                actual_return=existing_actual["actual_return"],
                actual_close=existing_actual["actual_close"],
                reference_close=existing_actual.get("reference_close"),
                is_correct=is_corr,
                message="Actual outcome already verified and recorded in database.",
            )

        # 4. Acquire and clean market bars
        bars: List[MarketOHLCV] = []
        if market_bars is not None:
            bars = list(market_bars)
        else:
            try:
                # Fetch window around reference date plus forward cushion for target session
                start_dt = datetime(ref_date.year, ref_date.month, ref_date.day, tzinfo=timezone.utc) - timedelta(days=7)
                end_dt = datetime.now(timezone.utc) + timedelta(days=1)
                raw_bars = self.provider.fetch_historical_ohlcv(symbol, start_date=start_dt, end_date=end_dt)
                cleaned = clean_market_data(raw_bars)
                bars = cleaned.cleaned_records
            except Exception as exc:
                logger.error("Failed to fetch market data for verification of %s (%s): %s", symbol, pid, exc)
                return VerificationRecord(
                    prediction_id=pid,
                    symbol=symbol,
                    status=VerificationStatus.DATA_UNAVAILABLE,
                    predicted_direction=pred_dir,
                    predicted_label=pred_label,
                    message=f"Market data provider error: {exc}",
                )

        if not bars:
            return VerificationRecord(
                prediction_id=pid,
                symbol=symbol,
                status=VerificationStatus.DATA_UNAVAILABLE,
                predicted_direction=pred_dir,
                predicted_label=pred_label,
                message=f"No market bars returned for symbol '{symbol}'.",
            )

        # Ensure bars are chronologically sorted
        bars.sort(key=lambda b: b.timestamp)

        # 5. Locate reference session t
        ref_idx: Optional[int] = None
        for i, b in enumerate(bars):
            if parse_session_date(b.timestamp) == ref_date:
                ref_idx = i
                break

        if ref_idx is None:
            return VerificationRecord(
                prediction_id=pid,
                symbol=symbol,
                status=VerificationStatus.DATA_UNAVAILABLE,
                predicted_direction=pred_dir,
                predicted_label=pred_label,
                message=f"Reference session date '{ref_date}' not found in available market bars.",
            )

        ref_bar = bars[ref_idx]
        ref_close = ref_bar.close

        # 6. Locate target session t+1
        if ref_idx + 1 >= len(bars):
            # Target session has not occurred yet
            return VerificationRecord(
                prediction_id=pid,
                symbol=symbol,
                status=VerificationStatus.PENDING,
                predicted_direction=pred_dir,
                predicted_label=pred_label,
                reference_close=ref_close,
                message=f"Target session following {ref_date} has not yet closed. Outcome is pending.",
            )

        target_bar = bars[ref_idx + 1]
        target_close = target_bar.close
        target_date_str = target_bar.timestamp.isoformat()

        # 7. Compute target return and direction using canonical definition
        fwd_return = calculate_forward_return(ref_close, target_close)
        if fwd_return is None or not math.isfinite(fwd_return):
            return VerificationRecord(
                prediction_id=pid,
                symbol=symbol,
                status=VerificationStatus.DATA_UNAVAILABLE,
                predicted_direction=pred_dir,
                predicted_label=pred_label,
                reference_close=ref_close,
                message="Non-positive or non-finite prices encountered calculating return.",
            )

        actual_dir, actual_lbl = classify_forward_direction(fwd_return)
        if actual_dir is None or actual_lbl is None:
            return VerificationRecord(
                prediction_id=pid,
                symbol=symbol,
                status=VerificationStatus.DATA_UNAVAILABLE,
                predicted_direction=pred_dir,
                predicted_label=pred_label,
                reference_close=ref_close,
                message="Unable to classify forward direction from return.",
            )

        # 8. Construct ActualOutcome
        outcome = ActualOutcome(
            prediction_id=pid,
            symbol=symbol,
            target_date=target_date_str,
            actual_direction=actual_dir,
            actual_label=actual_lbl,
            actual_return=round(fwd_return, 6),
            actual_close=target_close,
            reference_close=ref_close,
            source=target_bar.source,
            recorded_at=datetime.now(timezone.utc).isoformat(),
        )

        # 9. Persist outcome if requested
        if persist:
            try:
                self.repository.save_actual(outcome)
            except ValueError as exc:
                if "Conflicting" in str(exc):
                    return VerificationRecord(
                        prediction_id=pid,
                        symbol=symbol,
                        status=VerificationStatus.CONFLICT,
                        predicted_direction=pred_dir,
                        predicted_label=pred_label,
                        actual_direction=actual_dir,
                        actual_label=actual_lbl,
                        target_date=target_date_str,
                        actual_return=outcome.actual_return,
                        actual_close=target_close,
                        reference_close=ref_close,
                        message=str(exc),
                    )
                raise

        is_correct = (pred_dir == actual_dir)
        return VerificationRecord(
            prediction_id=pid,
            symbol=symbol,
            status=VerificationStatus.VERIFIED,
            predicted_direction=pred_dir,
            predicted_label=pred_label,
            actual_direction=actual_dir,
            actual_label=actual_lbl,
            target_date=target_date_str,
            actual_return=outcome.actual_return,
            actual_close=target_close,
            reference_close=ref_close,
            is_correct=is_correct,
            message="Outcome verified successfully against realized market session.",
        )

    def verify_all_pending(
        self,
        symbol: Optional[str] = None,
        market_bars_by_symbol: Optional[Dict[str, Sequence[MarketOHLCV]]] = None,
        persist: bool = True,
    ) -> List[VerificationRecord]:
        """Verify all eligible predictions that currently lack an actuals record.

        Args:
            symbol: Optional stock symbol filter.
            market_bars_by_symbol: Optional dictionary mapping symbol -> pre-fetched bars.
            persist: Whether to save verified outcomes to actuals table.

        Returns:
            List of VerificationRecord for each processed prediction.
        """
        pending_preds = self.repository.list_predictions_with_actuals(
            symbol=symbol,
            pending_only=True,
            limit=10000,
        )

        results: List[VerificationRecord] = []
        for pred in pending_preds:
            sym = pred["symbol"]
            bars = None
            if market_bars_by_symbol and sym in market_bars_by_symbol:
                bars = market_bars_by_symbol[sym]

            record = self.verify_prediction(pred, market_bars=bars, persist=persist)
            results.append(record)

        return results
