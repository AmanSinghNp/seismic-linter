"""Tests for public API (imports, analyze_file, analyze_code)."""

import pytest
import pandas as pd


def test_public_api_import(tmp_path):
    """Public API is importable and all exports are usable."""
    from seismic_linter import (
        analyze_file,
        analyze_code,
        Violation,
        verify_monotonicity,
        validate_split_integrity,
        TemporalCausalityError,
    )

    (tmp_path / "dummy.py").write_text("x = 1", encoding="utf-8")
    assert isinstance(analyze_file(tmp_path / "dummy.py", cache_root=tmp_path), list)

    result = analyze_code("x = 1")
    assert isinstance(result, list)
    assert len(result) == 0

    v = Violation(
        rule_id="T001",
        message="test",
        filename="<string>",
        lineno=0,
        col_offset=0,
        severity="warning",
    )
    assert v.rule_id == "T001"

    @verify_monotonicity(time_col="t")
    def sorted_df():
        return pd.DataFrame({"t": [1, 2, 3]})

    assert sorted_df() is not None

    train_df = pd.DataFrame({"time": [1, 2]})
    test_df = pd.DataFrame({"time": [3, 4]})
    validate_split_integrity(train_df, test_df, time_col="time")

    with pytest.raises(TemporalCausalityError):
        raise TemporalCausalityError("test")


def test_analyze_file_with_cache(tmp_path):
    """analyze_file works with a real file and uses cache on second call."""
    from seismic_linter import analyze_file

    py_file = tmp_path / "script.py"
    py_file.write_text("x = 1\nprint(x)", encoding="utf-8")

    result1 = analyze_file(py_file, cache_root=tmp_path)
    assert isinstance(result1, list)
    assert len(result1) == 0

    result2 = analyze_file(py_file, cache_root=tmp_path)
    assert result2 == result1

    # Change content to code that yields a violation -> cache miss, fresh analysis
    leaky_code = (
        "import pandas as pd\n"
        "df = pd.DataFrame({'x': [1,2,3]})\n"
        "print(df['x'].mean())"
    )
    py_file.write_text(leaky_code, encoding="utf-8")
    result3 = analyze_file(py_file, cache_root=tmp_path)
    assert isinstance(result3, list)
    assert len(result3) >= 1
    assert any(v.rule_id == "T001" for v in result3)
    assert result3 != result1
