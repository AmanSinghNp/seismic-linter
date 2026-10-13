import json
import sys
from pathlib import Path
from unittest.mock import patch

from seismic_linter.cli import is_excluded, main


def test_is_excluded_ignores_segments_above_base(tmp_path):
    """Default excludes such as 'build' must not match the scanned tree's parents."""
    base = Path("/srv/build/project")
    excludes = [".git", "build", "venv"]

    assert not is_excluded(base / "src" / "train.py", excludes, base)
    assert not is_excluded(base / "notebooks" / "eda.ipynb", excludes, base)


def test_is_excluded_still_matches_segments_below_base():
    base = Path("/srv/project")
    excludes = ["build", "venv"]

    assert is_excluded(base / "build" / "train.py", excludes, base)
    assert is_excluded(base / "src" / "venv" / "site.py", excludes, base)


def test_is_excluded_without_base_uses_full_path():
    assert is_excluded(Path("/srv/build/project/train.py"), ["build"])


def test_cli_scans_project_located_under_build_directory(tmp_path, monkeypatch, capsys):
    """A project inside a directory named 'build' is still scanned."""
    project = tmp_path / "build" / "project"
    src = project / "src"
    src.mkdir(parents=True)
    (src / "leaky.py").write_text(
        "import pandas as pd\ndf = pd.DataFrame({'x': [1]})\nprint(df['x'].mean())\n",
        encoding="utf-8",
    )

    monkeypatch.chdir(project)
    with patch.object(
        sys,
        "argv",
        ["seismic-linter", "--output", "json", "--no-fail-on-error", str(src)],
    ):
        try:
            main()
        except SystemExit as e:
            assert e.code == 0

    data = json.loads(capsys.readouterr().out)
    assert any(v["rule_id"] == "T001" for v in data)
