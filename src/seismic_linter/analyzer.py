"""
Core AST analyzer for detecting temporal leakage patterns.
"""

import ast
import tokenize
import io
import re
from typing import List, Dict, Optional, Tuple, Set
from pathlib import Path
from .rules import Violation, RULES
from .notebook_handler import parse_notebook, NotebookMapper, map_violations
from .caching import ContentCache



# T002 Heuristics
UNSAFE_EXACT_NAMES = {"df", "data", "x", "input", "inputs", "dataframe", "dataset"}
UNSAFE_SUBSTRING_NAMES = ["test", "val", "full", "all", "whole", "entire"]
SAFE_SUBSTRING_NAMES = ["train", "trn", "training", "fit", "sample", "resampled"]


def extract_suppressions(source: str) -> Dict[int, Set[str]]:
    """
    Parse source code to find suppression comments.
    Format: # seismic-linter: ignore T001 T002
    Returns: Dict[lineno, Set[rule_ids]]
    
    If tokenization fails (e.g. syntax error or encoding issue), returns empty dict 
    (no suppressions applied).
    """
    suppressions: Dict[int, Set[str]] = {}
    try:
        # tokenize.tokenize requires bytes
        tokens = tokenize.tokenize(io.BytesIO(source.encode("utf-8")).readline)
        for token in tokens:
            if token.type == tokenize.COMMENT:
                content = token.string.strip()
                # Match: # seismic-linter: ignore Txxx ...
                match = re.search(r"seismic-linter:\s*ignore\s+(.+)$", content)
                if match:
                    rules_str = match.group(1)
                    # Split by space/comma
                    rules = set(
                        r.strip() for r in re.split(r"[,\s]+", rules_str) if r.strip()
                    )
                    if rules:
                        if token.start[0] not in suppressions:
                            suppressions[token.start[0]] = set()
                        suppressions[token.start[0]].update(rules)
    except tokenize.TokenError:
        pass  # If tokenization fails (syntax error), we just won't suppress anything
    return suppressions


