"""
Keeps the README examples runnable and in step with the code they document.
"""

import re
from pathlib import Path

import pandas as pd
import pytest

try:
    import tomllib
except ImportError:  # Python 3.10
    import tomli as tomllib

from seismic_linter.analyzer import analyze_code
from seismic_linter.config import load_config
from seismic_linter.rules import RULES

README = Path(__file__).resolve().parent.parent / "README.md"


def _fenced_blocks(language):
    text = README.read_text(encoding="utf-8")
    pattern = rf"```{language}\n(.*?)```"
    return re.findall(pattern, text, flags=re.DOTALL)


def _single_block(language, marker):
    matches = [b for b in _fenced_blocks(language) if marker in b]
    assert len(matches) == 1, f"expected one {language} block with {marker!r}"
    return matches[0]


def test_runtime_example_runs(tmp_path, monkeypatch):
    block = _single_block("python", "verify_monotonicity")
    monkeypatch.chdir(tmp_path)
    pd.DataFrame(
        {
            "time": pd.date_range("2019-12-28", periods=6, freq="D"),
            "mag": [2.1, 3.0, 2.5, 4.2, 3.3, 2.9],
        }
    ).to_csv("catalogue.csv", index=False)

    namespace = {}
    exec(compile(block, str(README), "exec"), namespace)

    assert list(namespace["df"].columns) == ["time", "mag"]
    assert len(namespace["train"]) == 4
    assert len(namespace["test"]) == 2


def test_inline_suppression_example_is_silent():
    block = _single_block("python", "seismic-linter: ignore")
    assert analyze_code(block) == []


def test_toml_config_example_is_recognised(tmp_path, monkeypatch):
    block = _single_block("toml", "[tool.seismic-linter]")
    (tmp_path / "pyproject.toml").write_text(block, encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    parsed = tomllib.loads(block)["tool"]["seismic-linter"]
    config = load_config(tmp_path)

    assert parsed["fail-on"] == ["T003"]
    assert config["fail_on"] == ["T003"]
    assert "T002" in config["ignore"]
    assert "tests" in config["exclude"] and ".git" in config["exclude"]
    assert config["include"] == ["src", "notebooks"]


def test_rules_table_matches_registry():
    text = README.read_text(encoding="utf-8")
    documented = set(re.findall(r"^\| \*\*(\w{4})\*\* \|", text, flags=re.MULTILINE))

    assert documented == {rule_id for rule_id in RULES if rule_id.startswith("T")}


@pytest.mark.parametrize("rule_id", ["T001", "T002", "T003"])
def test_rules_table_severity_matches_registry(rule_id):
    text = README.read_text(encoding="utf-8")
    row = next(line for line in text.splitlines() if f"**{rule_id}**" in line)
    expected = {"warning": "Warning", "info": "Info", "error": "Error"}
    assert expected[RULES[rule_id].severity] in row


def test_pre_commit_manifest_defines_documented_hook():
    yaml = pytest.importorskip("yaml")
    manifest_path = README.parent / ".pre-commit-hooks.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))

    hook = next(h for h in manifest if h["id"] == "seismic-linter")
    assert hook["entry"] == "seismic-linter"
    assert hook["language"] == "python"
    assert set(hook["types_or"]) == {"python", "jupyter"}
