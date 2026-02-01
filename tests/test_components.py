import json
from pathlib import Path
from seismic_linter.notebook_handler import (
    NotebookMapper,
    map_violations,
    parse_notebook,
)
from seismic_linter.caching import ContentCache
from seismic_linter.rules import Violation


# --- Notebook Handler Tests ---
def test_parse_notebook_simple(tmp_path):
    # Create simple notebook
    nb_content = {
        "cells": [
            {"cell_type": "code", "source": ["import os\n", "x = 1"], "metadata": {}},
            {"cell_type": "markdown", "source": ["# Docs"], "metadata": {}},
            {"cell_type": "code", "source": ["y = 2"], "metadata": {}},
        ],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    f = tmp_path / "test.ipynb"
    f.write_text(json.dumps(nb_content), encoding="utf-8")

    source, mapper = parse_notebook(f)

    assert "import os" in source
    assert "y = 2" in source
    # Check mapping
    # Cell 0: import os (line 1), x=1 (line 2)
    # Line 3: blank
    # Cell 2: y=2 (line 4)

    # Map line 1 -> Cell 0 (displayed as 1), line 0
    # Wait, mapper stores 1-based lines?
    # Let's check impl: mapper.virtual_lines[current_line] = (cell_idx, local_line)

    assert mapper.map_line(1) == (0, 1)  # Cell 0, Line 1
    assert mapper.map_line(4) == (2, 1)  # Cell 2, Line 1


def test_map_violations():
    mapper = NotebookMapper()
    # Mock map: Line 10 -> Cell 1, Line 5
    mapper.virtual_lines[10] = (1, 5)

    v = Violation("T001", "msg", "f.ipynb", 10, 0, "warning")
    original_lineno, original_cell_id = v.lineno, v.cell_id
    mapped = map_violations([v], mapper)

    assert mapped[0].cell_id == 2  # 0-indexed idx 1 -> Cell 2
    assert mapped[0].lineno == 5
    # map_violations returns new instances; originals unchanged
    assert v.lineno == original_lineno
    assert v.cell_id == original_cell_id
    assert id(mapped[0]) != id(v)


# --- Caching Tests ---
def test_caching_behavior(tmp_path):
    cache_root = tmp_path / "root"
    cache = ContentCache(cache_root)

    f = Path("/abs/path/to/script.py")  # Fake path
    content = "print('hello')"
    h = cache.compute_hash(content)

    # Get empty
    assert cache.get(f, h) is None

    # Set
    v = Violation("T001", "msg", str(f), 1, 0, "warning")
    cache.set(f, h, [v])

    # Get hit
    hit = cache.get(f, h)
    assert hit is not None
    assert len(hit) == 1
    assert hit[0].rule_id == "T001"

    # Get miss (hash change)
    assert cache.get(f, "newhash") is None
