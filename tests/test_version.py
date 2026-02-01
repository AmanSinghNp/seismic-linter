import pytest
from unittest.mock import patch, MagicMock
from seismic_linter.version import _get_version
import importlib.metadata

def test_get_version_importlib_success():
    """Test that version is retrieved from importlib.metadata if installed."""
    # We patch where it is looked up: seismic_linter.version.version
    with patch("seismic_linter.version.version", return_value="1.2.3"):
        assert _get_version() == "1.2.3"

def test_get_version_importlib_not_found():
    """Test fallback when package is not installed."""
    package_not_found = importlib.metadata.PackageNotFoundError
    with patch("seismic_linter.version.version", side_effect=package_not_found):
        # Should fallback to pyproject.toml -> 0.2.0
        assert _get_version() == "0.2.0"
