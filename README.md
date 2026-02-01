# seismic-linter

[![PyPI](https://img.shields.io/pypi/v/seismic-linter)](https://pypi.org/project/seismic-linter/)
[![CI](https://github.com/AmanSinghNp/seismic-linter/actions/workflows/ci.yml/badge.svg)](https://github.com/AmanSinghNp/seismic-linter/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Stop publishing 99% accurate models that fail in production.**

seismic-linter automatically detects temporal causality violations in earthquake forecasting and seismology machine learning pipelines. It catches the silent bugs that make your model "cheat" by using future data during training—leading to papers with impressive results that completely fail during real-time deployment.

## The Problem

Earthquake forecasting suffers from a unique ML pathology: **temporal data leakage**. When you normalize magnitudes using global statistics, split data with `shuffle=True`, or fit transformers before temporal splitting, your model implicitly "knows" about future earthquakes. This creates artificially high accuracy that evaporates in production.

## The Solution

seismic-linter provides:
- 🔍 **Static analysis** - Scan your Python code for leakage patterns before running
- ⚡ **Runtime validation** - Decorators (`@verify_monotonicity`) and integrity checks
- 🧪 **Pytest Integration** - Use `validate_split_integrity(train_df, test_df)` after splitting. See [docs/api.md](docs/api.md) for full API.
- 📋 **Pre-commit hooks** - Block leaky code from entering your repository

The GitHub Action runs in a Linux container; Windows runners are not supported.

## Detected Rules

| Rule ID | Description | Severity |
|---------|-------------|----------|
| **T001** | Global statistics (mean/std) computed without temporal context | ⚠️ Warning |
| **T002** | Model `.fit()` called on potentially leaky data (e.g., raw `df`) | ℹ️ Info |
| **T003** | `train_test_split` with `shuffle=True` (random split) | ❌ Error |

## Configuration
Configuration is loaded from the `pyproject.toml` of the first path specified in the CLI arguments (or current directory if none).

Inline suppressions are supported using `# seismic-linter: ignore rule_id` (applies to current line only):
```python
df['norm'] = (df['mag'] - df['mag'].mean()) / df['mag'].std()  # seismic-linter: ignore T001
```

> **Note**: When using `github` output format, paths are relative to the current working directory where possible.

## Quick Example

```python
# ❌ This will trigger a warning
df['normalized'] = (df['magnitude'] - df['magnitude'].mean()) / df['magnitude'].std()

# ✅ This passes validation  
df['normalized'] = df.groupby('station')['magnitude'].transform(
    lambda x: (x - x.rolling(window=100).mean())
)
