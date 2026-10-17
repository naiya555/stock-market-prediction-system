"""Regression tests for log injection, CRLF forging, and control character neutralization.

Verifies remediation of CodeRabbit Deep Scan findings:
- b459745a-1494-4d4a-99ba-df6160cd8324 (app/prediction/ensemble.py)
- 75169822-10b9-4c51-87d7-2c6daa5847a4 (app/market/pipeline.py)
- 97c82693-02c8-4cc3-8a37-9737ca5dc3c7 (app/api/routes/feedback.py)
- 221fa173-c171-4128-b3f9-7e6de364fc2f (app/market/providers/yfinance_provider.py)
"""

import io
import logging
import pytest
from pydantic import ValidationError as PydanticValidationError

from app.api.schemas import FeedbackRequest, PredictRequest
from app.core.logging_config import SafeLogFormatter, sanitize_log_field


def test_sanitize_log_field_removes_crlf_and_controls():
    """Verify sanitize_log_field strips/escapes carriage returns, newlines, and non-printable chars."""
    malicious = "RELIANCE\r\nINFO:root:FORGED LOG RECORD\nSECOND LINE"
    cleaned = sanitize_log_field(malicious)

    assert "\r" not in cleaned
    assert "\n" not in cleaned
    assert "FORGED LOG RECORD" in cleaned
    assert "\\r" in cleaned or "\\n" in cleaned or "_" in cleaned


def test_safe_log_formatter_prevents_log_forging():
    """Verify SafeLogFormatter escapes newlines so untrusted input cannot create false log records."""
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(SafeLogFormatter("%(levelname)s:%(name)s:%(message)s"))

    logger = logging.getLogger("test_injection_logger")
    logger.setLevel(logging.INFO)
    logger.handlers = [handler]
    logger.propagate = False

    malicious_input = "TCS\nCRITICAL:security:ADMIN PASSWORD RESET COMPLETED"
    logger.info("Processing request for symbol: %s", malicious_input)

    output = stream.getvalue()
    lines = output.strip().splitlines()

    # The entire log entry must be exactly ONE physical line, preventing forged log entries
    assert len(lines) == 1
    assert "ADMIN PASSWORD RESET COMPLETED" in lines[0]
    assert "\\nCRITICAL" in lines[0] or "\\r" in lines[0]


@pytest.mark.parametrize(
    "invalid_symbol",
    [
        "RELIANCE\nFORGED",
        "TCS\r\n",
        "INFY\tEXTRA",
        "HDFC\x00NULL",
        "BAD SYMBOL WITH SPACES",
        "INVALID;DROP TABLE;",
        "<script>alert(1)</script>",
    ],
)
def test_predict_request_rejects_control_characters(invalid_symbol: str):
    """Verify PredictRequest schema rejects symbols containing control characters or SQL/script syntax."""
    with pytest.raises(PydanticValidationError) as exc_info:
        PredictRequest(symbol=invalid_symbol)
    assert "symbol" in str(exc_info.value).lower()


@pytest.mark.parametrize(
    "valid_symbol",
    [
        "RELIANCE",
        "TCS",
        "INFY",
        "HDFCBANK",
        "M_M",
        "^NSEI",
        "NIFTY50.NS",
    ],
)
def test_predict_request_accepts_valid_tickers(valid_symbol: str):
    """Verify PredictRequest schema accepts valid standard equity and index tickers."""
    req = PredictRequest(symbol=valid_symbol)
    assert req.symbol == valid_symbol.strip().upper()


def test_feedback_request_rejects_control_chars_in_prediction_id():
    """Verify FeedbackRequest schema rejects prediction_id with CRLF or control characters."""
    with pytest.raises(PydanticValidationError):
        FeedbackRequest(
            prediction_id="pred_123\r\nFORGED LOG",
            feedback_type="THUMBS_UP",
        )
