from pathlib import Path
from seismic_linter.analyzer import analyze_code

def test_inline_suppression_single():
    code = """
import pandas as pd
df = pd.DataFrame({'a': [1, 2]})
df['b'] = df['a'].mean()  # seismic-linter: ignore T001
    """
    violations = analyze_code(code)
    # T001 should be suppressed
    assert len(violations) == 0

def test_inline_suppression_multiple():
    code = """
import pandas as pd
from sklearn.model_selection import train_test_split
df = pd.DataFrame({'a': [1, 2]})
# Suppress T001 and T003
df['b'] = df['a'].mean()
x, y = train_test_split(df) # seismic-linter: ignore T001 T003
    """
    violations = analyze_code(code)
    # Line 6 has T001 (unsuppressed)
    # Line 7 has T003 (suppressed)
    assert len(violations) == 1
    assert violations[0].lineno == 6
    assert violations[0].rule_id == "T001"

def test_inline_suppression_irrelevant():
    code = """
import pandas as pd
df = pd.DataFrame({'a': [1, 2]})
df['b'] = df['a'].mean()  # seismic-linter: ignore T002
    """
    violations = analyze_code(code)
    # T001 not suppressed by T002 ignore
    assert len(violations) == 1
    assert violations[0].rule_id == "T001"
