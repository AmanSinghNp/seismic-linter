
import pytest
import pandas as pd
from seismic_linter.runtime import verify_monotonicity, validate_split_integrity, TemporalCausalityError

def test_verify_monotonicity_success():
    """Test that sorted data passes."""
    @verify_monotonicity(time_col='time')
    def load_data():
        return pd.DataFrame({'time': [1, 2, 3], 'val': ['a', 'b', 'c']})
        
    # Should not raise
    df = load_data()
    assert len(df) == 3

def test_verify_monotonicity_failure():
    """Test that unsorted data raises Error."""
    @verify_monotonicity(time_col='time')
    def load_data():
        return pd.DataFrame({'time': [1, 3, 2], 'val': ['a', 'b', 'c']})
        
    with pytest.raises(TemporalCausalityError, match="is not sorted"):
        load_data()

def test_validate_split_integrity_success():
    """Test valid temporal split."""
    train = pd.DataFrame({'time': [1, 2, 3]})
    test = pd.DataFrame({'time': [4, 5, 6]})
    
    # Should not raise
    validate_split_integrity(train, test, time_col='time')

def test_validate_split_integrity_overlap():
    """Test overlapping split failure."""
    train = pd.DataFrame({'time': [1, 2, 3]})
    test = pd.DataFrame({'time': [3, 4, 5]}) # Overlap at 3
    
    with pytest.raises(TemporalCausalityError, match="Temporal Leak Detected"):
        validate_split_integrity(train, test, time_col='time')

def test_validate_split_integrity_past_leak():
    """Test failure when test data is completely before training."""
    train = pd.DataFrame({'time': [10, 11, 12]})
    test = pd.DataFrame({'time': [1, 2, 3]})
    
    with pytest.raises(TemporalCausalityError, match="Temporal Leak Detected"):
        validate_split_integrity(train, test, time_col='time')
