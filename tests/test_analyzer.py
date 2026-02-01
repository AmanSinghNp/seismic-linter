import ast
from seismic_linter.analyzer import TemporalAnalyzer, analyze_code


def test_safe_parent_recursion_limit():
    """Test that deeply nested calls do not cause infinite recursion."""
    # extremely nested calls: df.a.b.c.d.e....mean()
    # We just need enough to exceed max_iter=100 in logic, but standard python
    # recursion limit handles AST. The linter has an explicit loop limit.
    
    # Heuristic chain
    code = "df" + ".parent" * 150 + ".mean()"
    analyzer = TemporalAnalyzer("test")
    tree = ast.parse(code)
    analyzer.visit(tree)
    # Should not crash, and should probably flag T001 because it can't find a safe parent within limit
    assert len(analyzer.violations) == 1
    assert analyzer.violations[0].rule_id == "T001"


def test_check_train_test_split_variable_args():
    """Test T003 with variable arguments."""
    code = """
from sklearn.model_selection import train_test_split
args = {'shuffle': False}
train_test_split(df, **args) 
    """
    # This matches the "not literal False" path -> violation
    violations = analyze_code(code)
    assert len(violations) == 1
    assert violations[0].rule_id == "T003"


def test_t001_global_mean_trigger():
    """Test detection of global mean calculation."""
    code = """
import pandas as pd
df = pd.DataFrame({'mag': [1, 2, 3]})
print(df['mag'].mean())
"""
    violations = analyze_code(code)
    assert len(violations) == 1
    assert violations[0].rule_id == "T001"
    assert "Global mean()" in violations[0].message


def test_t001_rolling_mean_ignore():
    """Test that rolling/groupby operations are ignored."""
    code = """
import pandas as pd
df = pd.DataFrame({'mag': [1, 2, 3]})
print(df['mag'].rolling(10).mean())
print(df.groupby('grp')['mag'].mean())
"""
    violations = analyze_code(code)
    assert len(violations) == 0


def test_t003_random_split_trigger():
    """Test detection of random train_test_split (default shuffle=True)."""
    code = """
from sklearn.model_selection import train_test_split
X_train, X_test = train_test_split(X, y)
"""
    violations = analyze_code(code)
    assert len(violations) == 1
    assert violations[0].rule_id == "T003"
    ctx = violations[0].context or ""
    assert "shuffle=True" in ctx or "Random splitting" in ctx


def test_t003_explicit_shuffle_true_trigger():
    """Test detection of explicit shuffle=True."""
    code = """
from sklearn.model_selection import train_test_split
X_train, X_test = train_test_split(X, y, shuffle=True)
"""
    violations = analyze_code(code)
    assert len(violations) == 1
    assert violations[0].rule_id == "T003"


def test_t003_shuffle_false_pass():
    """Test that shuffle=False passes."""
    code = """
from sklearn.model_selection import train_test_split
X_train, X_test = train_test_split(X, y, shuffle=False)
"""
    violations = analyze_code(code)
    assert len(violations) == 0


def test_t003_aliased_import_trigger():
    """Test detection with aliased import."""
    code = """
from sklearn.model_selection import train_test_split as tts
X_train, X_test = tts(X, y, shuffle=True)
"""
    violations = analyze_code(code)
    assert len(violations) == 1
    assert violations[0].rule_id == "T003"


def test_analyze_code_syntax_error_returns_e001():
    """analyze_code returns E001 violation for invalid syntax instead of raising."""
    violations = analyze_code("def broken(")
    assert len(violations) == 1
    assert violations[0].rule_id == "E001"
    msg = violations[0].message
    assert "syntax" in msg.lower()
