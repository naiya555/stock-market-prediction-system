"""Historical Evaluation Data-Readiness Audit CLI (Day 60).

Runs the comprehensive data-readiness audit to evaluate whether the repository contains
sufficient, reliable, point-in-time historical data to evaluate ML-only predictions
against an LLM-assisted or blended approach.
"""

from pathlib import Path
import sys

# Configure UTF-8 encoding on Windows if supported
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure project root is in sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.history.data_readiness import audit_repository_data_readiness


def run_audit() -> None:
    """Execute audit and print structured findings."""
    report = audit_repository_data_readiness(root_dir=project_root)

    print("=" * 100)
    print("DAY 60: HISTORICAL EVALUATION DATA-READINESS AUDIT REPORT")
    print("=" * 100)
    print(f"Workspace Root:                 {project_root}")
    print(f"ML-Only Evaluation Readiness:   {report.ml_evaluation_readiness.value}")
    print(f"LLM-Only Evaluation Readiness:  {report.llm_evaluation_readiness.value}")
    print(f"Blended Evaluation Readiness:   {report.blended_evaluation_readiness.value}")
    print(f"Reproducible ML Holdout Size:   N = {report.reproducible_ml_sessions} sessions")
    print(f"Reproducible Models:            {', '.join(report.reproducible_ml_models)}")
    print("-" * 100)

    print("\nDATASET & PROVIDER INVENTORY:")
    print("-" * 100)
    for idx, item in enumerate(report.inventory, 1):
        print(f"[{idx}] {item.name}")
        print(f"    Location:           {item.storage_location}")
        print(f"    Topic/Instrument:   {item.instrument_or_topic}")
        print(f"    Coverage Range:     {item.earliest_timestamp or 'N/A'} to {item.latest_timestamp or 'N/A'}")
        print(f"    Record Count:       {item.record_count}")
        print(f"    Point-in-Time:      {'VERIFIED' if item.is_point_in_time_verified else 'UNVERIFIED / EPHEMERAL'}")
        print(f"    Readiness Status:   {item.readiness_status.value}")
        print(f"    Notes:              {item.notes}")
        print()

    print("=" * 100)
    print("MISSING HISTORICAL EVALUATION PREREQUISITES:")
    print("=" * 100)
    for idx, prereq in enumerate(report.missing_prerequisites, 1):
        print(f"  {idx}. {prereq}")

    print("\n" + "=" * 100)
    print("RECOMMENDED NEXT STEPS & BOUNDED ROADMAP ACTIONS:")
    print("=" * 100)
    for idx, step in enumerate(report.recommended_next_steps, 1):
        print(f"  {idx}. {step}")
    print("=" * 100)


if __name__ == "__main__":
    run_audit()
