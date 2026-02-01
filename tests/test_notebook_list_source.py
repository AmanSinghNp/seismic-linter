import nbformat
from seismic_linter.notebook_handler import parse_notebook


def test_parse_notebook_list_source(tmp_path):
    """
    Test that parse_notebook correctly handles cell.source as a list of strings.
    """
    nb = nbformat.v4.new_notebook()
    # Create a code cell where source is a list of strings
    code_source_list = ["import os\n", "print('hello')\n"]
    cell = nbformat.v4.new_code_cell(source=code_source_list)
    nb.cells.append(cell)

    nb_path = tmp_path / "test_list_source.ipynb"
    with open(nb_path, "w", encoding="utf-8") as f:
        nbformat.write(nb, f)

    # Analyze - should not raise AttributeError
    source, mapper = parse_notebook(nb_path)

    # Verify content
    assert "import os" in source
    assert "print('hello')" in source

    # Verify mapping exists
    # We expect some lines to be mapped.
    assert len(mapper.virtual_lines) > 0
    # Cell index 0 or 1 depending on enumeration
    assert 0 in mapper.cells or 1 in mapper.cells
