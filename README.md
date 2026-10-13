# seismic-linter

[![PyPI](https://img.shields.io/pypi/v/seismic-linter)](https://pypi.org/project/seismic-linter/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/AmanSinghNp/seismic-linter/actions/workflows/ci.yml/badge.svg)](https://github.com/AmanSinghNp/seismic-linter/actions/workflows/ci.yml)

**Static analysis for temporal causality in machine learning.**

`seismic-linter` prevents "future leakage" (the most common pathology in time-series forecasting and earthquake prediction models). It detects code patterns where future data inadvertently leaks into training, ensuring your model's performance in production matches its offline validation.

## Why use this?

In time-series domains like seismology or finance, standard ML practices often fail:
- **Global Normalization**: Computing `mean()` over the entire dataset (including the test set) leaks distribution info.
- **Random Splits**: Using `train_test_split(shuffle=True)` destroys temporal order.
- **Premature Fitting**: Calling `.fit()` on data before time-splitting allows the model to glimpse the future.

This tool catches these issues **statically** (before you run the code) and **dynamically** (with runtime guards).

## Installation

```bash
pip install seismic-linter
```

## Quick Start

Run the linter on your project directory:

```bash
seismic-linter ./src
```

**Example Output:**
```text
=== Seismic Linter Scan ===

File: /path/to/project/src/models/train.py
  ❌ [Line 5] T001: Global mean() may cause temporal leakage. Consider using rolling window or ensure causality.
     Context: Computing mean without detected temporal boundaries
  ❌ [Line 7] T003: train_test_split used with shuffle=True on time series (shuffle must be explicitly False)
     Context: Random splitting violates temporal causality

Found 2 potential violation(s).
```

The exit code is `1` when any error-severity rule or any rule in `fail-on` is reported, and `0` otherwise. Use `--output json` or `--output github` for machine-readable output.

## Features

- **Static Analysis**: Scans Python files (`.py`) and Jupyter Notebooks (`.ipynb`) for leaky AST patterns.
- **Runtime Guards**: API to verify data integrity during execution.
- **Zero Config**: Works out of the box, but fully configurable via `pyproject.toml`.
- **Fast**: Multiprocess analysis with content-based caching.

## Rules

| ID | Severity | Description |
|----|----------|-------------|
| **T001** | ⚠️ Warning | **Global Statistics**: Computing aggregate statistics (mean, std, var, min, max, normalize) on what appears to be a global DataFrame without grouping or rolling windows. Statistics over a slice with an explicit stop (`x[:split]`) or an error metric over a difference of two arrays (`(pred - target) ** 2`) are not reported. Differences over time, such as returns (`x - x.shift(1)`), are reported. |
| **T002** | ℹ️ Info | **Unsafe Usage**: Calling `.fit()` on variables named generic terms like `df` or `data` instead of explicit training splits (`train_df`, `X_train`). |
| **T003** | ❌ Error | **Random Splitting**: Using `train_test_split` with `shuffle=True` (or without explicitly setting `shuffle=False`), which violates temporal causality. |

## Configuration

You can configure the linter via `pyproject.toml` in your project root:

```toml
[tool.seismic-linter]
include = ["src", "notebooks"]
exclude = ["tests", "legacy"]
fail-on = ["T003"]            # Only exit with error code for T003
ignore = ["T002"]             # Completely silence T002 rules
```

- `include` replaces the default of scanning the whole project. Entries can be directories, files or globs.
- `exclude` and `ignore` are added to the defaults. `exclude` defaults to `.git`, `__pycache__`, `.venv`, `venv`, `.env`, `build` and `dist`, matched against path segments below the scanned directory.
- `fail-on` replaces the default list `["T001", "T003"]`. Error-severity findings (for example T003 and syntax errors) always fail the run.
- Keys may also be written with underscores (`fail_on`). The CLI flags `--ignore` and `--fail-on` override the config values.

### Inline Suppression

Ignore specific violations on a single line using a comment:

```python
# Calculate global mean for baseline (safe usage)
baseline = df['mag'].mean()  # seismic-linter: ignore T001
```

## Runtime Verification API

For critical pipelines, add runtime checks to ensure data integrity.

```python
import pandas as pd
from seismic_linter import verify_monotonicity, validate_split_integrity

# 1. Decorator to ensure DataFrame is sorted by time
@verify_monotonicity(time_col="time")
def load_catalogue(path):
    return pd.read_csv(path, parse_dates=["time"])

df = load_catalogue("catalogue.csv")

# 2. Explicit check after splitting on a fixed date cutoff
cutoff = pd.Timestamp("2020-01-01")
train = df[df["time"] < cutoff]
test = df[df["time"] >= cutoff]
validate_split_integrity(train, test, time_col="time")
# Raises TemporalCausalityError if the test set does not start after the training set ends
```

## Pre-commit Hook

Add to your `.pre-commit-config.yaml` to catch leaks before they are committed:

```yaml
repos:
  - repo: https://github.com/AmanSinghNp/seismic-linter
    rev: v0.2.0
    hooks:
      - id: seismic-linter
```

The hook receives the staged `.py` and `.ipynb` files from pre-commit and fails the commit on the same findings as the CLI, using the `fail-on` rules from your `pyproject.toml`. The hook is defined in `.pre-commit-hooks.yaml`. That file was added after the `v0.2.0` tag, so pin `rev` to a release tagged later than that, or to `main`.

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details on setting up the developments environment and running tests.

## License

MIT
