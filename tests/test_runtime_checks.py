import pandas as pd
import pytest

from seismic_linter.runtime import (
    TemporalCausalityError,
    validate_split_integrity,
    verify_monotonicity,
)


def test_temporal_causality_error_is_value_error():
    assert issubclass(TemporalCausalityError, ValueError)


def test_verify_monotonicity_passes_non_dataframe_through():
    @verify_monotonicity(time_col="time")
    def load_rows():
        return [3, 1, 2]

    assert load_rows() == [3, 1, 2]


def test_verify_monotonicity_warns_when_time_column_missing():
    @verify_monotonicity(time_col="time")
    def load_data():
        return pd.DataFrame({"val": [2, 1]})

    with pytest.warns(UserWarning, match="not found"):
        df = load_data()
    assert list(df["val"]) == [2, 1]


def test_verify_monotonicity_rejects_all_nan_time_column():
    @verify_monotonicity(time_col="time")
    def load_data():
        return pd.DataFrame({"time": [None, None]})

    with pytest.raises(TemporalCausalityError, match="cannot be all NaN"):
        load_data()


def test_verify_monotonicity_accepts_empty_frame_with_typed_time_column():
    """Empty DataFrames are valid and sorted, so an empty time column is not NaN."""

    @verify_monotonicity(time_col="time")
    def load_data():
        return pd.DataFrame(
            {
                "time": pd.Series([], dtype="datetime64[ns]"),
                "mag": pd.Series([], dtype=float),
            }
        )

    df = load_data()

    assert df.empty and list(df.columns) == ["time", "mag"]


def test_verify_monotonicity_accepts_untyped_empty_time_column():
    @verify_monotonicity(time_col="time")
    def load_data():
        return pd.DataFrame({"time": []})

    assert load_data().empty


def test_verify_monotonicity_error_names_the_function():
    @verify_monotonicity(time_col="time")
    def load_catalogue():
        return pd.DataFrame({"time": [2, 1]})

    with pytest.raises(TemporalCausalityError, match="load_catalogue"):
        load_catalogue()


def _split(train_times, test_times, time_col="time"):
    return (
        pd.DataFrame({time_col: train_times}),
        pd.DataFrame({time_col: test_times}),
    )


def test_validate_split_integrity_accepts_strict_separation():
    train, test = _split([1, 2, 3], [4, 5])

    validate_split_integrity(train, test, time_col="time")


def test_validate_split_integrity_rejects_equal_boundary():
    train, test = _split([1, 2, 3], [3, 4])

    with pytest.raises(TemporalCausalityError, match="Temporal Leak"):
        validate_split_integrity(train, test, time_col="time")


def test_validate_split_integrity_missing_column_in_train():
    train = pd.DataFrame({"other": [1]})
    test = pd.DataFrame({"time": [2]})

    with pytest.raises(ValueError, match="not found in training data"):
        validate_split_integrity(train, test, time_col="time")


def test_validate_split_integrity_missing_column_in_test():
    train = pd.DataFrame({"time": [1]})
    test = pd.DataFrame({"other": [2]})

    with pytest.raises(ValueError, match="not found in test data"):
        validate_split_integrity(train, test, time_col="time")


def test_validate_split_integrity_rejects_nan_times():
    train = pd.DataFrame({"time": [1.0, None]})
    test = pd.DataFrame({"time": [2.0]})

    with pytest.raises(ValueError, match="must not contain NaN"):
        validate_split_integrity(train, test, time_col="time")
