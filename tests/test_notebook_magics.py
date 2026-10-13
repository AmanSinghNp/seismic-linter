import nbformat
from seismic_linter.analyzer import analyze_file
from seismic_linter.notebook_handler import _comment_line_magic, parse_notebook


def _write_notebook(tmp_path, sources):
    nb = nbformat.v4.new_notebook()
    nb.cells = [nbformat.v4.new_code_cell(source=src) for src in sources]
    path = tmp_path / "magics.ipynb"
    with open(path, "w", encoding="utf-8") as f:
        nbformat.write(nb, f)
    return path


def test_comment_line_magic_keeps_indentation():
    assert _comment_line_magic("%matplotlib inline") == "# %matplotlib inline"
    assert _comment_line_magic("    !pip install x") == "    # !pip install x"
    assert _comment_line_magic("x = 1") == "x = 1"


def test_notebook_with_line_magics_has_no_syntax_error(tmp_path):
    path = _write_notebook(
        tmp_path,
        [
            ["%matplotlib inline\n", "!pip install numpy\n", "import pandas as pd"],
            ["df = pd.DataFrame({'a': [1, 2]})\n", "print(df['a'].mean())"],
        ],
    )

    violations = analyze_file(path)

    assert not [v for v in violations if v.rule_id == "E001"]
    t001 = [v for v in violations if v.rule_id == "T001"]
    assert len(t001) == 1
    assert t001[0].cell_id == 2
    assert t001[0].lineno == 2


def test_notebook_line_numbers_survive_magics(tmp_path):
    path = _write_notebook(
        tmp_path,
        [["%load_ext autoreload\n", "x = 1\n", "y = 2"]],
    )

    source, mapper = parse_notebook(path)

    assert source.split("\n")[0] == "# %load_ext autoreload"
    assert mapper.map_line(2) == (0, 2)
    assert mapper.map_line(3) == (0, 3)


def test_cell_magic_cell_is_skipped(tmp_path):
    path = _write_notebook(
        tmp_path,
        [
            ["%%bash\n", "ls -la\n", "df.mean()"],
            [
                "import pandas as pd\n",
                "df = pd.DataFrame({'a': [1]})\n",
                "print(df['a'].mean())",
            ],
        ],
    )

    source, mapper = parse_notebook(path)
    violations = analyze_file(path)

    assert "ls -la" not in source
    assert all(cell_idx != 0 for cell_idx, _ in mapper.virtual_lines.values())
    assert not [v for v in violations if v.rule_id == "E001"]
    assert [v.cell_id for v in violations if v.rule_id == "T001"] == [2]
