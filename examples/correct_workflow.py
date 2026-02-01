"""
Demonstrates the correct temporal workflow.
"""

import pandas as pd
import numpy as np
from seismic_linter.runtime import verify_monotonicity, validate_split_integrity


@verify_monotonicity(time_col="time")
def load_data():
    # Mock data for demo
    times = pd.date_range(start="2020-01-01", periods=100, freq="D")
    df = pd.DataFrame(
        {
            "time": times,
            "magnitude": np.random.uniform(2.0, 5.0, 100),
            "station": ["StatA"] * 100,
        }
    )
    return df


print("Loading data...")
df = load_data()

# ✅ Use rolling statistics
print("Computing rolling statistics...")
df["normalized"] = df.groupby("station")["magnitude"].transform(
    lambda x: (x - x.rolling(10).mean()) / x.rolling(10).std()
)

# ✅ Temporal split
print("Splitting data temporarily...")
# Use quantile for demo purposes (in production, use a fixed date cutoff)
cutoff = df["time"].quantile(0.8)
train = df[df["time"] < cutoff]
test = df[df["time"] >= cutoff]

print("Validating split integrity...")
validate_split_integrity(train, test, time_col="time")
print("Workflow completed successfully.")
