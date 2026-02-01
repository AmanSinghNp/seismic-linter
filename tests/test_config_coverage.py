import pytest
import sys
from unittest.mock import patch, MagicMock
from seismic_linter.config import _normalize_list_values, load_config, DEFAULT_CONFIG

def test_normalize_list_values_None():
    assert _normalize_list_values(None) == []

def test_normalize_list_values_str():
    assert _normalize_list_values("foo") == ["foo"]

def test_normalize_list_values_invalid_type():
    assert _normalize_list_values(123) == []

def test_normalize_list_values_mixed_types(capsys):
    """Test warning output on non-string elements."""
    lst = ["a", 1, "b", ""]
    res = _normalize_list_values(lst)
    assert res == ["a", "b"]
    captured = capsys.readouterr()
    assert "Config list values must be strings" in captured.err

def test_load_config_broken_toml(tmp_path, capsys):
    """Test exception handling when toml load fails."""
    p = tmp_path / "pyproject.toml"
    p.write_text("INVALID TOML [", encoding="utf-8")
    
    cfg = load_config(p)
    # Should fallback to default
    assert cfg["include"] == []
    captured = capsys.readouterr()
    assert "Warning: Failed to parse" in captured.err

def test_load_config_fail_on_hyphen(tmp_path):
    """Test normalization of fail-on to fail_on."""
    p = tmp_path / "pyproject.toml"
    # Create valid toml with fail-on
    content = """
    [tool.seismic-linter]
    fail-on = ["T001"]
    """
    p.write_text(content, encoding="utf-8")
    
    cfg = load_config(p)
    assert cfg["fail_on"] == ["T001"]
    assert "fail-on" not in cfg

def test_load_config_invalid_list_type(tmp_path, capsys):
    """Test processing of invalid type for list key in final validation."""
    p = tmp_path / "pyproject.toml"
    content = """
    [tool.seismic-linter]
    exclude = 123
    """
    p.write_text(content, encoding="utf-8")
    
    cfg = load_config(p)
    # Should fallback to default list, not empty (because merge logic keeps defaults)
    assert set(cfg["exclude"]) == set(DEFAULT_CONFIG["exclude"])

def test_load_config_single_string_exclude(tmp_path):
    """Test exclude as single string normalization."""
    p = tmp_path / "pyproject.toml"
    content = """
    [tool.seismic-linter]
    exclude = "single_file.py"
    """
    p.write_text(content, encoding="utf-8")
    
    cfg = load_config(p)
    assert "single_file.py" in cfg["exclude"]
