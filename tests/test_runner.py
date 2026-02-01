import pytest
from seismic_linter.runner import process_file_wrapper
import seismic_linter.runner
from unittest.mock import patch
import sys

def test_debug_runner_attrs():
    """Debug what attributes runner has."""
    print(f"Runner dir: {dir(seismic_linter.runner)}")
    assert hasattr(seismic_linter.runner, "analyze_path"), "analyze_path missing"

def test_process_file_wrapper_exception(tmp_path):
    """Test that runner catches exceptions during analysis."""
    f = tmp_path / "crash.py"
    f.touch()
    
    # Debug print
    if not hasattr(seismic_linter.runner, "analyze_path"):
        pytest.fail(f"analyze_path not in runner. dir={dir(seismic_linter.runner)}")

    with patch("seismic_linter.runner.analyze_path", side_effect=ValueError("Boom")):
        res = process_file_wrapper((f, None, None))
        path_str, violations, h, error = res
        assert "Boom" in error
