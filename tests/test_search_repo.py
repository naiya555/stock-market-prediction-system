"""Tests for scripts/search_repo.sh shell argument handling and safety.

Verifies remediation of CodeRabbit Deep Scan finding a51c3c34-6b77-4c88-9a88-69640cb653f5:
Ensures safe bash array handling for spaces, options, and wildcards without command injection.
"""

import shutil
import subprocess
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "search_repo.sh"


@pytest.fixture(scope="module")
def bash_executable():
    """Locate bash executable for invoking the script."""
    bash = shutil.which("bash")
    if not bash:
        pytest.skip("bash executable not found in PATH")
    return bash


def test_search_repo_no_args_shows_usage(bash_executable):
    """Verify invoking script with no arguments displays usage and exits with 1."""
    res = subprocess.run(
        [bash_executable, "scripts/search_repo.sh"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert res.returncode == 1
    assert "Usage: search_repo.sh" in res.stdout


def test_search_repo_spaces_in_pattern(bash_executable):
    """Verify spaces in the search pattern do not split arguments or inject commands."""
    res = subprocess.run(
        [bash_executable, "scripts/search_repo.sh", "Market Data Pipeline", "app/"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    assert "pipeline.py" in res.stdout


def test_search_repo_with_type_flag(bash_executable):
    """Verify option flags like --type py are safely parsed and forwarded."""
    res = subprocess.run(
        [bash_executable, "scripts/search_repo.sh", "MarketDataPipelineResult", "app/", "--type", "py"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    assert "pipeline.py" in res.stdout


def test_search_repo_wildcard_pattern(bash_executable):
    """Verify pattern containing wildcard characters does not undergo unintended shell expansion."""
    res = subprocess.run(
        [bash_executable, "scripts/search_repo.sh", "MarketOHLCV.*dataclass", "app/"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0


def test_search_repo_no_match(bash_executable):
    """Verify searching for a non-existent pattern gracefully reports no matches."""
    res = subprocess.run(
        [bash_executable, "scripts/search_repo.sh", "NON_EXISTENT_STRING_XYZ_999", "app/"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    assert "No matches found" in res.stdout
