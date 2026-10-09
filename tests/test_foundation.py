"""Day 1 Foundation Tests.

Validates that:
- Python environment and project structure are sound.
- Core packages can be imported cleanly.
- main() runs successfully and returns status 0.
"""

from pathlib import Path
import app
import main


def test_core_package_import():
    """Verify that the app package imports and has a valid version."""
    assert hasattr(app, "__version__")
    assert isinstance(app.__version__, str)


def test_main_execution(capsys):
    """Verify that main() executes cleanly and outputs readiness message."""
    exit_code = main.main()
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Stock Market Prediction System" in captured.out
    assert "Day 1 environment ready" in captured.out


def test_required_project_directories_exist():
    """Verify the presence of all foundational project directories."""
    project_root = Path(__file__).resolve().parent.parent

    required_dirs = [
        project_root / "app",
        project_root / "app" / "core",
        project_root / "app" / "api",
        project_root / "app" / "database",
        project_root / "app" / "market",
        project_root / "app" / "news",
        project_root / "app" / "nlp",
        project_root / "app" / "prediction",
        project_root / "app" / "training",
        project_root / "app" / "history",
        project_root / "data" / "raw",
        project_root / "data" / "processed",
        project_root / "data" / "cache",
        project_root / "models",
        project_root / "docs",
        project_root / "tests",
    ]

    for directory in required_dirs:
        assert directory.is_dir(), f"Expected directory does not exist: {directory}"


def test_no_forbidden_day1_mock_data():
    """Ensure no fake market data or mock models were accidentally introduced."""
    project_root = Path(__file__).resolve().parent.parent

    # Raw and processed data directories should contain no data files on Day 1
    raw_files = [f for f in (project_root / "data" / "raw").iterdir() if f.name != ".gitkeep"]
    processed_files = [f for f in (project_root / "data" / "processed").iterdir() if f.name not in (".gitkeep", "charts")]
    model_files = [f for f in (project_root / "models").iterdir() if f.name != ".gitkeep"]

    assert len(raw_files) == 0, f"Found unexpected raw data files: {raw_files}"
    assert len(processed_files) == 0, f"Found unexpected processed data files: {processed_files}"
    assert len(model_files) == 0, f"Found unexpected model files: {model_files}"
