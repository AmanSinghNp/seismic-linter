"""
Rule definitions and violation structures for seismic-linter.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Violation:
    """Represents a detected temporal causality violation."""

    rule_id: str
    message: str
    filename: str
    lineno: int
    col_offset: int
    severity: str  # 'error', 'warning', 'info'
    context: Optional[str] = None
    cell_id: Optional[int] = None  # For Jupyter Notebooks


@dataclass(frozen=True)
class Rule:
    """Definition of a linter rule."""

    id: str
    description: str
    severity: str


# Rule Registry
RULES = {
    "E000": Rule(
        id="E000",
        description="Analysis error (e.g. crash or exception)",
        severity="error",
    ),
    "E001": Rule(id="E001", description="Syntax error in source", severity="error"),
    "T001": Rule(
        id="T001",
        description="Global statistics computed without temporal context",
        severity="warning",
    ),
    "T002": Rule(
        id="T002",
        description="sklearn fit() called on potentially leaky data",
        severity="info",
    ),
    "T003": Rule(
        id="T003",
        description="train_test_split used with shuffle=True on time series",
        severity="error",
    ),
}
