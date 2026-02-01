# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
