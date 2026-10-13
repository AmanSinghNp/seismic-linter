# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- **Encoding**: Python files saved with a UTF-8 byte order mark are no longer reported as E001 syntax errors.
- **T001**: Statistics over a slice with an explicit stop (`x[:split]`, `cft[i, on:off]`) and error metrics over a difference of two arrays (`(pred - target) ** 2`) are no longer reported. Slices without a stop, such as `x[:]` or the tail `x[split:]`, differences over time, such as returns (`x - x.shift(1)`), and plain squared series still are.
- **Exclude Patterns**: Default excludes (e.g. `build`, `venv`) match only path segments below the scanned directory, so a project stored under such a directory is no longer skipped silently.
- **Notebooks**: IPython line magics and shell escapes, including backslash-continued ones, no longer make the whole notebook fail with E001. A `%name` continuation line inside brackets is Python, not a magic. Cells with a non-Python cell magic (`%%bash`) are skipped, while `%%time`, `%%timeit`, `%%capture` and `%%prun` keep their Python body and `%time x = expr` keeps its statement.
- **T002**: Unsafe names are matched by word, so names such as `small` or `call_features` no longer trigger.
- **Suppressions**: Free-text after a second `#` in a suppression comment is not read as rule IDs.
- **Pre-commit**: Added `.pre-commit-hooks.yaml` so the documented `seismic-linter` hook resolves.
- **Coverage gate**: The 90% gate compares unrounded totals and the test suite no longer depends on `.seismic_cache` state.

### Documentation
- README runtime examples use `time_col` and run as written; sample CLI output matches the tool.

## [0.2.0] - 2026-02-01

### Added
- **Notebook Support**: Full parsing and analysis support for Jupyter Notebooks (`.ipynb`), including pre-commit hooks.
- **Config Management**: Improved configuration handling with `pyproject.toml`, additive merging for exclude/ignore lists.
- **Runtime Validation**: Robust `validate_split_integrity` and `verify_monotonicity` runtime hooks.
- **Testing Helpers**: Helpers for verifying checks in pytest.
- **CLI**: Parallel processing using Manager-Worker pattern.
- **Inline Suppressions**: Support for `# seismic-linter: ignore T001` (same-line only).

### Fixed
- **Exclude Patterns**: Default excludes (e.g., `.git`) now correctly match directory segments without wildcards.
- **Split Integrity**: `validate_split_integrity` now explicitly rejects empty DataFrames.
- **T002 Logic**: Refined `fit()` leakage detection heuristics to reduce false positives.
- **GitHub Action**: Fixed `fail_on_error` input not being passed to Docker container.
- **Circular Imports**: Resolved dependency cycle in internal modules.
- **Validation**: Fixed config validation for list types.

### Changed
- **Architecture**: Unified analysis logic between CLI and internal analyzer to ensure cache consistency.
- **AST**: Migrated from deprecated `ast.NameConstant` to `ast.Constant`.

## [0.1.0] - Initial Release

[Unreleased]: https://github.com/AmanSinghNp/seismic-linter/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/AmanSinghNp/seismic-linter/releases/tag/v0.2.0
[0.1.0]: https://github.com/AmanSinghNp/seismic-linter/releases/tag/v0.1.0
