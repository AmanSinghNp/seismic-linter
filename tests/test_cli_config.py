import pytest
from seismic_linter.config import load_config, find_pyproject_toml
from seismic_linter.cli import collect_files


@pytest.fixture
def temp_project(tmp_path):
    """
    Creates a temporary project structure:
    /project
      pyproject.toml
      src/
        main.py
        ignored.py
        utils.txt
    """
    project_root = tmp_path / "project"
    project_root.mkdir()

    # Create config manually
    toml_content = """
[tool.seismic-linter]
include = ["src"]
exclude = ["src/ignored.py"]
ignore = ["T001"]
"""

    with open(project_root / "pyproject.toml", "w", encoding="utf-8") as f:
        f.write(toml_content)

    src = project_root / "src"
    src.mkdir()
    (src / "main.py").touch()
    (src / "ignored.py").touch()
    (src / "utils.txt").touch()  # Wrong extension

    return project_root


def test_find_pyproject_toml(temp_project):
    """Test finding pyproject.toml from a subdirectory."""
    src = temp_project / "src"
    found = find_pyproject_toml(src)
    assert found == temp_project / "pyproject.toml"


def test_load_config_from_subdir(temp_project):
    """Test loading config when running from a subdirectory."""
    src = temp_project / "src"
    config = load_config(src)

    assert config["ignore"] == ["T001"]
    assert config["include"] == ["src"]
    assert "src/ignored.py" in config["exclude"]


def test_collect_files_respects_config(temp_project):
    """Test that collect_files uses the config logic."""
    config = load_config(temp_project)

    # collect_files expects base_path and config.
    # Logic:
    # 1. includes = ["src"]. expand relative to base_path.
    #    If base_path is project_root, src -> project_root/src/*.

    files = collect_files(temp_project, config)
    filenames = [f.name for f in files]

    # main.py should be there
    assert "main.py" in filenames
    # ignored.py should NOT be there (excluded)
    assert "ignored.py" not in filenames
    # utils.txt should NOT be there (extension)
    assert "utils.txt" not in filenames


def test_load_config_strips_whitespace_from_list_values(tmp_path):
    """Config list values (ignore, fail_on) are stripped and empty strings dropped."""
    project_root = tmp_path / "proj"
    project_root.mkdir()
    toml_content = """
[tool.seismic-linter]
ignore = [" T001 ", "T002", "  "]
fail_on = [" T003 "]
"""
    (project_root / "pyproject.toml").write_text(toml_content, encoding="utf-8")
    config = load_config(project_root)
    assert config["ignore"] == ["T001", "T002"]
    assert config["fail_on"] == ["T003"]


def test_find_pyproject_toml_none_uses_cwd(temp_project, monkeypatch):
    """find_pyproject_toml(None) uses Path.cwd() and finds pyproject.toml from there."""
    import pathlib

    monkeypatch.setattr(pathlib.Path, "cwd", classmethod(lambda cls: temp_project))
    found = find_pyproject_toml(None)
    assert found == temp_project / "pyproject.toml"
