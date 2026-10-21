"""Day 49: Non-Destructive Backup & Restore Verification Drill.

Executes Section 5.4 of docs/deployment-runbook.md in an isolated temporary
environment with disposable database copies.
Verifies:
1. Protected files (data/predictions.db, models/.gitkeep) are hashed before and after.
2. Zero mutation on existing development and model files.
3. Online SQLite backup captures WAL pages without locking.
4. Integrity checks on backup and restored databases return 'ok'.
5. Restoration into ephemeral sandbox confirms table structure and row counts.
"""

import hashlib
import os
from pathlib import Path
import sqlite3
import sys
import tempfile

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def compute_sha256(path: Path) -> str:
    if not path.exists():
        return "MISSING"
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def run_drill():
    print("=" * 70)
    print("DAY 49: NON-DESTRUCTIVE BACKUP & RESTORE VERIFICATION DRILL")
    print("=" * 70)

    dev_db_path = PROJECT_ROOT / "data" / "predictions.db"
    model_keep_path = PROJECT_ROOT / "models" / ".gitkeep"

    # Step 1: Pre-drill SHA-256 baseline
    db_hash_before = compute_sha256(dev_db_path)
    model_hash_before = compute_sha256(model_keep_path)
    print(f"[1] Pre-Drill Protected File Hashes:")
    print(f"    - data/predictions.db: {db_hash_before}")
    print(f"    - models/.gitkeep:     {model_hash_before}")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        source_db = temp_path / "live_simulated.db"
        backup_db = temp_path / "backup_snapshot.db"
        restore_db = temp_path / "restored_verify.db"

        print(f"\n[2] Setting up disposable isolated database in:")
        print(f"    {temp_path}")

        # Seed isolated database with production-like schema & WAL mode
        src_conn = sqlite3.connect(source_db)
        try:
            src_conn.execute("PRAGMA journal_mode=WAL;")
            src_conn.execute("""
                CREATE TABLE predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    prediction_date TEXT NOT NULL,
                    predicted_direction TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    horizon_days INTEGER NOT NULL
                );
            """)
            src_conn.execute("""
                CREATE TABLE model_releases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_name TEXT NOT NULL,
                    candidate_tag TEXT NOT NULL,
                    promoted_at TEXT NOT NULL,
                    training_cutoff TEXT NOT NULL,
                    status TEXT NOT NULL
                );
            """)
            src_conn.execute(
                "INSERT INTO predictions (symbol, prediction_date, predicted_direction, confidence, horizon_days) "
                "VALUES ('RELIANCE.NS', '2026-10-21', 'UP', 0.82, 5), "
                "       ('TCS.NS', '2026-10-21', 'DOWN', 0.65, 5);"
            )
            src_conn.execute(
                "INSERT INTO model_releases (model_name, candidate_tag, promoted_at, training_cutoff, status) "
                "VALUES ('xgboost_direction', 'cand-20261021-01', '2026-10-21T06:00:00Z', '2026-10-15', 'active');"
            )
            src_conn.commit()

            # Check WAL file exists
            wal_file = temp_path / "live_simulated.db-wal"
            print(f"    - Source DB created. WAL active: {wal_file.exists()}")

            # Step 3: Execute Online Backup (Section 5.2 / 5.4)
            print(f"\n[3] Executing SQLite Online Backup to disposable backup destination...")
            bck_conn = sqlite3.connect(backup_db)
            try:
                src_conn.backup(bck_conn)
            finally:
                bck_conn.close()
            print(f"    - Backup created: {backup_db.name} ({backup_db.stat().st_size} bytes)")
        finally:
            src_conn.close()

        # Step 4: Run in-place integrity check on backup file (Section 5.4 step 2)
        print(f"\n[4] Running PRAGMA integrity_check on backup snapshot...")
        bck_conn = sqlite3.connect(backup_db)
        try:
            integrity_result = bck_conn.execute("PRAGMA integrity_check;").fetchone()
            print(f"    - PRAGMA integrity_check result: {integrity_result[0]}")
            assert integrity_result[0] == "ok", f"Integrity check failed: {integrity_result}"
        finally:
            bck_conn.close()

        # Step 5: Isolated dry-run restore drill (Section 5.4 step 3)
        print(f"\n[5] Executing isolated dry-run restore into ephemeral verify database...")
        restore_db.write_bytes(backup_db.read_bytes())
        print(f"    - Restored file created: {restore_db.name} ({restore_db.stat().st_size} bytes)")

        res_conn = sqlite3.connect(restore_db)
        try:
            res_integrity = res_conn.execute("PRAGMA integrity_check;").fetchone()
            print(f"    - Restored PRAGMA integrity_check result: {res_integrity[0]}")
            assert res_integrity[0] == "ok"

            pred_cnt = res_conn.execute("SELECT count(*) FROM predictions;").fetchone()[0]
            rel_cnt = res_conn.execute("SELECT count(*) FROM model_releases;").fetchone()[0]
            print(f"    - Restored row counts: predictions={pred_cnt}, model_releases={rel_cnt}")
            assert pred_cnt == 2, f"Expected 2 predictions, got {pred_cnt}"
            assert rel_cnt == 1, f"Expected 1 model_release, got {rel_cnt}"
        finally:
            res_conn.close()

        print("\n[6] Ephemeral sandbox verification successful. Cleaning up temp directory...")

    # Step 7: Post-drill SHA-256 verification of protected files
    db_hash_after = compute_sha256(dev_db_path)
    model_hash_after = compute_sha256(model_keep_path)
    print(f"\n[7] Post-Drill Protected File Hashes:")
    print(f"    - data/predictions.db: {db_hash_after}")
    print(f"    - models/.gitkeep:     {model_hash_after}")

    assert db_hash_before == db_hash_after, "FATAL: data/predictions.db was modified during drill!"
    assert model_hash_before == model_hash_after, "FATAL: models/.gitkeep was modified during drill!"

    print("\n[8] Non-Destructive Guarantee: VERIFIED. Protected files remain 100% UNTOUCHED.")
    print("=" * 70)


if __name__ == "__main__":
    run_drill()
