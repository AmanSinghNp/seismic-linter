# Detection Rules

## Temporal Causality Rules

### T001: Global Statistics
**Severity**: Warning
**Description**: Detects use of global statistical operations without temporal boundaries.

### T002: Premature Fitting
**Severity**: Info
**Description**: Warns about sklearn fit() operations that may use leaky data.

### T003: Random Splitting
**Severity**: Error
**Description**: Detects train_test_split without shuffle=False.

[Detailed descriptions for each rule]
