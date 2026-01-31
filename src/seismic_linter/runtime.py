"""
Runtime validation hooks for temporal causality.
"""
import functools
import warnings
import pandas as pd
from typing import Callable, Optional, Any

class TemporalCausalityError(ValueError):
    """Raised when temporal causality is violated in data."""
    pass

def verify_monotonicity(time_col: str = 'time') -> Callable:
    """
    Decorator to ensure the returned DataFrame is sorted by time.
    Useful for data loading functions.
    
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
                warnings.warn(f"Column '{time_col}' not found. Skipping temporal check.")
                return result
            
            # Check if sorted
            if not result[time_col].is_monotonic_increasing:
                raise TemporalCausalityError(
                    f"Data returned by {func.__name__} is not sorted by '{time_col}'. "
                    "This breaks temporal causality for split operations."
                )
            return result
        return wrapper
    return decorator

def validate_split_integrity(train: pd.DataFrame, test: pd.DataFrame, time_col: str = 'time') -> None:
    """
    Explicitly checks that no test data comes before the end of training data.
    
    Args:
        train: Training DataFrame.
        test: Testing DataFrame.
        time_col: Name of the timestamp column.
        
    Raises:
        TemporalCausalityError: If test data starts before training data ends.
        ValueError: If time_col is missing.
    """
    if time_col not in train.columns:
        raise ValueError(f"Time column '{time_col}' not found in training data.")
    if time_col not in test.columns:
        raise ValueError(f"Time column '{time_col}' not found in test data.")
        
    train_max = train[time_col].max()
    test_min = test[time_col].min()
    
    if train_max >= test_min:
        raise TemporalCausalityError(
            f"Temporal Leak Detected! \n"
            f"Training ends at: {train_max}\n"
            f"Testing starts at: {test_min}\n"
            f"The model allows access to future information."
        )
    print("✅ Temporal split integrity verified.")
