import json
import sys
from unittest.mock import patch

import nbformat
import pytest

from seismic_linter.cli import collect_files, main


def _run(args, cwd, monkeypatch, capsys):
    monkeypatch.chdir(cwd)
    with patch.object(sys, "argv", ["seismic-linter"] + args):
        try:
            main()
            rc = 0
        except SystemExit as e:
            rc = e.code if e.code is not None else 0
    captured = capsys.readouterr()
    return rc, captured.out, captured.err


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "proj"
    for rel in [
        "src/a.py",
        "src/sub/b.py",
        "notebooks/eda.ipynb",
        "scripts/c.py",
        "tests/test_x.py",
        "README.md",
    ]:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("x = 1\n", encoding="utf-8")
    return root


def test_collect_files_respects_include_and_exclude(project):
    config = {
        "include": ["src", "notebooks/*.ipynb"],
        "exclude": ["tests"],
    }

    files = collect_files(project, config)

    assert files == sorted(
        [
            project / "src" / "a.py",
            project / "src" / "sub" / "b.py",
            project / "notebooks" / "eda.ipynb",
        ]
    )


def test_collect_files_named_file_include(project):
    files = collect_files(project, {"include": ["scripts/c.py", "missing.py"]})

    assert files == [project / "scripts" / "c.py"]


def test_collect_files_without_include_skips_other_extensions(project):
    files = collect_files(project, {"exclude": ["tests", "notebooks"]})

    assert project / "README.md" not in files
    assert project / "tests" / "test_x.py" not in files
    assert project / "scripts" / "c.py" in files


def test_collect_files_single_file_base(project):
    target = project / "src" / "a.py"

    assert collect_files(target, {}) == [target]
    assert collect_files(target, {"include": ["src"]}) == [target]


def test_cli_reports_when_no_supported_files(tmp_path, monkeypatch, capsys):
    (tmp_path / "notes.txt").write_text("hello", encoding="utf-8")

    rc, out, _ = _run([str(tmp_path)], tmp_path, monkeypatch, capsys)

    assert rc == 0
    assert "No Python or Jupyter files to analyze." in out


def test_cli_second_run_uses_cache(tmp_path, monkeypatch, capsys):
    py_file = tmp_path / "leaky.py"
    py_file.write_text("df.mean()\n", encoding="utf-8")
    args = ["--output", "json", "--no-fail-on-error", str(py_file)]

    rc1, out1, _ = _run(args, tmp_path, monkeypatch, capsys)
    with patch(
        "seismic_linter.cli.process_file_wrapper",
        side_effect=AssertionError("worker should not run for cached file"),
    ):
        rc2, out2, _ = _run(args, tmp_path, monkeypatch, capsys)

    assert rc1 == rc2 == 0
    assert json.loads(out1) == json.loads(out2)
    assert json.loads(out2)[0]["rule_id"] == "T001"


def _write_two_cell_notebook(path):
    nb = nbformat.v4.new_notebook()
    nb.cells = [
        nbformat.v4.new_code_cell(source="import pandas as pd"),
        nbformat.v4.new_code_cell(source="model.fit(df)"),
    ]
    with open(path, "w", encoding="utf-8") as f:
        nbformat.write(nb, f)


def test_cli_text_output_shows_cell_location(tmp_path, monkeypatch, capsys):
    nb_path = tmp_path / "eda.ipynb"
    _write_two_cell_notebook(nb_path)

    rc, out, _ = _run(
        ["--no-fail-on-error", str(nb_path)], tmp_path, monkeypatch, capsys
    )

    assert rc == 0
    assert "[Cell 2, Line 1] T002" in out


def test_cli_github_output_marks_info_as_notice(tmp_path, monkeypatch, capsys):
    nb_path = tmp_path / "eda.ipynb"
    _write_two_cell_notebook(nb_path)

    rc, out, _ = _run(
        ["--output", "github", "--no-fail-on-error", str(nb_path)],
        tmp_path,
        monkeypatch,
        capsys,
    )

    assert rc == 0
    assert "::notice file=eda.ipynb,line=1::[Cell 2] T002" in out
