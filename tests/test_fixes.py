import pytest
import pandas as pd
from pathlib import Path
from seismic_linter.cli import is_excluded
from seismic_linter.config import load_config
from seismic_linter.runtime import validate_split_integrity, TemporalCausalityError
from seismic_linter.analyzer import analyze_code


# --- Test Exclude Patterns (Fix 1.2) ---
def test_exclude_patterns_match_directory_segments():
    """Ensure is_excluded matches directory names in path, not just file names."""
    excludes = [".git", "__pycache__"]

    p1 = Path("project/.git/config")
    assert is_excluded(p1, excludes), "Should exclude file inside .git folder"

    p2 = Path("src/__pycache__/utils.cpython-39.pyc")
    assert is_excluded(p2, excludes), "Should exclude file inside __pycache__"

    p3 = Path("src/main.py")
    assert not is_excluded(p3, excludes), "Should not exclude normal file"

    p4 = Path(".git")
    assert is_excluded(p4, excludes), "Should exclude .git folder itself (as path)"


# --- Test Config Validation (Fix 1.3 & 2.3) ---
def test_config_list_coercion_and_merge(tmp_path):
    """Ensure string values are coerced AND lists are merged additively."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.seismic-linter]
ignore = "T001"
exclude = ["legacy"]
    """,
        encoding="utf-8",
    )

    config = load_config(tmp_path)

    # Check Merge (Default ignore=[] but default exclude=[.git...])
    # T001 should be present
    assert "T001" in config["ignore"]

    # Check Exclude Merge: Default entries + 'legacy'
    assert "legacy" in config["exclude"]
    assert ".git" in config["exclude"]  # Default should still be there!


# --- Test Runtime Split Integrity (Fix 1.1) ---
def test_validate_split_integrity_empty_should_fail():
    """Ensure empty splits raise an error instead of passing silently."""
    df_train = pd.DataFrame({"time": [1, 2, 3]})
    df_empty = pd.DataFrame({"time": []})

    # Case 1: Empty test
    with pytest.raises(ValueError, match="empty"):
        validate_split_integrity(df_train, df_empty, time_col="time")

    # Case 2: Empty train
    with pytest.raises(ValueError, match="empty"):
        validate_split_integrity(df_empty, df_train, time_col="time")


def test_validate_split_integrity_valid():
    df_train = pd.DataFrame({"time": [1, 2, 3]})
    df_test = pd.DataFrame({"time": [4, 5, 6]})
    # Should not raise
    validate_split_integrity(df_train, df_test, time_col="time")


def test_validate_split_integrity_overlap():
    df_train = pd.DataFrame({"time": [1, 5]})
    df_test = pd.DataFrame({"time": [4, 6]})
    with pytest.raises(TemporalCausalityError):
        validate_split_integrity(df_train, df_test, time_col="time")


# --- Test T002 Refinement (Fix 2.2) ---
def test_t002_refinement():
    # Case 1: Unsafe (df)
    code_unsafe = "model.fit(df, y)"
    violations = analyze_code(code_unsafe)
    assert any(v.rule_id == "T002" for v in violations), "df should trigger T002"

    # Case 2: Safe (X_train) - white list check logic
    code_safe = "model.fit(X_train, y_train)"
    violations = analyze_code(code_safe)
    assert not any(v.rule_id == "T002" for v in violations), "X_train should be safe"

    # Case 3: Previously Unsafe, now Safe (custom_matrix)
    # The new logic says: If not in explicit unsafe list, assume safe.
    code_custom = "model.fit(my_custom_matrix, y)"
    violations = analyze_code(code_custom)
    assert not any(
        v.rule_id == "T002" for v in violations
    ), "Unknown variable names should be assumed safe to reduce noise"

    # Case 4: Explicitly Unsafe Substring (test_data)
    code_leak = "model.fit(test_data, y)"
    violations = analyze_code(code_leak)
    assert any(v.rule_id == "T002" for v in violations), (
        "test_data should trigger T002"
    )
