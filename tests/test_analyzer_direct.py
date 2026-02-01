import pytest
import sys
from pathlib import Path
from seismic_linter.analyzer import analyze_path, analyze_file
from seismic_linter.rules import Violation

def test_analyze_path_simple(tmp_path):
    """Test analyze_path with a simple python file."""
    f = tmp_path / "simple.py"
    f.write_text("x = 1", encoding="utf-8")
    
    violations, hash_val = analyze_path(f)
    assert violations == []
    assert isinstance(hash_val, str)

def test_analyze_path_with_override(tmp_path):
    """Test analyze_path with source override."""
    f = tmp_path / "dummy.py"
    # File doesn't even need to exist if we provide source, 
    # but the function signature might expect path for filename reporting
    
    source = "df.mean()" # Leaky
    violations, hash_val = analyze_path(f, source_override=source)
    
    assert len(violations) >= 1
    assert violations[0].rule_id == "T001"

def test_analyze_file_cache_hit(tmp_path, monkeypatch):
    """Test analyze_file with caching behavior."""
    f = tmp_path / "cached.py"
    f.write_text("x=1", encoding="utf-8")
    
    # First run
    v1 = analyze_file(f)
    assert v1 == []
    
    # Second run (should hit cache - verify coverage of cache hit path)
    v2 = analyze_file(f)
    assert v2 == []

def test_analyze_file_syntax_error(tmp_path):
    """Test analyze_file handles syntax errors."""
    f = tmp_path / "bad.py"
    f.write_text("if True", encoding="utf-8")
    
    v = analyze_file(f)
    assert len(v) == 1
    assert v[0].rule_id == "E001"

def test_analyze_file_general_exception(tmp_path):
    """Test analyze_file catches generic errors."""
    f = tmp_path / "crash.py"
    f.write_text("x=1", encoding="utf-8")
    
    # Mock open to raise exception or analyze_code
    from unittest.mock import patch
    with patch("seismic_linter.analyzer.analyze_code", side_effect=Exception("Boom")):
        v = analyze_file(f)
        assert len(v) == 1
        assert v[0].rule_id == "E000"
        assert "Boom" in v[0].message
