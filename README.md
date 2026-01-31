# seismic-linter

**Stop publishing 99% accurate models that fail in production.**

seismic-linter automatically detects temporal causality violations in earthquake forecasting and seismology machine learning pipelines. It catches the silent bugs that make your model "cheat" by using future data during training—leading to papers with impressive results that completely fail during real-time deployment.

## The Problem

Earthquake forecasting suffers from a unique ML pathology: **temporal data leakage**. When you normalize magnitudes using global statistics, split data with `shuffle=True`, or fit transformers before temporal splitting, your model implicitly "knows" about future earthquakes. This creates artificially high accuracy that evaporates in production.

## The Solution

seismic-linter provides:
- 🔍 **Static analysis** - Scan your Python code for leakage patterns before running
- ⚡ **Runtime validation** - Decorators that enforce temporal causality during execution  
- 🧪 **Pytest integration** - Automated tests to prove your train/test split is valid
- 📋 **Pre-commit hooks** - Block leaky code from entering your repository

## Quick Example

```python
# ❌ This will trigger a warning
df['normalized'] = (df['magnitude'] - df['magnitude'].mean()) / df['magnitude'].std()

# ✅ This passes validation  
df['normalized'] = df.groupby('station')['magnitude'].transform(
    lambda x: (x - x.rolling(window=100).mean())
)
