# Detection Rules

## Temporal Causality Rules

### T001: Global Statistics
**Severity**: Warning
**Description**: Detects use of global statistical operations (mean, std, var, min, max, normalize) on DataFrames without preceding grouping or rolling windows.
**Reasoning**: Global statistics leak future information into the past if the data is a time series.
**Example**:
```python
# Violation
df['val_norm'] = (df['val'] - df['val'].mean()) / df['val'].std()

# Fix
df['val_norm'] = (df['val'] - df['val'].rolling('1h').mean()) / df['val'].rolling('1h').std()

# Suppression
df['val_norm'] = (df['val'] - df['val'].mean()) # seismic-linter: ignore T001
```

**Limitations**: Currently, only `groupby`, `rolling`, `expanding`, and `resample` are recognized as "safe" predecessors. Other temporal transformations (e.g. `ewm`, custom wrappers) may trigger false positives and should be suppressed if correct.

Statistics over a slice with an explicit stop (e.g. `df[:split].mean()`, `np.max(cft[i, on:off])`) and error metrics over a difference of two arrays (e.g. `np.mean((pred - target) ** 2)`) are not reported, because they do not normalize over the whole series. Slices without a stop are still reported, including the tail `df[split:]` that runs to the end of the series, as are constant shifts such as `np.mean(x - 1)`. A difference of two raw series, such as `np.mean(df.close - df.open)`, is also not reported, so check those by hand. A difference that moves along time, such as a return `df.close - df.close.shift(1)` or a lagged difference `x[1:] - x[:-1]`, is reported.

### T002: Premature Fitting
**Severity**: Info
**Description**: Warns about `fit()` operations called on likely non-training data (e.g., raw `df`, `data`, `X`).
**Reasoning**: Fitting a scaler or model on the entire dataset before splitting leaks distributional information from the test set.
**Example**:
```python
# Violation
scaler.fit(df) 
X_train, X_test = train_test_split(df)

# Fix
X_train, X_test = train_test_split(df)
scaler.fit(X_train)
```

### T003: Random Splitting
**Severity**: Error
**Description**: Detects `train_test_split` without explicitly setting `shuffle=False`.
**Reasoning**: Random shuffling destroys temporal order, allowing the model to train on future data relative to some test points.
**Example**:
```python
# Violation
train, test = train_test_split(df) 
# Violation
train, test = train_test_split(df, shuffle=True)

# Fix
train, test = train_test_split(df, shuffle=False)
```

Only literal `shuffle=False` is recognized; variables (e.g. `shuffle=my_flag`) are still reported.
