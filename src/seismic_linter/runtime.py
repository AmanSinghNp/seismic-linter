"""
Runtime validation hooks for temporal causality.
"""

import functools
import warnings
import pandas as pd
from typing import Any, Callable


class TemporalCausalityError(ValueError):
    """Raised when temporal causality is violated in data."""
    pass




def verify_monotonicity(time_col: str = "time") -> Callable:
    """
    Decorator to ensure the returned DataFrame is sorted by time.
    Useful for data loading functions.

    If data is not a DataFrame, it is returned unchanged.
    Empty DataFrames are considered valid and sorted.
    The time column must not be all NaN; otherwise TemporalCausalityError is raised.

    Args:
        time_col: Name of the timestamp column to check.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = func(*args, **kwargs)

            if not isinstance(result, pd.DataFrame):
                return result

            if time_col not in result.columns:
                warnings.warn(
                    f"Column '{time_col}' not found. Skipping temporal check."
                )
                return result

            if result[time_col].isna().all():
                raise TemporalCausalityError(
                    f"Time column '{time_col}' cannot be all NaN."
                )

            # Check if sorted
            if not result[time_col].is_monotonic_increasing:
                raise TemporalCausalityError(
                    f"Data returned by {func.__name__} is not sorted by '{time_col}'. "
                    "This breaks temporal causality for split operations."
                )
            return result

        return wrapper

    return decorator


def validate_split_integrity(
    train: pd.DataFrame, test: pd.DataFrame, time_col: str = "time"
) -> None:
    """
    Test set must be strictly after training set in time:
    train[time_col].max() < test[time_col].min().
    Raises if this does not hold (overlap or test before train).

    Args:
        train: Training DataFrame.
        test: Testing DataFrame.
        time_col: Name of the timestamp column.

    Raises:
        TemporalCausalityError: If the split violates temporal order.
        ValueError: If time_col is missing, a DataFrame is empty, or the time
            column contains NaN.

    Note:
        Timezone-naive vs aware comparisons may behave strictly (or fail).
        Ensure time columns have consistent timezone awareness.
    """
    if time_col not in train.columns:
        raise ValueError(f"Time column '{time_col}' not found in training data.")
    if time_col not in test.columns:
        raise ValueError(f"Time column '{time_col}' not found in test data.")

    if train.empty:
        raise ValueError("Training data is empty. Cannot validate split integrity.")
    if test.empty:
        raise ValueError("Test data is empty. Cannot validate split integrity.")

    if train[time_col].isna().any() or test[time_col].isna().any():
        raise ValueError("Time column must not contain NaN.")

    train_max = train[time_col].max()
    test_min = test[time_col].min()

    if train_max >= test_min:
        msg = (
            f"Temporal Leak Detected! \n"
            f"Training ends at: {train_max}\n"
            f"Testing starts at: {test_min}\n"
            f"The model allows access to future information (or overlaps boundary)."
        )
        raise TemporalCausalityError(msg)
