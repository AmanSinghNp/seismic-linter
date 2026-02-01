# API Reference

This document outlines the public API of `seismic-linter` for users integrating it into their Python scripts or testing frameworks.

## Package Version

The package version is available via `__version__`:

```python
from seismic_linter import __version__
print(__version__)
```

## Analysis

All file reads use UTF-8 encoding; files in other encodings may cause analysis errors (E000).

### `analyze_file`

```python
def analyze_file(filepath: Path, cache_root: Optional[Path] = None) -> List[Violation]
```

Analyzes a single file (Python script or Jupyter Notebook) for temporal causality violations. Returns a list of `Violation` objects. Results are cached under `cache_root`; if omitted, the cache root is inferred from the project (e.g. directory containing `pyproject.toml`) or the file's parent.

> **Note**: The cache is keyed by the absolute path of the file. Moving the repository or running from a different path will invalidate the cache.

### `analyze_path`

```python
def analyze_path(
    filepath: Path,
    source_override: Optional[str] = None,
    mapper_override: Optional[NotebookMapper] = None
) -> Tuple[List[Violation], str]
```

Low-level analysis function used by the CLI runner. Returns a tuple of `(violations, content_hash)`.
- `source_override`: Optional pre-read content (to avoid re-reading).
- `mapper_override`: Optional `NotebookMapper` (if already parsed).
Use this if you need access to the computed content hash or need to pass pre-loaded content.

### `analyze_code`

```python
def analyze_code(source: str, filename: str = "<string>") -> List[Violation]
```

Analyzes a string of Python source code directly. Invalid syntax is reported as a violation (rule E001), not raised; this matches `analyze_file` behavior.

### Suppressions

Inline suppressions using `# seismic-linter: ignore T001 T002` are supported. The comment must appear on the same line as the code triggering the violation. Suppressions on subsequent lines are not supported.

## Runtime Helpers (Pytest Integration)

These helpers verify data splits at runtime and are designed for use in tests.

### `validate_split_integrity`

```python
def validate_split_integrity(train: pd.DataFrame, test: pd.DataFrame, time_col: str = "time") -> None
```

Checks that the test set does not overlap or precede the training set in time (strict separation: `train[time_col].max() < test[time_col].min()`). Raises `TemporalCausalityError` if the split is invalid, or `ValueError` if the time column is missing or a DataFrame is empty. Call this explicitly after creating train/test splits; it is not a decorator.

> **Warning**:
> - Does **not** check if `train` or `test` are sorted internally; it only compares boundaries.
> - Ensure consistent timezone awareness. Mixing naive and aware timestamps may cause runtime errors or unexpected behavior; no strict check is enforced.

### `verify_monotonicity`

```python
@verify_monotonicity(time_col="time")
def processing_function(df)
```

Ensures that a DataFrame remains temporally sorted. If the return value is not a DataFrame, it is passed through unchanged. Empty DataFrames are considered valid and sorted.

## Data Structures

### `Violation`

```python
@dataclass(frozen=True)
class Violation:
    rule_id: str
    message: str
    filename: str
    lineno: int
    col_offset: int
    severity: str
    context: Optional[str]
    cell_id: Optional[int]
```

Represents a detected issue. Instances are immutable and hashable.
