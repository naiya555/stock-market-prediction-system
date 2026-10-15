"""SQLite Database Schema Definitions and Migrations for Phase 6.

Defines tables for:
- stocks: Indian equities metadata and tracking status.
- model_versions: Serialized model configurations and provenance.
- predictions: Immutable prediction audit records with native SQLite triggers preventing mutation.
- actuals: Realized market outcomes linked to past predictions for Phase 7 accuracy tracking.
"""

import sqlite3

SCHEMA_SQL = """
-- 1. Stocks Table
CREATE TABLE IF NOT EXISTS stocks (
    symbol TEXT PRIMARY KEY NOT NULL,
    company_name TEXT,
    exchange TEXT NOT NULL DEFAULT 'NSE',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

-- 2. Model Versions Table
CREATE TABLE IF NOT EXISTS model_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    hyperparameters TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(model_name, model_version)
);

-- 3. Predictions Table (Immutable)
CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prediction_id TEXT UNIQUE NOT NULL,
    symbol TEXT NOT NULL,
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    prediction_timestamp TEXT NOT NULL,
    latest_input_timestamp TEXT,
    status TEXT NOT NULL,
    predicted_direction TEXT,
    predicted_label INTEGER,
    probability_up REAL,
    probability_down REAL,
    is_probability_calibrated INTEGER NOT NULL DEFAULT 0,
    probability_calibration TEXT NOT NULL DEFAULT 'uncalibrated',
    expected_movement REAL,
    expected_movement_status TEXT NOT NULL DEFAULT 'UNSUPPORTED',
    total_bars_fetched INTEGER,
    cleaned_bars INTEGER,
    warmup_bars_required INTEGER,
    warmup_complete INTEGER,
    missing_feature_count INTEGER,
    error_message TEXT,
    disclaimer TEXT NOT NULL,
    raw_result_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (symbol) REFERENCES stocks(symbol) ON DELETE RESTRICT ON UPDATE RESTRICT
);

-- 4. Actuals Table (Realized Outcomes for Phase 7)
CREATE TABLE IF NOT EXISTS actuals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prediction_id TEXT UNIQUE NOT NULL,
    symbol TEXT NOT NULL,
    target_date TEXT NOT NULL,
    actual_direction TEXT,
    actual_label INTEGER,
    actual_return REAL,
    actual_close REAL,
    reference_close REAL,
    source TEXT DEFAULT 'yfinance',
    recorded_at TEXT NOT NULL,
    FOREIGN KEY (prediction_id) REFERENCES predictions(prediction_id) ON DELETE RESTRICT,
    FOREIGN KEY (symbol) REFERENCES stocks(symbol) ON DELETE RESTRICT
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_predictions_symbol_timestamp 
    ON predictions (symbol, prediction_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_predictions_model 
    ON predictions (model_name, model_version);

CREATE INDEX IF NOT EXISTS idx_predictions_latest_bar 
    ON predictions (symbol, latest_input_timestamp);

CREATE INDEX IF NOT EXISTS idx_actuals_symbol_date 
    ON actuals (symbol, target_date DESC);

-- Immutability Enforcement Triggers
CREATE TRIGGER IF NOT EXISTS trg_prevent_prediction_update
BEFORE UPDATE ON predictions
BEGIN
    SELECT RAISE(ABORT, 'Predictions are immutable: updates are strictly prohibited.');
END;

CREATE TRIGGER IF NOT EXISTS trg_prevent_prediction_delete
BEFORE DELETE ON predictions
BEGIN
    SELECT RAISE(ABORT, 'Predictions are immutable: deletions are strictly prohibited.');
END;

CREATE TRIGGER IF NOT EXISTS trg_prevent_actual_update
BEFORE UPDATE ON actuals
BEGIN
    SELECT RAISE(ABORT, 'Actual outcomes are immutable: updates are strictly prohibited.');
END;

CREATE TRIGGER IF NOT EXISTS trg_prevent_actual_delete
BEFORE DELETE ON actuals
BEGIN
    SELECT RAISE(ABORT, 'Actual outcomes are immutable: deletions are strictly prohibited.');
END;
"""


def initialize_database(conn: sqlite3.Connection) -> None:
    """Execute schema initialization and ensure all tables, indexes, and triggers exist."""
    conn.executescript(SCHEMA_SQL)
    # Check if existing actuals table needs column migrations
    cursor = conn.execute("PRAGMA table_info(actuals);")
    cols = {row[1] if isinstance(row, tuple) else row["name"] for row in cursor.fetchall()}
    if "reference_close" not in cols:
        conn.execute("ALTER TABLE actuals ADD COLUMN reference_close REAL;")
    if "source" not in cols:
        conn.execute("ALTER TABLE actuals ADD COLUMN source TEXT DEFAULT 'yfinance';")
    conn.commit()
