"""Dependency Vulnerability and Integrity Audit Runner.

Executes local dependency consistency verification (`pip check`) and, if available,
runs `pip-audit` against `requirements.txt`. Reports package names, advisory details,
and remediation guidance.
"""

import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple


def run_pip_check() -> Tuple[bool, str]:
    """Execute `pip check` to verify internal dependency constraints."""
    cmd = [sys.executable, "-m", "pip", "check"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        output = proc.stdout.strip() if proc.stdout else proc.stderr.strip()
        return (proc.returncode == 0, output)
    except Exception as exc:
        return (False, f"Failed to run pip check: {exc}")


def is_pip_audit_installed() -> bool:
    """Check if `pip-audit` is installed in the current Python environment."""
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pip_audit", "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        return proc.returncode == 0
    except Exception:
        return False


def run_pip_audit(requirements_path: Optional[Path] = None) -> Tuple[int, str]:
    """Execute `pip-audit` against the given requirements file."""
    req_file = requirements_path or (Path(__file__).resolve().parent.parent / "requirements.txt")
    if not req_file.exists():
        return (1, f"Requirements file not found at: {req_file}")

    cmd = [
        sys.executable,
        "-m",
        "pip_audit",
        "-r",
        str(req_file),
        "--desc",
        "on",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        out = (proc.stdout or "") + (proc.stderr or "")
        return (proc.returncode, out.strip())
    except Exception as exc:
        return (1, f"Failed to execute pip-audit: {exc}")


def perform_dependency_audit(requirements_path: Optional[Path] = None) -> Dict[str, Any]:
    """Run full dependency audit returning structured status dictionary."""
    req_file = requirements_path or (Path(__file__).resolve().parent.parent / "requirements.txt")
    pip_check_ok, pip_check_out = run_pip_check()
    has_audit = is_pip_audit_installed()

    results: Dict[str, Any] = {
        "pip_check_passed": pip_check_ok,
        "pip_check_output": pip_check_out,
        "pip_audit_available": has_audit,
        "requirements_file": str(req_file),
        "vulnerabilities_detected": False,
        "audit_output": "",
        "status": "ok" if pip_check_ok else "failed",
    }

    if has_audit:
        code, audit_out = run_pip_audit(req_file)
        results["audit_output"] = audit_out
        results["vulnerabilities_detected"] = (code != 0)
        if code != 0:
            results["status"] = "vulnerable"
    else:
        results["audit_output"] = (
            "pip-audit is not installed in the local environment. "
            "To run local vulnerability scanning: pip install pip-audit && pip-audit -r requirements.txt. "
            "Automated vulnerability scanning is configured in CI via .github/workflows/ci.yml."
        )

    return results


def main() -> int:
    """CLI entry point for dependency audit runner."""
    print("=" * 70)
    print("DEPENDENCY INTEGRITY & VULNERABILITY AUDIT")
    print("=" * 70)

    report = perform_dependency_audit()

    print(f"\n[1/2] Dependency Integrity (pip check):")
    if report["pip_check_passed"]:
        print("  PASS: All package constraints and dependencies are satisfied.")
    else:
        print(f"  FAIL: {report['pip_check_output']}")

    print(f"\n[2/2] Vulnerability Scanning (pip-audit):")
    if report["pip_audit_available"]:
        print(report["audit_output"])
        if report["vulnerabilities_detected"]:
            print("\nWARNING: Vulnerabilities detected in dependency scan.")
            return 1
        print("  PASS: Zero vulnerabilities detected.")
    else:
        print(f"  NOTICE: {report['audit_output']}")

    print("\n" + "=" * 70)
    return 0 if report["pip_check_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
