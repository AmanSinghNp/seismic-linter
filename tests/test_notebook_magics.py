import nbformat
import pytest
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


def test_continuation_lines_with_operators_are_not_magics(tmp_path):
    """'!= 0' and '% n' on a continuation line are Python, not magics."""
    path = _write_notebook(
        tmp_path,
        [["flag = (df['a']\n", "        != 0)\n", "rem = (total\n", "       % n)"]],
    )

    source, _ = parse_notebook(path)
    violations = analyze_file(path)

    assert "        != 0)" in source
    assert "       % n)" in source
    assert not [v for v in violations if v.rule_id == "E001"]


def test_percent_name_on_continuation_line_is_python(tmp_path):
    """'%name' inside an open bracket is the modulo operator, not a line magic."""
    path = _write_notebook(
        tmp_path,
        [
            ['name = "x"\n', 'msg = ("first %s"\n', "       %name)"],
            ["df = 1\n", 'print(df["a"].mean())'],
        ],
    )

    source, _ = parse_notebook(path)
    violations = analyze_file(path)

    assert "       %name)" in source
    assert not [v for v in violations if v.rule_id == "E001"]
    assert [(v.rule_id, v.cell_id) for v in violations] == [("T001", 2)]


def test_backslash_continued_shell_escape_is_fully_commented(tmp_path):
    """Every physical line of a backslash-continued '!' command is commented out."""
    path = _write_notebook(
        tmp_path,
        [
            ["!pip install \\\n", "    numpy \\\n", "    pandas\n", "x = 1"],
            ["df = 1\n", 'y = df["close"].mean()'],
        ],
    )

    source, _ = parse_notebook(path)
    violations = analyze_file(path)

    assert "# !pip install \\" in source
    assert "    # numpy \\" in source
    assert "    # pandas" in source
    assert not [v for v in violations if v.rule_id == "E001"]
    assert [(v.rule_id, v.cell_id) for v in violations] == [("T001", 2)]


def test_python_cell_magic_body_is_still_analyzed(tmp_path):
    """%%time, %%capture and %%timeit run Python, so their bodies are analyzed."""
    path = _write_notebook(
        tmp_path,
        [
            ["%%time\n", 'baseline = df["mag"].mean()\n', "print(baseline)"],
            ["%%capture out\n", 'level = df["x"].std()'],
            ["%%timeit -n 1\n", 'df["b"].mean()'],
            ["%%bash\n", "echo hi"],
            ['y = df["close"].mean()'],
        ],
    )

    violations = analyze_file(path)

    assert not [v for v in violations if v.rule_id == "E001"]
    assert [(v.cell_id, v.lineno) for v in violations if v.rule_id == "T001"] == [
        (1, 2),
        (2, 2),
        (3, 2),
        (5, 1),
    ]


def test_non_python_cell_magics_are_skipped(tmp_path):
    path = _write_notebook(
        tmp_path,
        [
            ["%%html\n", "<b>df['a'].mean()</b>"],
            ["%%writefile out.py\n", "df['a'].mean()"],
        ],
    )

    source, mapper = parse_notebook(path)

    assert source.strip() == ""
    assert analyze_file(path) == []


def test_timing_line_magic_keeps_its_statement(tmp_path):
    """'%time x = expr' runs expr, so the statement is analyzed without the magic."""
    path = _write_notebook(
        tmp_path,
        [
            [
                "import pandas as pd\n",
                'df = pd.DataFrame({"a": [1, 2]})\n',
                '%time m = df["a"].mean()\n',
                '%timeit -n 10 -r 3 s = df["a"].std()',
            ],
        ],
    )

    source, _ = parse_notebook(path)
    violations = analyze_file(path)

    assert 'm = df["a"].mean()' in source
    assert "%time" not in source
    assert [(v.rule_id, v.lineno) for v in violations if v.rule_id == "T001"] == [
        ("T001", 3),
        ("T001", 4),
    ]


@pytest.mark.parametrize(
    "line",
    [
        "%timeit -n1 -r1 y = f(1)",
        "%timeit -n10 y = f(1)",
        "%timeit -n 10 -r3 y = f(1)",
        "%timeit -o y = f(1)",
        "%timeit -oq -n5 y = f(1)",
        "%prun -s cumulative y = f(1)",
        "%prun -D out.prof y = f(1)",
        "%prun -l 10 y = f(1)",
        "%prun -r y = f(1)",
        "%time -n 10 y = f(1)",
    ],
)
def test_timing_magic_options_are_dropped(tmp_path, line):
    """Compact and non-numeric options are dropped, so the statement still parses."""
    path = _write_notebook(tmp_path, [[line + "\n", "print(y)"]])

    source, _ = parse_notebook(path)

    assert source.split("\n")[0] == "y = f(1)"
    assert not [v for v in analyze_file(path) if v.rule_id == "E001"]


def test_timing_magic_options_do_not_hide_findings(tmp_path):
    """A syntax error would replace every finding in the notebook, so none may hide."""
    path = _write_notebook(
        tmp_path,
        [
            [
                "%prun -s cumulative m = df['a'].mean()\n",
                "%timeit -n10 -r3 s = df['a'].std()",
            ],
        ],
    )

    violations = analyze_file(path)

    assert [(v.rule_id, v.lineno) for v in violations] == [
        ("T001", 1),
        ("T001", 2),
    ]
