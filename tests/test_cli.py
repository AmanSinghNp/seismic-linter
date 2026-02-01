import subprocess
import sys
from pathlib import Path



def run_cli(args, cwd, tmp_path):
    """Run CLI and return (returncode, stdout, stderr). Uses file redirection."""
    out_file = tmp_path / "stdout.txt"
    err_file = tmp_path / "stderr.txt"
    
    # Ensure fresh files
    # Ensure fresh files
    if out_file.exists():
        out_file.unlink()
    if err_file.exists():
        err_file.unlink()

    with open(out_file, "w", encoding="utf-8") as out, open(
        err_file, "w", encoding="utf-8"
    ) as err:
        result = subprocess.run(
            args,
            stdout=out,
            stderr=err,
            text=True,
            cwd=cwd,
            env={
                 **sys.modules["os"].environ,
                 "PYTHONPATH": str(Path.cwd() / "src"),
                 "PYTHONIOENCODING": "utf-8",
            }
        )
    
    stdout = out_file.read_text(encoding="utf-8") if out_file.exists() else ""
    stderr = err_file.read_text(encoding="utf-8") if err_file.exists() else ""
    return result.returncode, stdout, stderr


def test_cli_version(tmp_path):
    """Test that the CLI runs and outputs version."""
    rc, out, err = run_cli(
        [sys.executable, "-m", "seismic_linter.cli", "--version"],
        Path.cwd(),
        tmp_path
    )
    assert rc == 0
    assert "seismic-linter" in out


def test_cli_help(tmp_path):
    """Test that the CLI help command works."""
    rc, out, err = run_cli(
        [sys.executable, "-m", "seismic_linter.cli", "--help"],
        Path.cwd(),
        tmp_path
    )
    assert rc == 0
    assert "Detect temporal causality violations" in out


def test_cli_single_file(tmp_path):
    """CLI runs on a single file path and reports."""
    py_file = tmp_path / "single.py"
    py_file.write_text("x = 1", encoding="utf-8")

    rc, out, err = run_cli(
        [sys.executable, "-m", "seismic_linter.cli", str(py_file)],
        Path.cwd(),
        tmp_path
    )
    assert rc == 0, f"Failed with {rc}. Stderr: {err}"
    assert "No violations" in out or str(py_file) in out


def test_cli_worker_error_path(tmp_path):
    """CLI surfaces worker crash as E000 violation and error message."""
    # Invalid JSON notebook causes parse_notebook to raise in worker
    bad_nb = tmp_path / "bad.ipynb"
    bad_nb.write_text("not valid json", encoding="utf-8")

    rc, out, err = run_cli(
        [sys.executable, "-m", "seismic_linter.cli", str(tmp_path)],
        Path.cwd(),
        tmp_path
    )

    # We expect E000 in stdout OR "Analysis failed" in stdout (due to synthesized violation)
    # AND non-zero exit because of error severity

    assert "E000" in out or "Analysis failed" in out, (
        f"Stdout was: {out!r}\nStderr was: {err!r}"
    )
    assert rc != 0, f"Expected failure but got {rc}\nStdout: {out!r}\nStderr: {err!r}"


def test_cli_ignore_normalizes_whitespace(tmp_path):
    """CLI --ignore with spaces still matches rule IDs (T001 ignored)."""
    py_file = tmp_path / "leaky.py"
    py_file.write_text(
        "import pandas as pd\n"
        "df = pd.DataFrame({'x': [1,2,3]})\n"
        "print(df['x'].mean())",
        encoding="utf-8",
    )
    rc, out, err = run_cli(
        [
            sys.executable,
            "-m",
            "seismic_linter.cli",
            "--ignore",
            " T001 ",
            "--no-fail-on-error",
            str(py_file),
        ],
        Path.cwd(),
        tmp_path
    )
    assert rc == 0, f"Failed: {err}"
    assert "T001" not in out, "T001 should be ignored when passed as ' T001 '"


def test_cli_stress_torture(tmp_path):
    """Ensure the linter doesn't crash on complex valid Python code."""
    # We must assume tests/data/torture.py exists relative to CWD
    torture_file = Path("tests/data/torture.py")
    if not torture_file.exists():
        # Fallback for when running from elsewhere? 
        # But we assume running from project root.
        # But we assume running from project root.
        import pytest

        pytest.skip("tests/data/torture.py not found")

    rc, out, err = run_cli(
        [sys.executable, "-m", "seismic_linter.cli", str(torture_file)],
        Path.cwd(),
        tmp_path
    )
    assert rc == 0, f"Torture test failed/crashed: {err}"


def test_print_formatting(capsys, tmp_path):
    """Unit test for output formatters."""
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
    import json

    data = json.loads(captured.out)
    assert len(data) == 1
    assert data[0]["rule_id"] == "T001"

    # GitHub
    print_github(violations, fatal)
    captured = capsys.readouterr()
    assert "::warning file=test.py,line=10::T001: Test Message" in captured.out

    # Text
    print_text({"test.py": violations}, set(), set())
    captured = capsys.readouterr()
    assert "⚠️ [Line 10] T001: Test Message" in captured.out




