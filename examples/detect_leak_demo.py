"""
Demonstrates how seismic-linter catches a temporal leak.
Run: seismic-linter examples/detect_leak_demo.py
"""

import pandas as pd
from sklearn.model_selection import train_test_split

# Mock data creation for demo purposes, normally pd.read_csv('...')
df = pd.DataFrame(
    {
        "magnitude": [2.1, 4.5, 3.2, 5.0, 2.8] * 20,
        "station": (
            [
                "Observation_A",
                "Observation_B",
                "Observation_C",
                "Observation_D",
                "Observation_E",
            ]
            * 20
        ),
        "time": pd.to_datetime(
            ["2020-01-01", "2020-01-02", "2020-01-03", "2020-01-04", "2020-01-05"] * 20
        ),
    }
)

# ❌ This will trigger T001
# Global mean uses future data relative to early rows
global_mean = df["magnitude"].mean()
df["normalized"] = (df["magnitude"] - global_mean) / df["magnitude"].std()

# ❌ This will trigger T003
# train_test_split defaults to shuffle=True, which destroys temporal order
X_train, X_test = train_test_split(df, test_size=0.2)
