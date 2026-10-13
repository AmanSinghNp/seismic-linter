from pathlib import Path

from seismic_linter.analyzer import (
    analyze_code,
    analyze_file,
    analyze_path,
    extract_suppressions,
)


def _rule_ids(source):
    return [v.rule_id for v in analyze_code(source)]


# --- T002: word-based unsafe names ---
def test_t002_ignores_names_that_only_contain_an_unsafe_marker():
    """'small' and 'call_features' contain 'all' but are not unsafe words."""
    assert "T002" not in _rule_ids("model.fit(small)")
    assert "T002" not in _rule_ids("model.fit(call_features)")


def test_t002_flags_unsafe_words_inside_compound_names():
    assert "T002" in _rule_ids("model.fit(all_rows)")
    assert "T002" in _rule_ids("model.fit(validation_df)")
    assert "T002" in _rule_ids("model.fit(obj.whole_catalogue)")


def test_t002_safe_names_still_win():
    assert "T002" not in _rule_ids("model.fit(all_train)")


# --- T001: neutral operations keep the grouping context ---
def test_t001_neutral_ops_after_groupby_are_safe():
    assert _rule_ids("df.groupby('a').dropna().mean()") == []
    assert _rule_ids("df.groupby('a').copy().std()") == []


def test_t001_neutral_ops_without_grouping_still_flagged():
    assert _rule_ids("df.dropna().mean()") == ["T001"]


# --- T003: import and call variants ---
def test_t003_tracks_sklearn_import_alias():
    source = "from sklearn.model_selection import train_test_split as tts\ntts(df)"
    assert _rule_ids(source) == ["T003"]


def test_t003_accepts_module_attribute_with_shuffle_false():
    source = (
        "import sklearn.model_selection as ms\nms.train_test_split(df, shuffle=False)"
    )
    assert _rule_ids(source) == []


def test_t003_variable_shuffle_flag_is_reported():
    assert _rule_ids("train_test_split(df, shuffle=flag)") == ["T003"]


# --- Suppressions ---
def test_suppression_accepts_comma_separated_rules():
    source = "df.mean()  # seismic-linter: ignore T001, T002"
    assert _rule_ids(source) == []


def test_suppression_ignores_trailing_free_text_note():
    source = "df['a'].mean()  # seismic-linter: ignore T001  # sanity baseline"
    assert extract_suppressions(source) == {1: {"T001"}}
    assert _rule_ids(source) == []


def test_extract_suppressions_on_untokenizable_source_is_empty():
    assert extract_suppressions('x = """unterminated') == {}


# --- Entry points used by the CLI and the public API ---
def test_analyze_path_reads_python_file(tmp_path):
    py_file = tmp_path / "leaky.py"
    py_file.write_text("df.mean()\n", encoding="utf-8")

    violations, content_hash = analyze_path(py_file)

    assert [v.rule_id for v in violations] == ["T001"]
    assert len(content_hash) == 32


def test_analyze_path_reads_notebook_with_cell_mapping(tmp_path):
    import nbformat

    nb = nbformat.v4.new_notebook()
    nb.cells = [
        nbformat.v4.new_code_cell(source="x = 1"),
        nbformat.v4.new_code_cell(source="df.mean()"),
    ]
    nb_file = tmp_path / "eda.ipynb"
    with open(nb_file, "w", encoding="utf-8") as f:
        nbformat.write(nb, f)

    violations, _ = analyze_path(nb_file)

    assert [(v.rule_id, v.cell_id, v.lineno) for v in violations] == [("T001", 2, 1)]


def test_analyze_file_uses_pyproject_directory_for_cache(tmp_path):
    project = tmp_path / "project"
    (project / "src").mkdir(parents=True)
    (project / "pyproject.toml").write_text("[project]\nname='p'\n", encoding="utf-8")
    py_file = project / "src" / "leaky.py"
    py_file.write_text("df.mean()\n", encoding="utf-8")

    violations = analyze_file(py_file)

    assert [v.rule_id for v in violations] == ["T001"]
    assert any((project / ".seismic_cache").glob("*.json"))
    assert not Path(py_file.parent / ".seismic_cache").exists()
