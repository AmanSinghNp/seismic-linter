import json
from pathlib import Path

from seismic_linter import caching
from seismic_linter.caching import ContentCache, CACHE_DIR_NAME
from seismic_linter.rules import Violation


def _violation(path):
    return Violation("T001", "msg", str(path), 1, 0, "warning", cell_id=2)


def test_cache_entry_from_other_linter_version_is_a_miss(tmp_path):
    cache = ContentCache(tmp_path)
    source_file = tmp_path / "a.py"
    cache.set(source_file, "hash", [_violation(source_file)])

    cache_file = cache._get_cache_path(source_file)
    data = json.loads(cache_file.read_text(encoding="utf-8"))
    data["linter_version"] = "0.0.0"
    cache_file.write_text(json.dumps(data), encoding="utf-8")

    assert cache.get(source_file, "hash") is None


def test_cache_entry_from_other_analyzer_is_a_miss(tmp_path, monkeypatch):
    """An entry written before an analyzer or rule change is not reused."""
    cache = ContentCache(tmp_path)
    source_file = tmp_path / "a.py"
    cache.set(source_file, "hash", [_violation(source_file)])
    monkeypatch.setattr(caching, "ANALYSIS_DIGEST", "rules-changed")

    assert cache.get(source_file, "hash") is None


def test_cache_entry_without_analyzer_digest_is_a_miss(tmp_path):
    """Entries written by earlier versions have no digest and are not trusted."""
    cache = ContentCache(tmp_path)
    source_file = tmp_path / "a.py"
    cache.set(source_file, "hash", [_violation(source_file)])

    cache_file = cache._get_cache_path(source_file)
    data = json.loads(cache_file.read_text(encoding="utf-8"))
    del data["analyzer_digest"]
    cache_file.write_text(json.dumps(data), encoding="utf-8")

    assert cache.get(source_file, "hash") is None


def test_corrupt_cache_entry_is_a_miss(tmp_path):
    cache = ContentCache(tmp_path)
    source_file = tmp_path / "a.py"
    cache._get_cache_path(source_file).write_text("{not json", encoding="utf-8")

    assert cache.get(source_file, "hash") is None


def test_cache_round_trip_keeps_cell_id(tmp_path):
    cache = ContentCache(tmp_path)
    source_file = tmp_path / "eda.ipynb"
    cache.set(source_file, "hash", [_violation(source_file)])

    hit = cache.get(source_file, "hash")

    assert hit is not None and hit[0].cell_id == 2


def test_cache_write_failure_only_warns(tmp_path, capsys):
    cache = ContentCache(tmp_path)
    source_file = tmp_path / "a.py"
    # A directory at the cache file path makes the write fail.
    cache._get_cache_path(source_file).mkdir()

    cache.set(source_file, "hash", [])

    assert "Failed to write cache" in capsys.readouterr().err


def test_cache_directory_is_created_under_root(tmp_path):
    ContentCache(tmp_path)

    assert (Path(tmp_path) / CACHE_DIR_NAME).is_dir()
