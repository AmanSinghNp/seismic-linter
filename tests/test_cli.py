import sys
from pathlib import Path
from unittest.mock import patch
import pytest
import json
from seismic_linter.cli import main


def run_cli_in_process(args, cwd, monkeypatch, capsys):
    """
    Run CLI in-process by mocking sys.argv and cwd.
    Returns (exit_code, stdout, stderr).
    """
    monkeypatch.chdir(cwd)
    start_args = ["seismic-linter"] + args
    
    with patch.object(sys, "argv", start_args):
        try:
            main()
            rc = 0
        except SystemExit as e:
            rc = e.code if e.code is not None else 0
        except Exception as e:
            print(f"CLI Exception: {e}", file=sys.stderr)
            rc = 1
            
    captured = capsys.readouterr()
    return rc, captured.out, captured.err


def test_cli_version(tmp_path, monkeypatch, capsys):
    """Test that the CLI runs and outputs version."""
    rc, out, err = run_cli_in_process(["--version"], tmp_path, monkeypatch, capsys)
    assert rc == 0
    assert "seismic-linter" in out


def test_cli_help(tmp_path, monkeypatch, capsys):
    """Test that the CLI help command works."""
    rc, out, err = run_cli_in_process(["--help"], tmp_path, monkeypatch, capsys)
    assert rc == 0
    assert "Detect temporal causality violations" in out


def test_cli_single_file(tmp_path, monkeypatch, capsys):
    """CLI runs on a single file path and reports."""
    py_file = tmp_path / "single.py"
    py_file.write_text("x = 1", encoding="utf-8")

    rc, out, err = run_cli_in_process([str(py_file)], tmp_path, monkeypatch, capsys)
    assert rc == 0
    assert "No violations" in out or str(py_file) in out


def test_cli_worker_error_path(tmp_path, monkeypatch, capsys):
    """CLI surfaces worker crash as E000 violation and error message."""
    bad_nb = tmp_path / "bad.ipynb"
    bad_nb.write_text("not valid json", encoding="utf-8")

    rc, out, err = run_cli_in_process([str(tmp_path)], tmp_path, monkeypatch, capsys)
    assert "E000" in out or "Analysis failed" in out
    assert rc != 0


def test_cli_ignore_normalizes_whitespace(tmp_path, monkeypatch, capsys):
    """CLI --ignore with spaces still matches rule IDs (T001 ignored)."""
    py_file = tmp_path / "leaky.py"
    py_file.write_text(
        "import pandas as pd\n"
        "df = pd.DataFrame({'x': [1,2,3]})\n"
        "print(df['x'].mean())",
        encoding="utf-8",
    )
    
    rc, out, err = run_cli_in_process(
        [
            "--ignore",
            " T001 ",
            "--no-fail-on-error",
            str(py_file),
        ],
        tmp_path,
        monkeypatch,
        capsys
    )
    
    assert rc == 0
    assert "T001" not in out


def test_cli_stress_torture(tmp_path, monkeypatch, capsys):
    """Ensure the linter doesn't crash on complex valid Python code."""
    original_cwd = Path.cwd()
    torture_file = original_cwd / "tests/data/torture.py"
    
    if not torture_file.exists():
        pytest.skip("tests/data/torture.py not found")

    rc, out, err = run_cli_in_process([str(torture_file)], tmp_path, monkeypatch, capsys)
    assert rc == 0


def test_cli_json_output(tmp_path, monkeypatch, capsys):
    """Test JSON output format."""
    py_file = tmp_path / "leaky.py"
    py_file.write_text("df.future.mean()", encoding="utf-8")

    rc, out, err = run_cli_in_process(
        ["--output", "json", "--no-fail-on-error", str(py_file)], 
        tmp_path, 
        monkeypatch, 
        capsys
    )
    
    assert rc == 0
    # Output should be valid JSON list
    data = json.loads(out)
    assert isinstance(data, list)
    assert len(data) > 0
    assert "rule_id" in data[0]


def test_cli_github_output(tmp_path, monkeypatch, capsys):
    """Test GitHub output format."""
    py_file = tmp_path / "leaky.py"
    py_file.write_text("df.future.mean()", encoding="utf-8")

    rc, out, err = run_cli_in_process(
        ["--output", "github", "--no-fail-on-error", str(py_file)], 
        tmp_path, 
        monkeypatch, 
        capsys
    )
    
    assert rc == 0
    # Should look like ::warning file=...
    assert "::" in out
    assert "file=" in out


def test_cli_fail_on_argument(tmp_path, monkeypatch, capsys):
    """Test --fail-on argument triggers exit code 1."""
    py_file = tmp_path / "leaky.py"
    py_file.write_text("print('x')", encoding="utf-8") # Safe file

    # Create a violation T001
    py_file.write_text("df.future.mean()", encoding="utf-8")

    rc, out, err = run_cli_in_process(
        ["--fail-on", "T001", str(py_file)], 
        tmp_path, 
        monkeypatch, 
        capsys
    )
    
    assert rc == 1


def test_cli_missing_path(tmp_path, monkeypatch, capsys):
    """Test non-existent path argument."""
    rc, out, err = run_cli_in_process(["arglebargle"], tmp_path, monkeypatch, capsys)
    assert rc == 1
    assert "does not exist" in err


def test_print_formatting_unit(capsys):
    """Unit test for output formatters (direct call coverage)."""
    from seismic_linter.cli import print_json, print_github, print_text
    from seismic_linter.rules import Violation

    v = Violation(
        rule_id="T001",
        message="Test Message",
        filename="test.py",
        lineno=10,
        col_offset=5,
        severity="warning",
        context="ctx",
        cell_id=None,
    )
    violations = [v]
    fatal = set()

    # JSON
    print_json(violations)
    captured = capsys.readouterr()
    json.loads(captured.out)

    # GitHub
    print_github(violations, fatal)
    captured = capsys.readouterr()
    assert "::warning" in captured.out

    # Text
    print_text({"test.py": violations}, set(), set())
    captured = capsys.readouterr()
    assert "⚠️" in captured.out