class TemporalAnalyzer(ast.NodeVisitor):
    """AST visitor that detects temporal leakage patterns."""

    def __init__(self, filename: str):
        self.filename = filename
        self.violations: List[Violation] = []
        self.imported_names: Dict[str, str] = {}  # alias -> original_name

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Track imports to identify relevant functions."""
        if node.module == "sklearn.model_selection":
            for alias in node.names:
                if alias.name == "train_test_split":
                    asname = alias.asname or alias.name
                    self.imported_names[asname] = "train_test_split"
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Inspect function calls for leakage patterns."""
        func_name = self._get_func_name(node.func)

        # Detect global statistical operations (T001)
        if func_name in ["mean", "std", "var", "min", "max", "normalize"]:
            self._check_global_statistics(node, func_name)

        # Detect sklearn operations (T003)
        is_tracked_tts = (
            func_name in self.imported_names
            and self.imported_names[func_name] == "train_test_split"
        )
        is_direct_tts = func_name == "train_test_split"

        if is_tracked_tts or is_direct_tts:
            self._check_train_test_split(node)

        # Detect T002: .fit() on potentially leaky data
        if func_name == "fit":
            self._check_fit_leakage(node)

        self.generic_visit(node)

    def _get_func_name(self, node: ast.AST) -> str:
        """Extract function name from Call node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        return ""

    def _check_global_statistics(self, node: ast.Call, func_name: str) -> None:
        """Check if statistics are computed globally without temporal awareness."""
        # Check if this is method call on DataFrame/Series (heuristic)
        if isinstance(node.func, ast.Attribute):
            parent_is_safe = self._has_safe_parent(node)

            if not parent_is_safe:
                rule = RULES["T001"]
                self.violations.append(
                    Violation(
                        rule_id=rule.id,
                        message=(
                            f"Global {func_name}() may cause temporal leakage. "
                            f"Consider using rolling window or ensure causality."
                        ),
                        filename=self.filename,
                        lineno=node.lineno,
                        col_offset=node.col_offset,
                        severity=rule.severity,
                        context=(
                            f"Computing {func_name} "
                            "without detected temporal boundaries"
                        ),
                    )
                )

    def _check_train_test_split(self, node: ast.Call) -> None:
        """Check if train_test_split respects temporal ordering (T003)."""
        shuffle_arg = None

        # Check keywords
        for keyword in node.keywords:
            if keyword.arg == "shuffle":
                shuffle_arg = keyword.value
                break

        # Default for train_test_split is shuffle=True.
        # We require shuffle=False (explicitly) to avoid T003.
        is_shuffle_false = False

        if shuffle_arg:
            # Check literal False
            # For Python 3.8+ ast.Constant handles True/False/None.
            # ast.NameConstant is deprecated in 3.8 and removed in 3.14.
            if isinstance(shuffle_arg, ast.Constant) and shuffle_arg.value is False:
                is_shuffle_false = True
            # Check if variable name hints at False (e.g. SHUFFLE_OFF)?
            # No, keep strict: must be False.
            # But what if they pass a variable?
            # User Issue 1.5: "shuffle=SHOULD_SHUFFLE ...
            # ... are not understood"
            # Recommendation: "Document that only literal shuffle=False
            # is recognized"
            # We implemented a strict check. If it's a variable,
            # we can't know its value, so we warn.
            # This is "safe" behavior (false positive preferred
            # over false negative for leakage).

        if not is_shuffle_false:
            rule = RULES["T003"]
            self.violations.append(
                Violation(
                    rule_id=rule.id,
                    message=rule.description + " (shuffle must be explicitly False)",
                    filename=self.filename,
                    lineno=node.lineno,
                    col_offset=node.col_offset,
                    severity=rule.severity,
                    context="Random splitting violates temporal causality",
                )
            )

    def _check_fit_leakage(self, node: ast.Call) -> None:
        """
        T002: fit() on what looks like raw data instead of training split.
        Heuristic: If arg[0] is 'df', 'data', 'X', it might be leaky.
        If it is 'X_train', 'train_df', etc., it's likely safe.
        """
        if not node.args:
            return

        arg0 = node.args[0]
        arg_name = ""
        if isinstance(arg0, ast.Name):
            arg_name = arg0.id
        elif isinstance(arg0, ast.Attribute):
            arg_name = arg0.attr

        # New Heuristic (Narrowed Scope):
        # Only flag if name matches "known unsafe" patterns explicitly.
        # Safe by default.

        if not arg_name:
            return

        name_lower = arg_name.lower()

        if any(s in name_lower for s in SAFE_SUBSTRING_NAMES):
            return  # Explicitly safe

        is_suspicious = False

        if name_lower in UNSAFE_EXACT_NAMES:
            is_suspicious = True
        elif any(s in name_lower for s in UNSAFE_SUBSTRING_NAMES):
            is_suspicious = True

        if is_suspicious:
            rule = RULES["T002"]
            self.violations.append(
                Violation(
                    rule_id=rule.id,
                    message=(
                        "Model fit() called on potential non-training data "
                        f"'{arg_name}'. Ensure only training split is used."
                    ),
                    filename=self.filename,
                    lineno=node.lineno,
                    col_offset=node.col_offset,
                    severity=rule.severity,
                    context=f"Fitting model on {arg_name}",
                )
            )

    def _has_safe_parent(self, node: ast.Call) -> bool:
        """Check if call is preceded by a 'safe' operation like groupby or rolling."""
        if not isinstance(node.func, ast.Attribute):
            return False

        current = node.func.value

        # Neutral ops: return similar object, don't destroy order
        neutral_ops = {"reset_index", "copy", "dropna", "fillna", "assign", "pipe"}
        max_iter = 100  # Guard against pathological AST depth
        iter_count = 0

        while iter_count < max_iter:
            iter_count += 1
            if isinstance(current, ast.Call):
                func_name = self._get_func_name(current.func)

                if func_name in ["groupby", "rolling", "expanding", "resample"]:
                    return True

                if func_name in neutral_ops:
                    # Continue traversal
                    # Need to look deeper.
                    # Call structure: method().neutral()
                    # current=Call(neutral). func.value=Call(preceding)
                    if isinstance(current.func, ast.Attribute):
                        current = current.func.value
                        continue
                    else:
                        return False

                return False

            elif isinstance(current, ast.Subscript):
                current = current.value
            elif isinstance(current, ast.Attribute):
                # e.g. df.groupby().col.mean() -> attribute access 'col'
                current = current.value
            else:
                return False

        return False  # Max depth exceeded (pathological AST)


def analyze_path(
    filepath: Path,
    source_override: Optional[str] = None,
    mapper_override: Optional[NotebookMapper] = None,
) -> Tuple[List[Violation], str]:
    """
    Core analysis logic: Read -> Parse -> Hash -> Analyze -> Map.
    Returns (violations, content_hash).

    Can raise (e.g. FileNotFoundError, PermissionError, or parser errors).
    Intended for use via the runner, which catches exceptions and reports them as E000.
    """
    source = ""
    mapper: Optional[NotebookMapper] = None

    if source_override is not None:
        source = source_override
        mapper = mapper_override
    else:
        # Default path-based loading
        if filepath.suffix == ".ipynb":
            source, mapper = parse_notebook(filepath)
        else:
            with open(filepath, "r", encoding="utf-8") as f:
                source = f.read()

    content_hash = ContentCache.compute_hash(source)
    violations = analyze_code(source, filename=str(filepath))

    if mapper:
        violations = map_violations(violations, mapper)

    return violations, content_hash


def analyze_file(filepath: Path, cache_root: Optional[Path] = None) -> List[Violation]:
    """
    Analyze a file for violations, using caching.
    """
    try:
        # Determine cache root intelligently if not provided
        if not cache_root:
            from .config import find_pyproject_toml

            pyproj = find_pyproject_toml(filepath)
            if pyproj:
                cache_root = pyproj.parent
            else:
                cache_root = filepath.parent if filepath.parent else Path.cwd()

        cache = ContentCache(cache_root)

        # Read and hash once to check cache
        source = ""
        mapper: Optional[NotebookMapper] = None
        if filepath.suffix == ".ipynb":
            source, mapper = parse_notebook(filepath)
        else:
            with open(filepath, "r", encoding="utf-8") as f:
                source = f.read()

        content_hash = ContentCache.compute_hash(source)
        cached_violations = cache.get(filepath, content_hash)

        if cached_violations is not None:
            return cached_violations

        # Cache miss: use already-read source (single read)
        violations = analyze_code(source, filename=str(filepath))
        if mapper:
            violations = map_violations(violations, mapper)
        cache.set(filepath, content_hash, violations)
        return violations

    except SyntaxError as e:
        return [
            Violation(
                rule_id="E001",
                message=f"Syntax error: {e}",
                filename=str(filepath),
                lineno=e.lineno or 0,
                col_offset=e.offset or 0,
                severity="error",
            )
        ]
    except Exception as e:
        return [
            Violation(
                rule_id="E000",
                message=f"Analysis error: {str(e)}",
                filename=str(filepath),
                lineno=0,
                col_offset=0,
                severity="error",
            )
        ]


def analyze_code(source: str, filename: str = "<string>") -> List[Violation]:
    """Analyze a string of Python code for temporal leakage violations."""
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError as e:
        return [
            Violation(
                rule_id="E001",
                message=f"Syntax error: {e}",
                filename=filename,
                lineno=e.lineno or 0,
                col_offset=e.offset or 0,
                severity="error",
            )
        ]
    analyzer = TemporalAnalyzer(filename)
    analyzer.visit(tree)

    # Filter with suppressions
    suppressions = extract_suppressions(source)
    if not suppressions:
        return analyzer.violations

    filtered_violations = []
    for v in analyzer.violations:
        line_suppressions = suppressions.get(v.lineno, set())
        if v.rule_id not in line_suppressions:
            filtered_violations.append(v)

    return filtered_violations
