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


def test_t002_flags_unsafe_markers_attached_to_data_names():
    """train_test_split users often write Xtest, ytest and dftest without separators."""
    assert "T002" in _rule_ids("model.fit(Xtest)")
    assert "T002" in _rule_ids("model.fit(ytest)")
    assert "T002" in _rule_ids("model.fit(dftest)")
    assert "T002" in _rule_ids("model.fit(Xval)")
    assert "T002" not in _rule_ids("model.fit(Xtrain)")
    assert "T002" not in _rule_ids("model.fit(ytrain)")


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


# --- Byte order marks: Windows editors write a UTF-8 BOM that is not code ---
def test_analyze_path_accepts_utf8_bom(tmp_path):
    py_file = tmp_path / "bom.py"
    py_file.write_bytes(b"\xef\xbb\xbfdf.mean()\n")

    violations, _ = analyze_path(py_file)

    assert [(v.rule_id, v.lineno) for v in violations] == [("T001", 1)]


def test_analyze_file_accepts_utf8_bom(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "pyproject.toml").write_text("[project]\nname='p'\n", encoding="utf-8")
    py_file = project / "bom.py"
    py_file.write_bytes(b"\xef\xbb\xbfdf.mean()\n")

    violations = analyze_file(py_file)

    assert [v.rule_id for v in violations] == ["T001"]


# --- T001: explicit windows and error metrics are not global statistics ---
def test_t001_statistic_over_bounded_window_is_safe():
    """fast-trigger takes a peak over one pick's slice of a trace."""
    assert _rule_ids("snr = np.max(cft[trace_index, on : off + 1])") == []
    assert _rule_ids("train_stats = df[:split].mean()") == []
    assert _rule_ids("train_stats = df.iloc[:split].std()") == []


def test_t001_column_of_bounded_window_is_safe():
    """A column or attribute of a bounded window is still inside that window."""
    assert _rule_ids("m = df[:split].close.mean()") == []
    assert _rule_ids("m = df[:split]['close'].mean()") == []
    assert _rule_ids("m = np.max(df[:split].values)") == []
    assert _rule_ids("m = np.std(np.abs(df[:split].close))") == []
    assert _rule_ids("m = df[:split].close.abs().mean()") == []


def test_t001_column_of_tail_slice_is_still_flagged():
    assert _rule_ids("m = df[split:].close.mean()") == ["T001"]
    assert _rule_ids("m = df['close'][split:].mean()") == ["T001"]


def test_t001_unbounded_or_step_only_slices_still_flagged():
    assert _rule_ids("df[:].mean()") == ["T001"]
    assert _rule_ids("df[::2].mean()") == ["T001"]


def test_t001_tail_slice_without_stop_is_still_flagged():
    """df[split:] runs to the end of the series, so it is not a bounded window."""
    assert _rule_ids("train_stats = df[split:].mean()") == ["T001"]
    assert _rule_ids("df[100:].std()") == ["T001"]
    assert _rule_ids("df.iloc[split:].std()") == ["T001"]
    assert _rule_ids("snr = np.max(cft[trace_index, on:])") == ["T001"]


def test_t001_error_metric_over_difference_is_safe():
    """Residuals between prediction and reference are evaluation, not fitting."""
    assert _rule_ids("rms = np.mean((pred - target) ** 2)") == []
    assert _rule_ids("np.max(np.abs(got - expected))") == []
    assert _rule_ids("np.sqrt(np.mean((a - e) ** 2))") == []


def test_t001_difference_over_time_is_still_flagged():
    """Returns and lagged differences move along time, so they are not residuals."""
    assert _rule_ids("r = (df['close'] - df['close'].shift(1)).std()") == ["T001"]
    assert _rule_ids("m = np.mean(df.close.shift(1) - df.close)") == ["T001"]
    assert _rule_ids("v = np.std(x - x.diff())") == ["T001"]
    assert _rule_ids("rms = np.mean((pred - target.shift(1)) ** 2)") == ["T001"]


def test_t001_lagged_slices_are_still_flagged():
    """x[1:] - x[:-1] is a lag written with slices, so it is reported too."""
    assert _rule_ids("m = np.mean(x[1:] - x[:-1])") == ["T001"]
    assert _rule_ids("m = np.mean(df.close[1:] - df.close[:-1])") == ["T001"]
    assert _rule_ids("m = np.mean(df[1:].close - df[:-1].close)") == ["T001"]
    assert _rule_ids("m = np.mean(np.abs(x[1:] - x[:-1]))") == ["T001"]


def test_t001_same_slice_on_both_sides_is_still_safe():
    """Two arrays cut to the same rows are compared row by row, not over time."""
    assert _rule_ids("rms = np.mean((pred[1:] - target[1:]) ** 2)") == []
    assert _rule_ids("m = np.mean(cft[i, on:off] - cft[j, on:off])") == []


def test_t001_loss_on_method_chain_over_difference_is_safe():
    """torch-friction computes an MSE loss with .pow(2).mean() on a difference."""
    source = "loss = (predictions - target_friction).pow(2).mean()"
    assert _rule_ids(source) == []


def test_t001_squared_series_and_constant_shift_still_flagged():
    assert _rule_ids("np.mean(data ** 2)") == ["T001"]
    assert _rule_ids("np.mean(x - 1)") == ["T001"]
    assert _rule_ids("v_max = velocity.max()") == ["T001"]
